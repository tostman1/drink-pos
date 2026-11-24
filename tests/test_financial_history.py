"""RL-04 recorded snapshot preservation; RL-03 former failures retained in docs."""

import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts.financial_schema_inventory import derive
from scripts.standard_checks import test_environment


class FinancialHistoryTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="drink-pos-rl03-")))
        self.stack.enter_context(patch.dict(os.environ, test_environment(self.root), clear=True))
        from app import application
        from app.db import schema

        self.stack.callback(
            schema.configure_runtime, schema.DB_PATH, schema.ENV_PIN_CODE, schema.ENV_PIN_FROM_ENV, schema.get_conn
        )
        app, self.legacy = application.create_app("app")
        self.client = self.stack.enter_context(TestClient(app))
        self.person = self.client.get("/api/people").json()[0]
        self.item = self.post(
            "/api/admin/drinks/create",
            {"pin": "1234", "name": "Synthetic gift", "short_label": "Gift", "price": "3,00", "purchase_price": 0},
        )
        with self.legacy.get_conn() as conn:
            self.item = dict(conn.execute("SELECT * FROM items WHERE name='Synthetic gift'").fetchone())

    def post(self, path, payload):
        response = self.client.post(path, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def book(self):
        return self.post("/api/add-drink", {"person_id": self.person["id"], "item_id": self.item["id"]})

    def update(self, cost):
        return self.post(
            "/api/admin/drinks/update",
            {
                "pin": "1234",
                "item_id": self.item["id"],
                "name": self.item["name"],
                "short_label": "Gift",
                "price": 3,
                "purchase_price": cost,
                "sort_order": 100,
                "active": True,
                "admin_only": False,
            },
        )

    def test_served_item_update_preserves_legitimate_zero_even_in_versioned_mode(self):
        self.book()
        self.post("/api/pay", {"pin": "1234", "person_id": self.person["id"]})
        self.book()
        with self.legacy.get_conn() as conn:
            before = [tuple(r) for r in conn.execute("SELECT * FROM transactions")]
            line_dates = [tuple(r) for r in conn.execute("SELECT id,created_at,updated_at FROM order_lines")]
            conn.execute("PRAGMA journal_mode=DELETE")
        from app.db import migrations

        migrations.migrate(Path(self.legacy.DB_PATH), adopt_legacy=True)
        self.assertEqual(migrations.inspect(Path(self.legacy.DB_PATH))["state"], "versioned-current")
        with patch.dict(os.environ, {"DRINK_POS_MIGRATION_MODE": "versioned"}):
            self.update("1,25")
        with self.legacy.get_conn() as conn:
            self.assertEqual([r[0] for r in conn.execute("SELECT unit_purchase_price_eur FROM order_lines")], [0, 0])
            self.assertEqual(
                [
                    tuple(r)
                    for r in conn.execute(
                        "SELECT unit_purchase_price_eur,purchase_total_eur,profit_eur FROM transaction_items"
                    )
                ],
                [(0, 0, 3)] * 3,
            )
            self.assertEqual([tuple(r) for r in conn.execute("SELECT * FROM transactions ORDER BY id")][:-1], before)
            self.assertEqual(
                [tuple(r) for r in conn.execute("SELECT id,created_at,updated_at FROM order_lines")], line_dates
            )
        self.update(2)
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT DISTINCT unit_purchase_price_eur FROM transaction_items").fetchall()[0][0], 0
            )
        self.book()
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT unit_purchase_price_eur FROM order_lines ORDER BY id DESC LIMIT 1").fetchone()[0],
                2,
            )

    def test_startup_preserves_signed_details_null_ids_round_events_and_event_lines(self):
        self.book()
        with self.legacy.get_conn() as conn:
            line = dict(conn.execute("SELECT * FROM order_lines").fetchone())
            for item_id, kind in (
                (self.item["id"], "ROUND_DEDUCTED"),
                (None, "ROUND_DEDUCTED"),
                (self.item["id"], "SYNTHETIC_REFUND"),
            ):
                tx = self.legacy.log_transaction(conn, self.person["id"], kind, -3, "synthetic")
                self.legacy.log_transaction_item(conn, tx, self.person["id"], {**line, "item_id": item_id}, -1, kind)
            conn.execute(
                "INSERT INTO round_events(timestamp,round_price_eur,deducted_vk_eur,deducted_purchase_eur,profit_vs_purchase_eur,profit_vs_retail_eur) VALUES('then',10,3,0,10,7)"
            )
            conn.execute(
                "INSERT INTO event_sessions(name,start_time,created_at,updated_at) VALUES('Synthetic','then','then','then')"
            )
            conn.execute(
                "INSERT INTO event_lines(event_id,item_id,item_name_snapshot,item_short_label_snapshot,quantity,unit_price_eur,unit_purchase_price_eur,created_at,updated_at) VALUES(1,?,'Synthetic gift','Gift',1,3,0,'then','then')",
                (self.item["id"],),
            )
            conn.execute("UPDATE items SET purchase_price_eur=1.25 WHERE id=?", (self.item["id"],))
            conn.commit()
        self.legacy.init_db()
        with self.legacy.get_conn() as conn:
            rows = [
                tuple(r)
                for r in conn.execute(
                    "SELECT quantity,unit_purchase_price_eur,purchase_total_eur,profit_eur FROM transaction_items WHERE quantity<0 ORDER BY id"
                )
            ]
            self.assertEqual(rows, [(-1, 0, 0, -3)] * 3)
            self.assertEqual(conn.execute("SELECT deducted_purchase_eur FROM round_events").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT unit_purchase_price_eur FROM event_lines").fetchone()[0], 0)

    def test_startup_preserves_nonzero_round_audit_without_correction_record(self):
        with self.legacy.get_conn() as conn:
            item = conn.execute("SELECT * FROM items WHERE name='1 Runde'").fetchone()
            line_id = self.legacy.add_order_line(conn, self.person["id"], item)
            line = dict(conn.execute("SELECT * FROM order_lines WHERE id=?", (line_id,)).fetchone())
            tx = self.legacy.log_transaction(conn, self.person["id"], "ROUND_REQUEST_APPROVED", 10, "synthetic")
            self.legacy.log_transaction_item(
                conn, tx, self.person["id"], {**line, "unit_purchase_price_eur": 4}, 1, "ROUND_REQUEST_APPROVED"
            )
            conn.execute("UPDATE order_lines SET unit_purchase_price_eur=4 WHERE id=?", (line_id,))
            before = [tuple(r) for r in conn.execute("SELECT * FROM transactions")]
            conn.commit()
        self.legacy.init_db()
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                tuple(
                    conn.execute(
                        "SELECT unit_purchase_price_eur,purchase_total_eur,profit_eur,total_eur FROM transaction_items"
                    ).fetchone()
                ),
                (0, 0, line["unit_price_eur"], line["unit_price_eur"]),
            )
            self.assertEqual([tuple(r) for r in conn.execute("SELECT * FROM transactions")], before)

    def test_report_zero_profit_fallback_is_read_time_not_a_database_write(self):
        self.book()
        self.post("/api/pay", {"pin": "1234", "person_id": self.person["id"]})
        with self.legacy.get_conn() as conn:
            conn.execute(
                "UPDATE transaction_items SET unit_purchase_price_eur=1,purchase_total_eur=1,profit_eur=0 WHERE kind='PAID_CASH'"
            )
            conn.commit()
        result = self.post("/api/admin/statistics", {"pin": "1234", "scope": "all", "include_admin_items": True})
        self.assertEqual(result["kpis"]["profit_eur"], 2)
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT profit_eur FROM transaction_items WHERE kind='PAID_CASH'").fetchone()[0], 0
            )

    def test_member_and_admin_negative_corrections_do_not_append_signed_item_details(self):
        self.book()
        with self.legacy.get_conn() as conn:
            line_id = conn.execute("SELECT id FROM order_lines").fetchone()[0]
        self.post("/api/edit-request", {"person_id": self.person["id"], "line_quantities": {str(line_id): 1}})
        with self.legacy.get_conn() as conn:
            request_id = conn.execute("SELECT id FROM change_requests").fetchone()[0]
        self.post("/api/admin/change-request/decide", {"pin": "1234", "request_id": request_id, "decision": "approve"})
        self.book()
        self.post(
            "/api/admin/adjust-drink",
            {"pin": "1234", "person_id": self.person["id"], "item_id": self.item["id"], "delta": -1},
        )
        with self.legacy.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transaction_items WHERE quantity<0").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT SUM(quantity) FROM order_lines").fetchone()[0], 0)
            self.assertEqual(
                conn.execute("SELECT total FROM transactions WHERE type='ADMIN_ADJUSTMENT'").fetchone()[0], -3
            )

    def test_legacy_default_item_existing_zero_master_cost_is_preserved(self):
        with self.legacy.get_conn() as conn:
            conn.execute("UPDATE items SET purchase_price_eur=0 WHERE name='Bier gross'")
            conn.commit()
        self.legacy.init_db()
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT purchase_price_eur FROM items WHERE name='Bier gross'").fetchone()[0], 0
            )

    def test_item_update_rolls_back_and_preserves_history_when_audit_fails(self):
        self.book()
        with patch.object(self.legacy, "log_transaction", side_effect=RuntimeError("synthetic audit fault")):
            with self.assertRaisesRegex(RuntimeError, "synthetic audit fault"):
                self.update(1.25)
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT purchase_price_eur FROM items WHERE id=?", (self.item["id"],)).fetchone()[0], 0
            )
            self.assertEqual(
                tuple(
                    conn.execute(
                        "SELECT unit_purchase_price_eur,purchase_total_eur,profit_eur FROM transaction_items"
                    ).fetchone()
                ),
                (0, 0, 3),
            )
            self.assertEqual(conn.execute("SELECT unit_purchase_price_eur FROM order_lines").fetchone()[0], 0)


