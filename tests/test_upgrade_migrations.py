"""DP-014/023 characterize real startup migration risks, not historical releases."""

import os
import sqlite3
import subprocess
import sys
import unittest
from contextlib import closing
from unittest.mock import patch

import test_database_recovery as fixtures
from app import application_recovery as recovery
from app.db import schema


class UpgradeMigrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.DatabaseRecoveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        self.root = self.fixture.root

    def test_prototype_import_is_guarded_but_uses_current_price_and_date(self):
        database = self.root / "prototype.db"
        with closing(sqlite3.connect(database)) as conn:
            conn.executescript("""
                CREATE TABLE people(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
                INSERT INTO people VALUES(1,'Historical Member');
                CREATE TABLE drinks(name TEXT, price REAL, active INTEGER);
                INSERT INTO drinks VALUES('Synthetic prototype',3.25,1);
                CREATE TABLE orders(person_id INTEGER,drink TEXT,quantity INTEGER);
                INSERT INTO orders VALUES(1,'Synthetic prototype',2);
                INSERT INTO orders VALUES(1,'Synthetic prototype',-1);
            """)
        self.fixture.configure_schema_for(database)
        schema.init_db()
        before = recovery.database_metadata(database)
        schema.init_db()
        self.assertEqual(before, recovery.database_metadata(database))
        with closing(sqlite3.connect(database)) as conn:
            self.assertEqual(
                conn.execute("SELECT quantity,unit_price_eur,event_open FROM order_lines").fetchall(), [(2, 3.25, 1)]
            )
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0], 2)
            self.assertNotEqual(conn.execute("SELECT consumed_date FROM order_lines").fetchone()[0], "historical-date")
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 0)
            self.assertEqual(conn.execute("PRAGMA application_id").fetchone()[0], 0)

    def test_failure_leaves_early_schema_and_messages_but_rolls_back_dml(self):
        database = self.root / "partial.db"
        with closing(sqlite3.connect(database)) as conn:
            conn.executescript("""
                CREATE TABLE people(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
                INSERT INTO people VALUES(1,'Historical Member');
            """)
        before = recovery.database_metadata(database)
        self.fixture.configure_schema_for(database)
        with patch.object(schema, "ensure_indexes", side_effect=sqlite3.OperationalError("synthetic late failure")):
            with self.assertRaises(sqlite3.OperationalError):
                schema.init_db()
        after = recovery.database_metadata(database)
        self.assertNotEqual(before["schema_sha256"], after["schema_sha256"])
        self.assertTrue((self.root / "messages.json").exists())
        with closing(sqlite3.connect(database)) as conn:
            self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            self.assertEqual(conn.execute("SELECT name,first_name FROM people").fetchall(), [("Historical Member", "")])
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM items").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0], 0)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchall(), [("ok",)])
        schema.init_db()
        self.assertGreater(recovery.database_metadata(database)["tables"]["items"], 0)

    def test_zero_cost_backfill_repeats_and_changes_cost_history_not_sales(self):
        database, _, _, _ = self.fixture.populate_operational_database()
        with closing(sqlite3.connect(database)) as conn:
            conn.execute(
                "UPDATE transaction_items SET unit_purchase_price_eur=0,purchase_total_eur=0,profit_eur=total_eur"
            )
            conn.execute("UPDATE order_lines SET unit_purchase_price_eur=0")
            sales = conn.execute("SELECT id,quantity,unit_price_eur,total_eur FROM transaction_items").fetchall()
            transactions = conn.execute("SELECT * FROM transactions").fetchall()
            conn.commit()
        schema.init_db()
        with closing(sqlite3.connect(database)) as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT unit_purchase_price_eur,purchase_total_eur,profit_eur FROM transaction_items"
                ).fetchone(),
                (1.4, 1.4, 1.1),
            )
            self.assertEqual(
                conn.execute("SELECT id,quantity,unit_price_eur,total_eur FROM transaction_items").fetchall(), sales
            )
            self.assertEqual(conn.execute("SELECT * FROM transactions").fetchall(), transactions)
            # Zero is not marked as 'already migrated'; changing current item cost
            # can change a later startup's backfill again. Preserve/document this.
            conn.execute("UPDATE order_lines SET unit_purchase_price_eur=0")
            conn.execute("UPDATE items SET purchase_price_eur=1.75 WHERE id=(SELECT item_id FROM order_lines LIMIT 1)")
            conn.commit()
        schema.init_db()
        with closing(sqlite3.connect(database)) as conn:
            self.assertEqual(conn.execute("SELECT unit_purchase_price_eur FROM order_lines").fetchone()[0], 1.75)

    def test_late_duplicate_payment_index_failure_keeps_ids_and_rolls_back_backfill(self):
        database, person, _, _ = self.fixture.populate_operational_database()
        with closing(sqlite3.connect(database)) as conn:
            conn.execute("DROP INDEX idx_self_payment_sessions_client_payment_id")
            conn.execute(
                "INSERT INTO self_payment_sessions(person_id,client_payment_id,status,amount_eur,amount_cents,revision,created_at,updated_at) VALUES(?,'restore-payment-1','unknown',2.7,270,'synthetic','then','then')",
                (person,),
            )
            conn.execute("UPDATE order_lines SET unit_purchase_price_eur=0")
            conn.commit()
        before = recovery.database_metadata(database)
        with self.assertRaises(sqlite3.IntegrityError):
            schema.init_db()
        self.assertEqual(before, recovery.database_metadata(database))

    def test_abrupt_migration_leaves_detectable_partial_schema_and_bundle_recovers(self):
        database = self.root / "interrupted.db"
        with closing(sqlite3.connect(database)) as conn:
            conn.executescript("""
                CREATE TABLE people(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
                INSERT INTO people VALUES(1,'Historical Member');
                CREATE TABLE event_sessions(id INTEGER PRIMARY KEY, csv_path TEXT,pdf_path TEXT,status TEXT,invoice_created INTEGER);
            """)
        messages = self.root / "messages.json"
        messages.write_text('{"synthetic":"pre-upgrade"}', encoding="utf-8")
        bundle = recovery.create_backup(
            database, messages, self.root / "backup", deployment_id="interrupted-A", app_commit="a" * 40, quiesced=True
        )
        manifest = recovery.verify_application_bundle(bundle)
        environment = os.environ.copy()
        environment.update(DRINK_POS_DB=str(database), DRINK_POS_MESSAGES=str(messages))
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import os; from app import main; main.schema_service.ensure_indexes=lambda *a: os._exit(37); main.startup()",
            ],
            env=environment,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertNotEqual(
            recovery.database_metadata(database)["schema_sha256"], manifest["database"]["schema_sha256"]
        )
        recovered = recovery.restore_application(
            bundle,
            self.root / "separate-recovery",
            expected_commit="a" * 40,
            expected_schema=manifest["database"]["schema_sha256"],
        )
        self.assertEqual(
            recovery.database_metadata(recovered / "state/database.db", immutable=True), manifest["database"]
        )
        self.assertEqual((recovered / "state/messages.json").read_bytes(), b'{"synthetic":"pre-upgrade"}')
        # Original interrupted DB remains intact; no old application started here.
        self.assertTrue(database.exists())

    def test_repeatable_full_state_rehearsal_and_existing_target_protection(self):
        from scripts.upgrade_rehearsal import run_rehearsal

        target = self.root / "rehearsal"
        result = run_rehearsal(target, "b" * 40, synthetic_only=True)
        self.assertEqual(result["status"], "synthetic-upgrade-verified")
        self.assertTrue(result["recovery_verified"])
        self.assertEqual(result["network_attempts"], 0)
        self.assertEqual(result["historical_release_evidence"], "none; synthetic fixture only")
        before = (target / "RESULT.json").read_bytes()
        with self.assertRaises(FileExistsError):
            run_rehearsal(target, "b" * 40, synthetic_only=True)
        self.assertEqual((target / "RESULT.json").read_bytes(), before)
        self.assertFalse((self.root / "unapproved").exists())
        with self.assertRaises(ValueError):
            run_rehearsal(self.root / "unapproved", "b" * 40, synthetic_only=False)

    def test_optimized_interpreter_cannot_disable_rehearsal_checks(self):
        result = subprocess.run(
            [
                sys.executable,
                "-O",
                "-B",
                "scripts/upgrade_rehearsal.py",
                "--target",
                str(self.root / "unsafe-optimized"),
                "--commit",
                "b" * 40,
                "--synthetic-only",
            ],
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "unsafe-optimized").exists())
