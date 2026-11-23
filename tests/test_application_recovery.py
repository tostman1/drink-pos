"""DP-014/010/011 portable recovery; disposable synthetic state only."""

import importlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch


class ApplicationRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="drink-pos-app-recovery-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "installation ä" / "custom.db"
        self.source.parent.mkdir()
        with closing(sqlite3.connect(self.source)) as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE history(id INTEGER PRIMARY KEY AUTOINCREMENT, payment_id TEXT UNIQUE);
                INSERT INTO history VALUES(1,'payment-id-1');
                INSERT INTO history VALUES(100,'deleted-high-water');
                DELETE FROM history WHERE id=100;
                CREATE TABLE event_sessions(id INTEGER PRIMARY KEY, csv_path TEXT, pdf_path TEXT,
                                            status TEXT, invoice_created INTEGER);
                CREATE INDEX history_payment ON history(payment_id);
                CREATE TRIGGER immutable_history BEFORE DELETE ON history
                  BEGIN SELECT RAISE(ABORT, 'immutable'); END;
            """)
            events = self.source.parent / "events"
            events.mkdir()
            for name, data in (("invoice.csv", b"\xef\xbb\xbfrecovery"), ("invoice.pdf", b"%PDF-synthetic")):
                (events / name).write_bytes(data)
            conn.execute(
                "INSERT INTO event_sessions VALUES(1,?,?,'CLOSED',1)",
                (str(events / "invoice.csv"), str(events / "invoice.pdf")),
            )
            conn.commit()
        self.messages = self.root / "external-messages.json"
        self.messages.write_text('{"synthetic":"Wording ä"}', encoding="utf-8")
        self.destination = self.root / "backups"

    def module(self):
        try:
            return importlib.import_module("app.application_recovery")
        except ModuleNotFoundError:
            self.fail("EF-08b application recovery interface is missing")

    def backup(self, **kwargs):
        return self.module().create_backup(
            self.source,
            self.messages,
            self.destination,
            deployment_id="synthetic-A",
            app_commit="a" * 40,
            quiesced=True,
            **kwargs,
        )

    def restore(self, bundle, target=None, **kwargs):
        module = self.module()
        manifest = module.verify_application_bundle(bundle)
        return module.restore_application(
            bundle,
            target or self.root / "recovered",
            expected_commit="a" * 40,
            expected_schema=manifest["database"]["schema_sha256"],
            **kwargs,
        )

    def test_complete_state_and_relocated_relationships(self):
        bundle = self.backup()
        recovered = self.restore(bundle)
        with (
            closing(sqlite3.connect(self.source)) as source,
            closing(sqlite3.connect(recovered / "state/database.db")) as target,
        ):
            self.assertEqual(
                source.execute("SELECT * FROM history").fetchall(), target.execute("SELECT * FROM history").fetchall()
            )
            self.assertEqual(
                source.execute("SELECT * FROM sqlite_sequence").fetchall(),
                target.execute("SELECT * FROM sqlite_sequence").fetchall(),
            )
            self.assertEqual(
                source.execute("SELECT * FROM sqlite_master ORDER BY name").fetchall(),
                target.execute("SELECT * FROM sqlite_master ORDER BY name").fetchall(),
            )
            csv, pdf = target.execute("SELECT csv_path,pdf_path FROM event_sessions").fetchone()
            self.assertEqual(Path(csv).read_bytes(), (self.source.parent / "events/invoice.csv").read_bytes())
            self.assertEqual(Path(pdf).read_bytes(), (self.source.parent / "events/invoice.pdf").read_bytes())
            with self.assertRaises(sqlite3.IntegrityError):
                target.execute("DELETE FROM history")
        self.assertEqual((recovered / "state/messages.json").read_bytes(), self.messages.read_bytes())
        self.assertTrue((recovered / "RECOVERED.json").is_file())

    def test_refuses_unquiesced_backup(self):
        with self.assertRaises(ValueError):
            self.module().create_backup(
                self.source,
                self.messages,
                self.destination,
                deployment_id="synthetic-A",
                app_commit="a" * 40,
                quiesced=False,
            )
        self.assertFalse(self.destination.exists())

    def test_missing_required_artifact_refuses_publication(self):
        (self.source.parent / "events/invoice.pdf").unlink()
        with self.assertRaises(ValueError):
            self.backup()
        self.assertFalse(list(self.destination.glob("drink_pos_application_*")))

    def test_corruption_extra_files_and_unsupported_version_rejected(self):
        for mode in ("corrupt", "extra", "version"):
            bundle = self.backup()
            if mode == "corrupt":
                (bundle / "state/events/invoice.pdf").write_bytes(b"truncated")
            elif mode == "extra":
                (bundle / "unknown").write_text("foreign")
            else:
                manifest = json.loads((bundle / "manifest.json").read_text())
                manifest["format_version"] = 999
                (bundle / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                self.restore(bundle)
            self.assertFalse((self.root / "recovered").exists())

    def test_existing_destination_never_overwritten(self):
        bundle = self.backup()
        target = self.root / "owner"
        target.mkdir()
        (target / "work").write_text("owner")
        with self.assertRaises(FileExistsError):
            self.restore(bundle, target)
        self.assertEqual((target / "work").read_text(), "owner")

    def test_incompatible_commit_or_schema_rejected(self):
        module = self.module()
        bundle = self.backup()
        manifest = module.verify_application_bundle(bundle)
        for commit, schema in (("b" * 40, manifest["database"]["schema_sha256"]), ("a" * 40, "0" * 64)):
            with self.assertRaises(ValueError):
                module.restore_application(
                    bundle, self.root / "recovered", expected_commit=commit, expected_schema=schema
                )
        self.assertFalse((self.root / "recovered").exists())

    def test_observed_filesystem_change_aborts_backup(self):
        module = self.module()
        copy = module.copy_payload

        def changed(*args):
            result = copy(*args)
            self.messages.write_text('{"changed":true}')
            return result

        with patch.object(module, "copy_payload", side_effect=changed):
            with self.assertRaises(ValueError):
                self.backup()
        self.assertFalse(list(self.destination.glob("drink_pos_application_*")))

    def test_interruption_cleans_owned_resources(self):
        module = self.module()
        with patch.object(module, "copy_payload", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.backup()
        self.assertFalse(list(self.destination.iterdir()))

    def test_overlap_fails_without_removing_lock(self):
        module = self.module()
        self.destination.mkdir()
        lock = self.destination / ".drink-pos-application.lock"
        lock.write_text("other operation")
        with self.assertRaises(module.OperationBusy):
            self.backup()
        self.assertEqual(lock.read_text(), "other operation")

    def test_secrets_not_accepted_as_portable_configuration(self):
        with self.assertRaises(ValueError):
            self.backup(configuration={"SUMUP_API_KEY": "synthetic-not-a-secret"})

    def rewrite_manifest(self, bundle, update):
        module = self.module()
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        update(manifest)
        (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        from app.database_recovery import file_metadata

        marker = {"status": "verified", "backup_id": bundle.name, "manifest": file_metadata(bundle / "manifest.json")}
        (bundle / "COMPLETED.json").write_text(json.dumps(marker), encoding="utf-8")
        return module

    def test_traversal_absolute_windows_and_reserved_paths_fail(self):
        for unsafe in (
            "../outside",
            "/outside",
            "C:/outside",
            "state/events/../outside",
            "state/events/CON.csv",
            "state/events/a\\b",
        ):
            bundle = self.backup()
            module = self.rewrite_manifest(
                bundle, lambda manifest: manifest["files"].update({unsafe: {"size_bytes": 0, "sha256": "0" * 64}})
            )
            with self.assertRaises(ValueError):
                module.verify_application_bundle(bundle)
            self.assertFalse((self.root / "outside").exists())

    def test_missing_file_marker_and_malformed_metadata_rejected(self):
        for name in ("state/messages.json", "COMPLETED.json"):
            bundle = self.backup()
            (bundle / name).unlink()
            with self.assertRaises((ValueError, OSError)):
                self.restore(bundle)
        bundle = self.backup()
        for raw in ("[]", '{"format":1,"format":2}', "not-json"):
            (bundle / "manifest.json").write_text(raw)
            with self.assertRaises(ValueError):
                self.restore(bundle)

    def test_symlinks_nonregular_entries_and_case_collisions_rejected(self):
        module = self.module()
        if os.name == "posix":
            (self.source.parent / "events/INVOICE.csv").write_bytes(b"case collision")
            with self.assertRaises(ValueError):
                self.backup()
            (self.source.parent / "events/INVOICE.csv").unlink()
        if os.name == "posix":
            os.mkfifo(self.source.parent / "events/pipe")
            with self.assertRaises(ValueError):
                self.backup()
            (self.source.parent / "events/pipe").unlink()
        bundle = self.backup()
        link = bundle / "state/events/link"
        try:
            link.symlink_to(self.messages)
        except OSError as exc:
            if os.name != "nt":
                raise
            self.assertIn(getattr(exc, "winerror", None), (1314, 5))
            return  # Windows symlink privilege unavailable; Linux executes this guard.
        with self.assertRaises(ValueError):
            module.verify_application_bundle(bundle)

    def test_changed_database_and_new_artifact_abort(self):
        module = self.module()
        original = module.copy_payload
        for change in ("database", "new-file"):

            def changed(*args):
                original(*args)
                if change == "database":
                    with closing(sqlite3.connect(self.source)) as conn:
                        conn.execute("INSERT INTO history(payment_id) VALUES(?)", ("changed",))
                        conn.commit()
                else:
                    (self.source.parent / "events/new.csv").write_text("new")

            with patch.object(module, "copy_payload", side_effect=changed):
                with self.assertRaises(ValueError):
                    self.backup()
        self.assertFalse(list(self.destination.glob("drink_pos_application_*")))

    def test_restore_failure_and_racing_empty_target_preserve_owner(self):
        module = self.module()
        bundle = self.backup()
        target = self.root / "recovered"
        with patch.object(module, "copy_payload", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.restore(bundle, target)
        self.assertFalse(target.exists())
        self.assertFalse(list(self.root.glob(".drink-pos-recovery-*")))
        publish = module.publish_directory

        def race(staging, destination):
            destination.mkdir()
            publish(staging, destination)

        with patch.object(module, "publish_directory", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.restore(bundle, target)
        self.assertTrue(target.is_dir())
        self.assertEqual(list(target.iterdir()), [])

    def test_abrupt_backup_and_restore_leave_unpublished_state_and_stale_lock(self):
        module = self.module()
        bundle = self.backup()
        for command in ("backup", "restore"):
            if command == "backup":
                code = (
                    "import os; from app import application_recovery as r; from pathlib import Path; "
                    "r.copy_payload=lambda *a: os._exit(37); "
                    f"r.create_backup(Path({str(self.source)!r}),Path({str(self.messages)!r}),Path({str(self.destination)!r}),deployment_id='synthetic-A',app_commit={'a' * 40!r},quiesced=True)"
                )
            else:
                schema = module.verify_application_bundle(bundle)["database"]["schema_sha256"]
                code = (
                    "import os; from app import application_recovery as r; from pathlib import Path; "
                    "r.copy_payload=lambda *a: os._exit(37); "
                    f"r.restore_application(Path({str(bundle)!r}),Path({str(self.root / 'interrupted')!r}),expected_commit={'a' * 40!r},expected_schema={schema!r})"
                )
            result = subprocess.run([sys.executable, "-c", code], check=False, capture_output=True)
            self.assertEqual(result.returncode, 37, result.stderr)
        self.assertFalse((self.root / "interrupted").exists())
        self.assertEqual(len(list(self.destination.glob("drink_pos_application_*"))), 1)
        self.assertTrue(list(self.destination.glob(".drink-pos-application-*")))
        with self.assertRaises(module.OperationBusy):
            self.backup()

    def test_two_simultaneous_processes_have_predictable_overlap(self):
        # One process acquires and holds the actual OS-exclusive lock while a
        # second process attempts backup. Pipe coordination, no timing sleeps.
        code = (
            "import sys; from pathlib import Path; from app.application_recovery import operation_lock; "
            f"lock=operation_lock(Path({str(self.destination / '.drink-pos-application.lock')!r})); "
            "lock.__enter__(); print('locked',flush=True); sys.stdin.readline(); lock.__exit__(None,None,None)"
        )
        self.destination.mkdir()
        process = subprocess.Popen(
            [sys.executable, "-c", code],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            self.assertEqual(process.stdout.readline().strip(), "locked")
            with self.assertRaises(self.module().OperationBusy):
                self.backup()
        finally:
            process.communicate("release\n", timeout=20)
        self.assertEqual(process.returncode, 0)

    def test_status_age_deployment_integrity_lock_and_cli_exit_codes(self):
        module = self.module()
        self.assertEqual(module.backup_status(self.destination, "synthetic-A", 3600)["status"], "attention")
        bundle = self.backup()
        self.assertEqual(module.backup_status(self.destination, "synthetic-A", 3600)["status"], "ok")
        self.assertEqual(module.backup_status(self.destination, "synthetic-B", 3600)["status"], "attention")
        self.rewrite_manifest(
            bundle,
            lambda m: m.update(created_at_utc="2000-01-01T00:00:00+00:00", started_at_utc="2000-01-01T00:00:00+00:00"),
        )
        self.assertEqual(module.backup_status(self.destination, "synthetic-A", 3600)["status"], "attention")
        args = [
            sys.executable,
            "-m",
            "app.application_recovery",
            "status",
            "--destination",
            str(self.destination),
            "--deployment-id",
            "synthetic-A",
            "--max-age-seconds",
            "3600",
        ]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 4)
        self.assertEqual(json.loads(result.stdout)["status"], "attention")
        result = subprocess.run(
            [sys.executable, "-m", "app.application_recovery", "verify", str(bundle)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        (bundle / "state/messages.json").write_text("corrupt")
        result = subprocess.run(
            [sys.executable, "-m", "app.application_recovery", "verify", str(bundle)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("corrupt", result.stderr)

    def test_legacy_database_bundle_remains_available(self):
        from app import backup_database, restore_database

        with patch.dict(
            os.environ,
            {
                "DRINK_POS_DB": str(self.source),
                "DRINK_POS_BACKUP_DIR": str(self.destination),
                "DRINK_POS_BACKUP_KEEP": "",
            },
        ):
            legacy = backup_database.export_backup().parent
        restore_database.restore_backup(legacy, self.root / "legacy-recovered.db")
        with closing(sqlite3.connect(self.root / "legacy-recovered.db")) as conn:
            self.assertEqual(conn.execute("SELECT payment_id FROM history").fetchone()[0], "payment-id-1")
        self.assertEqual(json.loads((legacy / "manifest.json").read_text())["format_version"], 1)

    def test_missing_messages_requires_explicit_acknowledgement(self):
        self.messages.unlink()
        with self.assertRaises(ValueError):
            self.backup()
        bundle = self.backup(allow_missing_messages=True)
        self.assertFalse(self.module().verify_application_bundle(bundle)["messages_present"])
        restored = self.restore(bundle)
        self.assertFalse((restored / "state/messages.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows transient rename handles only")
    def test_windows_publication_retries_transient_denial_but_never_replaces_target(self):
        module = self.module()
        staging = self.root / "staging"
        staging.mkdir()
        target = self.root / "new"
        rename = Path.rename
        denied = OSError(13, "synthetic access denied")
        denied.winerror = 5
        attempts = []

        def temporarily_denied(source, destination):
            attempts.append(1)
            if len(attempts) == 1:
                raise denied
            return rename(source, destination)

        with patch.object(Path, "rename", temporarily_denied), patch("time.sleep"):
            module.publish_directory(staging, target)
        self.assertEqual(len(attempts), 2)
        self.assertTrue(target.is_dir())
        staging.mkdir()
        with patch.object(Path, "rename", side_effect=denied), patch("time.sleep"):
            with self.assertRaises(FileExistsError):
                module.publish_directory(staging, target)
        self.assertTrue(staging.exists())
        missing = self.root / "permission-denied-target"
        with patch.object(Path, "rename", side_effect=denied), patch("time.sleep"):
            with self.assertRaises(OSError):
                module.publish_directory(staging, missing)
        self.assertFalse(missing.exists())

    def test_full_operational_rehearsal_two_independent_deployments(self):
        # Reuse the existing all-16-table synthetic population, not production.
        from test_database_recovery import DatabaseRecoveryTests, sqlite_conn
        from app.services import events

        fixture = DatabaseRecoveryTests()
        fixture.setUp()
        try:
            database, _, _, event_id = fixture.populate_operational_database()
            with sqlite_conn(database) as conn:
                conn.row_factory = sqlite3.Row
                event = conn.execute("SELECT * FROM event_sessions WHERE id=?", (event_id,)).fetchone()
                events.close_event(conn, database, event, create_invoice=True)
                conn.execute(
                    "INSERT INTO transactions(type,total,details,timestamp) VALUES('EVENT_CLOSED',5,'synthetic invoice audit path remains unchanged','then')"
                )
                conn.commit()
            messages = fixture.root / "messages.json"
            module = self.module()
            for deployment in ("portable-A", "portable-B"):
                source_root = fixture.root / deployment
                source_root.mkdir()
                import shutil

                copied_db = source_root / "different-name.db"
                # Make each installation independent using snapshot + adjusted refs.
                snapshot = __import__("app.backup_database", fromlist=["create_snapshot"]).create_snapshot(
                    database, source_root
                )
                snapshot.rename(copied_db)
                shutil.copytree(database.parent / "events", source_root / "events")
                with sqlite_conn(copied_db) as conn:
                    paths = conn.execute("SELECT id,csv_path,pdf_path FROM event_sessions").fetchall()
                    for ident, csv, pdf in paths:
                        conn.execute(
                            "UPDATE event_sessions SET csv_path=?,pdf_path=? WHERE id=?",
                            (
                                str(source_root / "events" / Path(csv).name),
                                str(source_root / "events" / Path(pdf).name),
                                ident,
                            ),
                        )
                    conn.commit()
                bundle = module.create_backup(
                    copied_db, messages, self.destination, deployment_id=deployment, app_commit="a" * 40, quiesced=True
                )
                manifest = module.verify_application_bundle(bundle)
                restored = module.restore_application(
                    bundle,
                    fixture.root / (deployment + "-recovered"),
                    expected_commit="a" * 40,
                    expected_schema=manifest["database"]["schema_sha256"],
                )
                target = restored / "state/database.db"
                self.assertEqual(
                    module.database_metadata(target, immutable=True, original_references=manifest["event_references"]),
                    module.database_metadata(copied_db),
                )
                with sqlite_conn(copied_db) as source, sqlite_conn(target) as recovered:
                    tables = [row[0] for row in source.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                    self.assertEqual(len(tables), 17)
                    for table in tables:
                        self.assertGreater(source.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0], 0)
                        if table != "event_sessions":
                            self.assertEqual(
                                source.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall(),
                                recovered.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall(),
                            )
                    self.assertEqual(recovered.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
                    self.assertFalse(recovered.execute("PRAGMA foreign_key_check").fetchall())
                    csv, pdf = recovered.execute("SELECT csv_path,pdf_path FROM event_sessions").fetchone()
                    self.assertTrue(Path(csv).read_bytes().startswith(b"\xef\xbb\xbf"))
                    self.assertTrue(Path(pdf).read_bytes().startswith(b"%PDF"))
                    self.assertEqual(
                        recovered.execute("SELECT client_payment_id FROM self_payment_sessions").fetchone()[0],
                        "restore-payment-1",
                    )
                self.assertEqual(module.backup_status(self.destination, deployment, 3600)["status"], "ok")
        finally:
            fixture.tearDown()

    @unittest.skipUnless(os.name == "posix", "Real POSIX permissions require Linux; Windows ACLs separate")
    def test_private_permissions_under_permissive_umask(self):
        old = os.umask(0)
        try:
            bundle = self.backup()
            restored = self.restore(bundle)
            for root in (bundle, restored):
                for path in (root, *root.rglob("*")):
                    self.assertEqual(path.stat().st_mode & 0o777, 0o700 if path.is_dir() else 0o600)
        finally:
            os.umask(old)
