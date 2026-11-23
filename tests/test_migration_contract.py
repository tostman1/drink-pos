"""DP-024 opt-in migration safety; synthetic baseline, not historical releases."""

import importlib
import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import test_database_recovery as fixtures
from app import application_recovery as recovery
from app.db import schema


class MigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.DatabaseRecoveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root

    def module(self):
        try:
            return importlib.import_module("app.db.migrations")
        except ModuleNotFoundError:
            self.fail("DP-024 versioned migration contract missing")

    def current(self):
        database, *_ = self.fixture.populate_operational_database()
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA journal_mode=DELETE")
        return database

    def apply(self, database, **kwargs):
        return self.module().migrate(database, initialize=lambda c: schema._init_legacy(connection=c), **kwargs)

    def test_fresh_requires_permission_and_initializes_atomically(self):
        m = self.module()
        database = self.root / "fresh.db"
        self.fixture.configure_schema_for(database)
        self.assertEqual(m.inspect(database)["state"], "fresh-permission-required")
        with self.assertRaises(m.MigrationRejected):
            self.apply(database)
        self.assertFalse(database.exists())
        self.assertFalse((self.root / "messages.json").exists())
        self.apply(database, allow_fresh=True)
        self.assertEqual(m.inspect(database)["state"], "versioned-current")
        self.assertEqual(m.inspect(database)["version"], 1)
        before = recovery.database_metadata(database)
        self.apply(database)
        self.assertEqual(before, recovery.database_metadata(database))

    def test_exact_current_adoption_records_only_new_metadata_preserving_history(self):
        database = self.current()
        m = self.module()
        before = recovery.database_metadata(database)
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("UPDATE order_lines SET unit_purchase_price_eur=0")
            conn.execute(
                "UPDATE transaction_items SET unit_purchase_price_eur=0,purchase_total_eur=0,profit_eur=total_eur"
            )
            conn.execute("UPDATE items SET purchase_price_eur=8,active=0,archived_at='history' WHERE name='1 Runde'")
            conn.execute("UPDATE people SET first_name='Historical',last_name='Mismatch' WHERE id=1")
            conn.commit()
            original = conn.iterdump()
            original = list(original)
        self.assertEqual(m.inspect(database)["state"], "recognized-unversioned")
        with self.assertRaises(m.MigrationRejected):
            self.apply(database)
        self.apply(database, adopt_legacy=True)
        with closing(sqlite3.connect(database)) as conn:
            for table in before["tables"]:
                self.assertEqual(
                    [s for s in conn.iterdump() if s.startswith('INSERT INTO "' + table + '"')],
                    [s for s in original if s.startswith('INSERT INTO "' + table + '"')],
                )
        after = recovery.database_metadata(database)
        self.apply(database)
        self.assertEqual(after, recovery.database_metadata(database))

    def test_unknown_partial_prototype_and_zero_length_are_not_fresh(self):
        m = self.module()
        for name, sql in (
            ("unknown", "CREATE TABLE surprise(id INTEGER)"),
            ("partial", "CREATE TABLE people(id INTEGER PRIMARY KEY,name TEXT)"),
            (
                "prototype",
                "CREATE TABLE drinks(name TEXT,price REAL); CREATE TABLE orders(person_id INTEGER,drink TEXT,quantity INTEGER)",
            ),
            ("empty", ""),
        ):
            database = self.root / (name + ".db")
            with closing(sqlite3.connect(database)) as conn:
                conn.executescript(sql)
            before = database.read_bytes()
            with self.subTest(name=name), self.assertRaises(m.MigrationRejected):
                self.apply(database, allow_fresh=True, adopt_legacy=True)
            self.assertEqual(before, database.read_bytes())

    def test_future_missing_contradictory_checksum_and_incomplete_ledger_rejected(self):
        m = self.module()
        database = self.current()
        self.apply(database, adopt_legacy=True)
        baseline = database.read_bytes()
        for sql in (
            "PRAGMA user_version=2",
            "DROP TABLE schema_migrations",
            "UPDATE schema_migrations SET checksum='wrong'",
            "DELETE FROM schema_migrations",
            "UPDATE schema_migrations SET completed_at=''",
            "PRAGMA application_id=99",
            "UPDATE schema_migrations SET migration_id='unknown'",
            "UPDATE schema_migrations SET source_version=7",
            "UPDATE schema_migrations SET target_schema_sha256='unknown'",
            "UPDATE schema_migrations SET completed_at='2999-01-01T00:00:00+00:00'",
            "CREATE TRIGGER ledger_extra AFTER INSERT ON schema_migrations BEGIN SELECT 1; END",
        ):
            database.write_bytes(baseline)
            with closing(sqlite3.connect(database)) as conn:
                conn.executescript(sql)
                conn.commit()
            before = database.read_bytes()
            with self.subTest(sql=sql), self.assertRaises(m.MigrationRejected):
                self.apply(database, adopt_legacy=True)
            self.assertEqual(before, database.read_bytes())

    def test_inspection_is_read_only_and_sidecars_rejected_before_sql(self):
        m = self.module()
        database = self.current()
        before = database.read_bytes()
        connect = sqlite3.connect

        def readonly(path, **kwargs):
            self.assertTrue(str(path).endswith("?mode=ro"))
            return connect(path, **kwargs)

        with patch("sqlite3.connect", side_effect=readonly):
            self.assertEqual(m.inspect(database)["state"], "recognized-unversioned")
        self.assertEqual(before, database.read_bytes())
        for suffix in ("-wal", "-shm", "-journal"):
            sidecar = Path(str(database) + suffix)
            sidecar.write_bytes(b"synthetic recovery evidence")
            with patch("sqlite3.connect", side_effect=AssertionError):
                self.assertEqual(m.inspect(database)["state"], "recovery-required")
            sidecar.unlink()

    def test_schema_data_and_precommit_failures_roll_back_all_db_changes(self):
        self.module()
        database = self.current()
        before = recovery.database_metadata(database)
        for stage in ("before-write", "after-schema", "after-ledger", "before-commit"):

            def fail(point, conn):
                if point == stage:
                    raise sqlite3.OperationalError("synthetic fault")

            with self.subTest(stage=stage), self.assertRaises(sqlite3.OperationalError):
                self.apply(database, adopt_legacy=True, fault=fail)
            self.assertEqual(before, recovery.database_metadata(database))
            self.assertFalse(Path(str(database) + ".migration-lock").exists())
        fresh = self.root / "failed-fresh.db"
        messages_before = (self.root / "messages.json").read_bytes()
        self.fixture.configure_schema_for(fresh)
        with patch.object(schema, "ensure_default_items", side_effect=sqlite3.OperationalError("data fault")):
            with self.assertRaises(sqlite3.OperationalError):
                self.apply(fresh, allow_fresh=True)
        with closing(sqlite3.connect(fresh)) as conn:
            self.assertEqual(conn.execute("SELECT name FROM sqlite_master").fetchall(), [])
        self.assertEqual((self.root / "messages.json").read_bytes(), messages_before)

    def test_concurrent_writer_and_stale_migration_lock_fail_without_changes(self):
        m = self.module()
        database = self.current()
        before = recovery.database_metadata(database)
        with closing(sqlite3.connect(database)) as writer:
            writer.execute("BEGIN IMMEDIATE")
            with self.assertRaises(m.MigrationBusy):
                self.apply(database, adopt_legacy=True)
            writer.rollback()
        lock = Path(str(database) + ".migration-lock")
        lock.write_text("other owner", encoding="utf-8")
        with self.assertRaises(m.MigrationBusy):
            self.apply(database, adopt_legacy=True)
        self.assertEqual(lock.read_text(encoding="utf-8"), "other owner")
        self.assertEqual(before, recovery.database_metadata(database))

    def test_opt_in_startup_rejects_before_files_connections_or_ddl(self):
        m = self.module()
        database = self.root / "corrupt.db"
        database.write_bytes(b"not sqlite")
        self.fixture.configure_schema_for(database)
        with (
            patch.dict(os.environ, {"DRINK_POS_MIGRATION_MODE": "versioned"}),
            patch.object(schema, "ensure_messages_file", side_effect=AssertionError),
            patch.object(schema, "get_conn", side_effect=AssertionError),
        ):
            with self.assertRaises(m.MigrationRejected):
                schema.init_db()

    def test_abrupt_transaction_keeps_history_and_independent_bundle_recovers(self):
        self.module()
        database = self.current()
        messages = self.root / "messages.json"
        bundle = recovery.create_backup(
            database, messages, self.root / "backup", deployment_id="RL02", app_commit="a" * 40, quiesced=True
        )
        manifest = recovery.verify_application_bundle(bundle)
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import os,sys; from pathlib import Path; from app.db import migrations as m; m.migrate(Path(sys.argv[1]),adopt_legacy=True,fault=lambda p,c: os._exit(37) if p=='before-commit' else None)",
                str(database),
            ],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(self.module().inspect(database)["state"], "recovery-required")
        recovered = recovery.restore_application(
            bundle,
            self.root / "independent",
            expected_commit="a" * 40,
            expected_schema=manifest["database"]["schema_sha256"],
        )
        self.assertEqual(
            recovery.database_metadata(recovered / "state/database.db", immutable=True), manifest["database"]
        )
        # Explicit SQLite recovery of synthetic failed state; NEVER automatic gate repair.
        with closing(sqlite3.connect(database)) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        self.assertEqual(recovery.database_metadata(database), manifest["database"])
        self.assertTrue(Path(str(database) + ".migration-lock").exists())

    def test_missing_and_duplicate_payment_identifiers_are_never_repaired(self):
        m = self.module()
        database = self.current()
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("UPDATE self_payment_sessions SET client_payment_id=NULL")
            conn.commit()
        self.apply(database, adopt_legacy=True)
        with closing(sqlite3.connect(database)) as conn:
            self.assertEqual(conn.execute("SELECT client_payment_id FROM self_payment_sessions").fetchall(), [(None,)])
            conn.execute("DROP INDEX idx_self_payment_sessions_client_payment_id")
            conn.execute(
                "INSERT INTO self_payment_sessions(person_id,client_payment_id,status,amount_eur,amount_cents,revision,created_at,updated_at) SELECT person_id,'duplicate','unknown',amount_eur,amount_cents,revision,created_at,updated_at FROM self_payment_sessions"
            )
            conn.execute("UPDATE self_payment_sessions SET client_payment_id='duplicate'")
            conn.commit()
        before = database.read_bytes()
        with self.assertRaises(m.MigrationRejected):
            self.apply(database, adopt_legacy=True)
        self.assertEqual(database.read_bytes(), before)

    def test_storage_permission_and_postcommit_filesystem_boundaries(self):
        m = self.module()
        database = self.current()
        before = database.read_bytes()
        for error in (PermissionError("synthetic denied"), OSError(28, "synthetic full")):
            with patch.object(m.os, "open", side_effect=error), self.assertRaises(OSError):
                self.apply(database, adopt_legacy=True)
            self.assertEqual(database.read_bytes(), before)
        self.fixture.configure_schema_for(database)
        with (
            patch.dict(os.environ, {"DRINK_POS_MIGRATION_MODE": "versioned", "DRINK_POS_ADOPT_LEGACY": "1"}),
            patch.object(schema, "ensure_messages_file", side_effect=OSError("postcommit filesystem fault")),
        ):
            with self.assertRaises(OSError):
                schema.init_db()
        self.assertEqual(m.inspect(database)["state"], "versioned-current")
        # Committed DB is not rolled back by unrelated optional message failure.

    def test_wal_with_active_writer_is_intervention_not_immutable_evidence(self):
        m = self.module()
        database = self.current()
        with closing(sqlite3.connect(database)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("UPDATE settings SET value='active' WHERE key='app_name'")
            writer.commit()
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("UPDATE settings SET value='uncommitted' WHERE key='app_name'")
            with patch("sqlite3.connect", side_effect=AssertionError):
                self.assertEqual(m.inspect(database)["state"], "recovery-required")
            writer.rollback()
        self.assertEqual(m.inspect(database)["state"], "recovery-required")
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("PRAGMA journal_mode=DELETE")
        self.assertEqual(m.inspect(database)["state"], "recognized-unversioned")

    def test_unknown_mode_and_permission_fail_before_first_write(self):
        m = self.module()
        database = self.root / "not-created" / "state.db"
        self.fixture.configure_schema_for(database)
        for env in (
            {"DRINK_POS_MIGRATION_MODE": "typo"},
            {"DRINK_POS_MIGRATION_MODE": "versioned", "DRINK_POS_ALLOW_FRESH": "yes"},
        ):
            with patch.dict(os.environ, env), self.assertRaises(m.MigrationRejected):
                schema.init_db()
            self.assertFalse(database.parent.exists())

    def test_partial_ledger_cannot_be_disguised_as_unversioned_state(self):
        m = self.module()
        database = self.current()
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("CREATE VIEW schema_migrations AS SELECT 1 AS version")
        self.assertTrue(m.inspect(database)["ledger_present"])
        with self.assertRaises(m.MigrationRejected):
            self.apply(database, adopt_legacy=True)

    def test_real_concurrent_migration_processes_reject_second_attempt(self):
        m = self.module()
        database = self.current()
        script = "import sys; from pathlib import Path; from app.db import migrations as m; def_placeholder=0\ndef fault(p,c):\n if p=='after-schema':\n  print('locked',flush=True); sys.stdin.readline()\nm.migrate(Path(sys.argv[1]),adopt_legacy=True,fault=fault)"
        process = subprocess.Popen(
            [sys.executable, "-B", "-c", script, str(database)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(process.stdout.readline().strip(), "locked")
            with self.assertRaises(m.MigrationBusy):
                self.apply(database, adopt_legacy=True)
            _, stderr = process.communicate("release\n", timeout=20)
            self.assertEqual(process.returncode, 0, stderr)
        finally:
            if process.returncode is None:
                process.kill()
                process.communicate()
        self.assertEqual(m.inspect(database)["state"], "versioned-current")

    def test_changed_source_and_fresh_ddl_failure_do_not_advance_ledger(self):
        m = self.module()
        database = self.current()

        def changed(point, conn):
            if point == "before-write":
                with closing(sqlite3.connect(database)) as other:
                    other.execute("PRAGMA user_version=10")

        with self.assertRaises(m.MigrationRejected):
            self.apply(database, adopt_legacy=True, fault=changed)
        self.assertFalse(Path(str(database) + ".migration-lock").exists())
        fresh = self.root / "ddl-failed.db"

        def fail_ddl(conn):
            conn.execute("CREATE TABLE partial(id INTEGER)")
            raise sqlite3.OperationalError("synthetic DDL failure")

        with self.assertRaises(sqlite3.OperationalError):
            m.migrate(fresh, allow_fresh=True, initialize=fail_ddl)
        with closing(sqlite3.connect(fresh)) as conn:
            self.assertEqual(conn.execute("SELECT name FROM sqlite_master").fetchall(), [])
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)

    @unittest.skipIf(os.name == "nt", "POSIX permissions; Windows ACL remains operator boundary")
    def test_real_read_only_file_permission_failure_preserves_state(self):
        database = self.current()
        before = database.read_bytes()
        database.chmod(0o400)
        try:
            self.assertEqual(self.module().inspect(database)["state"], "recognized-unversioned")
            if os.geteuid() == 0:
                self.skipTest("Root bypasses ordinary file permissions")
            with self.assertRaises(sqlite3.OperationalError):
                self.apply(database, adopt_legacy=True)
            self.assertEqual(before, database.read_bytes())
        finally:
            database.chmod(0o600)

    def test_preflight_accepts_verified_ledger_and_rejects_unknown_metadata(self):
        from app.upgrade_preflight import evaluate
        from app.release_identity import release_identity

        database = self.current()
        self.apply(database, adopt_legacy=True)
        for valid in (True, False):
            if not valid:
                with closing(sqlite3.connect(database)) as conn:
                    conn.execute("UPDATE schema_migrations SET checksum='unknown'")
                    conn.commit()
            bundle = recovery.create_backup(
                database,
                self.root / "messages.json",
                self.root / ("backup-" + str(valid)),
                deployment_id="RL02",
                app_commit="a" * 40,
                quiesced=True,
            )
            manifest = recovery.verify_application_bundle(bundle)
            current = release_identity("a" * 40, "local", None)
            candidate = release_identity("b" * 40, "candidate", None)
            evidence = dict(
                format="drink-pos-upgrade-evidence",
                format_version=1,
                deployment_id="RL02",
                current_identity_sha256=recovery.digest_json(current),
                candidate_identity_sha256=recovery.digest_json(candidate),
                source_schema_sha256=manifest["database"]["schema_sha256"],
                target_schema_sha256=manifest["database"]["schema_sha256"],
                supported=True,
                approved_by="synthetic",
                permitted_changes=[],
                candidate_configuration={},
                target_python="3.12",
                secrets_recovery_verified=True,
                encryption_required=False,
            )
            result = evaluate(
                bundle=bundle,
                current=current,
                candidate=candidate,
                evidence=evidence,
                isolated_copy=True,
                mode="local",
                max_backup_age_seconds=3600,
            )
            self.assertEqual(result["status"], "rehearsal-ready" if valid else "unsafe")
