import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import backup_database, restore_database  # noqa: E402
from app.db import schema  # noqa: E402


@contextmanager
def sqlite_conn(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


class DatabaseRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.original_env = {
            key: os.environ.get(key)
            for key in [
                "DRINK_POS_DB",
                "DRINK_POS_BACKUP_DIR",
                "DRINK_POS_ENV",
                "DRINK_POS_MESSAGES",
            ]
        }
        self.original_schema_state = (
            schema.DB_PATH,
            schema.ENV_PIN_CODE,
            schema.ENV_PIN_FROM_ENV,
            schema.get_conn,
        )
        os.environ["DRINK_POS_ENV"] = "production"
        os.environ["DRINK_POS_MESSAGES"] = str(self.root / "messages.json")

    def tearDown(self):
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        schema.configure_runtime(*self.original_schema_state)
        self.temp_dir.cleanup()

    def configure_schema_for(self, db_path: Path) -> None:
        @contextmanager
        def get_test_conn():
            conn = sqlite3.connect(db_path, timeout=15)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

        schema.configure_runtime(str(db_path), "1234", False, get_test_conn)

    def test_readable_old_database_is_migrated(self):
        db_path = self.root / "old-drink-pos.db"
        with sqlite_conn(db_path) as conn:
            conn.execute(
                """
                CREATE TABLE people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                )
                """
            )
            conn.execute("INSERT INTO people (name) VALUES (?)", ("Alt Tester",))
            conn.commit()

        self.configure_schema_for(db_path)
        schema.init_db()

        with sqlite_conn(db_path) as conn:
            people_columns = {row[1] for row in conn.execute("PRAGMA table_info(people)").fetchall()}
            self.assertIn("first_name", people_columns)
            self.assertIn("last_name", people_columns)
            self.assertIn("active", people_columns)
            self.assertIsNotNone(conn.execute("SELECT 1 FROM items LIMIT 1").fetchone())
            self.assertIsNotNone(
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'self_payment_sessions'"
                ).fetchone()
            )

    def test_malformed_database_gets_actionable_startup_error(self):
        db_path = self.root / "drink_pos.db"
        db_path.write_bytes(b"this is not a sqlite database")
        self.configure_schema_for(db_path)

        with self.assertRaises(RuntimeError) as ctx:
            schema.init_db()

        message = str(ctx.exception)
        self.assertIn("not readable", message)
        self.assertIn("not a schema compatibility problem", message)
        self.assertIn("PRAGMA integrity_check", message)

    def test_csv_backup_restore_includes_newer_operational_tables(self):
        source_db = self.root / "drink_pos.db"
        backup_dir = self.root / "backups"
        os.environ["DRINK_POS_DB"] = str(source_db)
        os.environ["DRINK_POS_BACKUP_DIR"] = str(backup_dir)
        self.configure_schema_for(source_db)
        schema.init_db()

        with sqlite_conn(source_db) as conn:
            conn.row_factory = sqlite3.Row
            person_id = conn.execute("SELECT id FROM people ORDER BY id LIMIT 1").fetchone()["id"]
            item_id = conn.execute("SELECT id FROM items ORDER BY id LIMIT 1").fetchone()["id"]
            transaction_id = conn.execute(
                """
                INSERT INTO transactions (person_id, type, total, details, timestamp)
                VALUES (?, 'PAID_CASH', 2.5, 'restore-test', '2026-08-23 10:00:00')
                """,
                (person_id,),
            ).lastrowid
            message_id = conn.execute(
                """
                INSERT INTO member_messages (title, message, active, created_at, archived_at)
                VALUES ('Info', 'Restore me', 1, '2026-08-23 10:00:00', NULL)
                """
            ).lastrowid
            conn.execute(
                """
                INSERT INTO member_message_recipients (message_id, person_id, acknowledged_at)
                VALUES (?, ?, NULL)
                """,
                (message_id, person_id),
            )
            conn.execute(
                """
                INSERT INTO client_operations (client_operation_id, endpoint, transaction_id, client_time, device_info, created_at)
                VALUES ('restore-op-1', '/api/add-drink', ?, '2026-08-23T10:00:00', 'test', '2026-08-23 10:00:00')
                """,
                (transaction_id,),
            )
            conn.execute(
                """
                INSERT INTO self_payment_sessions (
                    person_id, client_payment_id, status, base_amount_cents, card_fee_cents,
                    rounding_mode, rounding_adjustment_cents, amount_eur, amount_cents,
                    currency, provider, provider_checkout_id, revision, terminal_result,
                    terminal_reference, raw_response, error, transaction_id, created_at,
                    updated_at, completed_at
                )
                VALUES (?, 'restore-payment-1', 'paid', 250, 20, 'none', 0, 2.7, 270,
                        'EUR', 'sumup', 'checkout-1', 'rev-1', 'ok', 'terminal-1',
                        '{}', NULL, ?, '2026-08-23 10:00:00',
                        '2026-08-23 10:01:00', '2026-08-23 10:02:00')
                """,
                (person_id, transaction_id),
            )
            conn.execute(
                """
                INSERT INTO paid_round_units (
                    source_order_line_id, payer_person_id, payer_name_snapshot, round_price_eur,
                    payment_transaction_id, event_open, created_at, closed_at
                )
                VALUES (NULL, ?, 'Alt Tester', 10.0, ?, 1, '2026-08-23 10:00:00', NULL)
                """,
                (person_id, transaction_id),
            )
            conn.execute(
                """
                INSERT INTO transaction_items (
                    transaction_id, person_id, item_id, item_name_snapshot, item_short_label_snapshot,
                    quantity, unit_price_eur, unit_purchase_price_eur, total_eur,
                    purchase_total_eur, profit_eur, kind, timestamp
                )
                VALUES (?, ?, ?, 'Bier gross', 'Gross', 1, 2.5, 1.4, 2.5, 1.4, 1.1, 'drink', '2026-08-23 10:00:00')
                """,
                (transaction_id, person_id, item_id),
            )
            conn.execute(
                """
                INSERT INTO round_events (
                    transaction_id, timestamp, round_price_eur, deducted_vk_eur,
                    deducted_purchase_eur, profit_vs_purchase_eur, profit_vs_retail_eur, details
                )
                VALUES (?, '2026-08-23 10:00:00', 10.0, 2.5, 1.4, 8.6, 7.5, 'restore-test')
                """,
                (transaction_id,),
            )
            conn.commit()

        backup_path = backup_database.export_backup()
        restored_db = self.root / "restored.db"
        restore_database.restore_backup(backup_path, restored_db)

        with sqlite_conn(restored_db) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(
                conn.execute("SELECT message FROM member_messages WHERE id = ?", (message_id,)).fetchone()[0],
                "Restore me",
            )
            self.assertEqual(
                conn.execute("SELECT client_payment_id FROM self_payment_sessions").fetchone()[0],
                "restore-payment-1",
            )
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM paid_round_units").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM client_operations").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM round_events").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