class FinancialSchemaEvidenceTests(unittest.TestCase):
    def test_independent_literal_ddl_matches_current_baseline_without_imports(self):
        from app.db.migrations import BASELINE_SCHEMA

        source = (Path(__file__).resolve().parents[1] / "app/db/schema.py").read_text(encoding="utf-8")
        with patch("builtins.exec", side_effect=AssertionError("No source execution")):
            result = derive(source)
        self.assertEqual(result["schema_sha256"], BASELINE_SCHEMA)
        self.assertEqual(len(result["tables"]), 17)

    def test_unsupported_dynamic_schema_fails_instead_of_inventing_evidence(self):
        with self.assertRaises(ValueError):
            derive("def init_db(): pass\ndef ensure_indexes(): indexes = dynamic()")

    def test_ddl_upgrade_path_is_not_equivalent_to_fresh_source_schema(self):
        old = """def init_db(conn):
 conn.execute('CREATE TABLE IF NOT EXISTS sample(id INTEGER, amount REAL)')
def ensure_indexes(conn):
 indexes = []
"""
        new = """def init_db(conn):
 conn.execute('CREATE TABLE IF NOT EXISTS sample(id INTEGER, fee REAL DEFAULT 0, amount REAL)')
 add_column_if_missing(conn, 'sample', 'fee REAL DEFAULT 0')
def ensure_indexes(conn):
 indexes = []
"""
        self.assertNotEqual(derive(new)["schema_sha256"], derive(old, new)["schema_sha256"])
        self.assertEqual([r[1] for r in derive(old, new)["tables"]["sample"]["columns"]], ["id", "amount", "fee"])
