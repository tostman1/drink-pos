"""DP-002/004/013/024 served financial boundaries, not reconstruction/refunds."""

import csv
import io
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from unittest.mock import patch

import test_financial_history as history_fixtures


class FinancialIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = history_fixtures.FinancialHistoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.legacy = self.fixture.legacy
        self.client = self.fixture.client
        self.post = self.fixture.post
        self.book = self.fixture.book
        self.update = self.fixture.update
        self.person = self.fixture.person
        self.item = self.fixture.item

    def state(self):
        with self.legacy.get_conn() as conn:
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {table: sorted(tuple(r) for r in conn.execute(f'SELECT * FROM "{table}"')) for table in tables}

    def report(self, report_type, **filters):
        return self.post(
            "/api/admin/report/preview", {"pin": "1234", "report_type": report_type, "group_by": "none", **filters}
        )

    def csv_rows(self, path, **payload):
        response = self.client.post(path, json={"pin": "1234", **payload})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        return list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))

    def seed_detail(self, kind, quantity, cost, profit, timestamp="2026-01-15 12:00:00", item_id=None):
        with self.legacy.get_conn() as conn:
            tx = self.legacy.log_transaction(conn, self.person["id"], kind, quantity * 3, "synthetic signed detail")
            self.legacy.log_transaction_item(
                conn,
                tx,
                self.person["id"],
                {
                    "item_id": self.item["id"] if item_id is None else item_id,
                    "item_name_snapshot": self.item["name"],
                    "item_short_label_snapshot": "Gift",
                    "unit_price_eur": 3,
                    "unit_purchase_price_eur": cost,
                },
                quantity,
                kind,
                timestamp=timestamp,
            )
            conn.execute("UPDATE transaction_items SET profit_eur=? WHERE transaction_id=?", (profit, tx))
            conn.commit()

    def test_paid_zero_positive_negative_and_signed_profit_reconcile_like_for_like(self):
        # Deliberately inconsistent originals; paid reports must read, not repair.
        for kind, qty, cost, profit in (
            ("PAID_CASH", 1, 1, 0),
            ("PAID_SUMUP", 1, 5, 0),
            ("PAID_CASH", -1, 1, -0.75),
            ("PAID_SUMUP", 2, 1.234, 1.115),
        ):
            self.seed_detail(kind, qty, cost, profit)
        self.seed_detail("CONSUME", 1, 1, 900)
        self.seed_detail("SYNTHETIC_REFUND", -1, 1, -900)
        before = self.state()
        for kind in ("revenue", "profit"):
            report = self.report(kind, date_from="2026-01-15", date_to="2026-01-15")
            self.assertEqual(report["rows"], [[3, "9,00", "9,00", "7,47", "0,36"]])
        stats = self.post("/api/admin/statistics", {"pin": "1234", "scope": "all", "include_admin_items": True})
        self.assertEqual(stats["kpis"]["profit_eur"], 0.36)
        self.assertEqual(stats["finance_by_date"][0]["profit_eur"], 0.36)
        paid = [
            r
            for r in self.csv_rows("/api/admin/export/item-summary")
            if r["status"] in self.legacy.PAID_TRANSACTION_KINDS
        ]
        self.assertEqual(sum(Decimal(r["profit_eur"].replace(",", ".")) for r in paid), Decimal("0.36"))
        self.assertEqual(self.state(), before)

    def test_round_and_consumption_operational_formulas_remain_distinct(self):
        self.seed_detail("PAID_CASH", 1, 1, 0)
        self.seed_detail("ROUND_DEDUCTED", -1, 1.25, 80)
        self.seed_detail("CONSUME", 2, 1, 70)
        self.assertEqual(self.report("revenue")["rows"], [[1, "3,00", "3,00", "1,00", "0,00"]])
        self.assertEqual(self.report("profit")["rows"], [[0, "6,00", "3,00", "2,25", "-1,25"]])
        self.assertEqual(self.report("consumption")["rows"], [[2, "6,00", "0,00", "2,00", "-2,00"]])
        stats = self.post("/api/admin/statistics", {"pin": "1234", "scope": "all", "include_admin_items": True})
        self.assertEqual(stats["kpis"]["profit_eur"], -1.25)
        self.assertEqual(stats["top_items"][0]["profit_eur"], 4)
        # Raw export is every kind's stored detail, not the round-expense report.
        round_row = next(r for r in self.csv_rows("/api/admin/export/item-summary") if r["status"] == "ROUND_DEDUCTED")
        self.assertEqual(round_row["profit_eur"], "80,00")

    def test_report_period_archive_and_admin_visibility_are_not_redefined(self):
        self.seed_detail("PAID_CASH", 1, 1, 0, "2026-01-01 00:00:00")
        self.seed_detail("PAID_CASH", 1, 1, -7, "2026-01-31 23:59:59")
        self.seed_detail("PAID_SUMUP", 1, 1, 90, "2026-02-01 00:00:00")
        with self.legacy.get_conn() as conn:
            conn.execute(
                "UPDATE items SET admin_only=1,active=0,archived_at='synthetic' WHERE id=?", (self.item["id"],)
            )
            conn.execute("UPDATE people SET active=0,archived_at='synthetic' WHERE id=?", (self.person["id"],))
            conn.commit()
        self.assertEqual(self.report("profit", date_from="2026-01-01", date_to="2026-01-31")["rows"][0][-1], "-7,00")
        for include, expected in ((False, 0), (True, -7)):
            stats = self.post(
                "/api/admin/statistics",
                {
                    "pin": "1234",
                    "scope": "custom",
                    "date_from": "2026-01-01",
                    "date_to": "2026-01-31",
                    "include_admin_items": include,
                },
            )
            self.assertEqual(stats["kpis"]["profit_eur"], expected)
        preview = self.report("profit", date_from="2026-01-01", date_to="2026-01-31")
        exported = self.csv_rows(
            "/api/admin/export/report",
            report_type="profit",
            group_by="none",
            date_from="2026-01-01",
            date_to="2026-01-31",
        )
        self.assertEqual(list(exported[0].values()), [str(v) for v in preview["rows"][0]])

    def test_stored_profit_helper_distinguishes_zero_none_and_unavailable(self):
        for row, expected in (
            ({"profit_eur": 0}, 0),
            ({"profit_eur": -0.0}, 0),
            ({"profit_eur": -1.123}, -1.123),
            ({"profit_eur": None}, 2),
            ({}, 2),
        ):
            with self.subTest(row=row):
                self.assertEqual(self.legacy.recorded_paid_profit(row, revenue=3, cost=1), expected)
        with sqlite3.connect(":memory:") as conn:
            conn.row_factory = sqlite3.Row
            for sql, expected in (
                ("SELECT 0 AS profit_eur", 0),
                ("SELECT NULL AS profit_eur", 2),
                ("SELECT 1 AS other", 2),
            ):
                self.assertEqual(
                    self.legacy.recorded_paid_profit(conn.execute(sql).fetchone(), revenue=3, cost=1), expected
                )

    def test_master_edit_repeated_unchanged_and_archived_rows_preserve_all_history(self):
        self.book()
        self.post("/api/pay", {"pin": "1234", "person_id": self.person["id"]})
        self.book()
        self.seed_detail("ROUND_DEDUCTED", -1, 0, 11)
        self.seed_detail("PAID_CASH", 1, 2, -9)
        with self.legacy.get_conn() as conn:
            conn.execute("UPDATE order_lines SET event_open=0")
            conn.execute("UPDATE people SET active=0,archived_at='synthetic' WHERE id=?", (self.person["id"],))
            conn.execute("UPDATE sqlite_sequence SET seq=seq+100 WHERE name='transactions'")
            conn.commit()
        original = self.state()
        for cost in (1.25, 1.25, 2, 0):
            before = self.state()
            self.update(cost)
            after = self.state()
            for table in before.keys() - {"items", "transactions", "sqlite_sequence"}:
                self.assertEqual(after[table], before[table], table)
            self.assertEqual(after["transactions"][:-1], before["transactions"])
            self.assertEqual(after["transactions"][-1][2], "ITEM_UPDATED")
        self.assertEqual(self.state()["transaction_items"], original["transaction_items"])
        self.assertEqual(self.state()["order_lines"], original["order_lines"])
        with self.legacy.get_conn() as conn:
            conn.execute("UPDATE items SET active=0,archived_at='synthetic' WHERE id=?", (self.item["id"],))
            conn.commit()
        archived = self.state()
        response = self.client.post(
            "/api/admin/drinks/update",
            json={
                "pin": "1234",
                "item_id": self.item["id"],
                "name": self.item["name"],
                "price": 3,
                "purchase_price": 9,
            },
        )
        self.assertEqual(response.status_code, 400)  # Existing archived-master API contract.
        self.legacy.startup()
        self.assertEqual(self.state(), archived)

    def test_startup_failure_and_repeated_startup_do_not_change_financial_state(self):
        self.book()
        self.update(1.25)
        before = self.state()
        with patch.object(
            self.legacy.schema_service,
            "ensure_indexes",
            side_effect=sqlite3.OperationalError("synthetic startup failure"),
        ):
            with self.assertRaises(sqlite3.OperationalError):
                self.legacy.startup()
        self.assertEqual(self.state(), before)
        for _ in range(3):
            self.legacy.startup()
            self.assertEqual(self.state(), before)

    def test_missing_default_initialization_does_not_replace_existing_zero(self):
        with self.legacy.get_conn() as conn:
            conn.execute("UPDATE items SET purchase_price_eur=0 WHERE name='Bier gross'")
            conn.execute("DELETE FROM items WHERE name='Bier klein'")
            conn.commit()
        self.legacy.startup()
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT purchase_price_eur FROM items WHERE name='Bier gross'").fetchone()[0], 0
            )
            self.assertEqual(
                conn.execute("SELECT purchase_price_eur FROM items WHERE name='Bier klein'").fetchone()[0], 1
            )

    def test_real_audit_insert_failure_rolls_back_master_and_all_state(self):
        self.book()
        with self.legacy.get_conn() as conn:
            conn.execute(
                "CREATE TRIGGER synthetic_audit_fault BEFORE INSERT ON transactions WHEN NEW.type='ITEM_UPDATED' BEGIN SELECT RAISE(ABORT,'synthetic audit insertion'); END"
            )
            conn.commit()
        before = self.state()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "synthetic audit insertion"):
            self.update(1.25)
        self.assertEqual(self.state(), before)

    def test_concurrent_master_edit_and_booking_snapshot_one_committed_cost(self):
        self.book()
        before = self.state()["transaction_items"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            edit = pool.submit(self.update, 1.25)
            booking = pool.submit(self.book)
            edit.result()
            booking.result()
        with self.legacy.get_conn() as conn:
            rows = [dict(r) for r in conn.execute("SELECT * FROM transaction_items ORDER BY id")]
            self.assertIn(rows[-1]["unit_purchase_price_eur"], (0, 1.25))
            self.assertEqual(rows[-1]["purchase_total_eur"], rows[-1]["unit_purchase_price_eur"])
        self.assertEqual(self.state()["transaction_items"][: len(before)], before)

    def test_paid_detail_insert_failure_rolls_back_debt_payment_and_entitlements(self):
        self.book()
        self.post("/api/round-request", {"person_id": self.person["id"], "quantity": 1})
        with self.legacy.get_conn() as conn:
            conn.execute(
                "CREATE TRIGGER synthetic_paid_detail_fault BEFORE INSERT ON transaction_items WHEN NEW.kind='PAID_CASH' BEGIN SELECT RAISE(ABORT,'synthetic detail insertion'); END"
            )
            conn.commit()
        before = self.state()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "synthetic detail insertion"):
            self.post("/api/pay", {"pin": "1234", "person_id": self.person["id"]})
        self.assertEqual(self.state(), before)

    def test_synthetic_end_to_end_both_modes_and_independent_recovery(self):
        from scripts.financial_rehearsal import run_rehearsal

        result = run_rehearsal(self.fixture.root / "full-scenario", "b" * 40, synthetic_only=True)
        self.assertEqual(result["status"], "synthetic-financial-integrity-verified")
        self.assertEqual(result["network_attempts"], 0)
        self.assertTrue(result["recovery_verified"])
        self.assertTrue(result["versioned_adoption_verified"])
        self.assertEqual(result["original_tables_preserved"], 17)


class CorrectionAuditTests(unittest.TestCase):
    def setUp(self):
        self.fixture = FinancialIntegrityTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        self.post = self.fixture.post
        self.legacy = self.fixture.legacy
        self.person = self.fixture.person
        self.item = self.fixture.item
        self.fixture.book()
        self.fixture.book()
        with self.legacy.get_conn() as conn:
            self.line = dict(conn.execute("SELECT * FROM order_lines").fetchone())

    def request(self, qty=1):
        self.post(
            "/api/edit-request",
            {
                "person_id": self.person["id"],
                "line_quantities": {str(self.line["id"]): qty},
                "reason": "synthetic correction",
            },
        )
        with self.legacy.get_conn() as conn:
            return conn.execute("SELECT MAX(id) FROM change_requests").fetchone()[0]

    def decide(self, request_id, decision="approve", pin="1234"):
        return self.client.post(
            "/api/admin/change-request/decide", json={"pin": pin, "request_id": request_id, "decision": decision}
        )

    def test_request_approval_replay_and_consumption_gap(self):
        before = self.fixture.state()
        request_id = self.request()
        pending = self.fixture.state()
        self.assertEqual(pending["order_lines"], before["order_lines"])
        self.assertEqual(pending["transaction_items"], before["transaction_items"])
        self.assertEqual(pending["transactions"][-1][2:4], ("CHANGE_REQUEST", 0))
        self.assertEqual(self.decide(request_id, pin="wrong").status_code, 403)
        self.assertEqual(self.fixture.state(), pending)
        self.assertEqual(self.decide(request_id).status_code, 200)
        after = self.fixture.state()
        self.assertEqual(after["transaction_items"], before["transaction_items"])
        self.assertEqual(after["transactions"][-1][2:4], ("CHANGE_APPROVED", 0))
        self.assertEqual(self.client.get(f"/api/kassa/person/{self.person['id']}").json()["total"], 3)
        self.assertEqual(self.fixture.report("consumption")["rows"][0][0], 2)
        self.assertEqual(self.decide(request_id).status_code, 400)
        self.assertEqual(self.fixture.state(), after)

    def test_rejection_and_duplicate_pending_capacity_do_not_change_debt(self):
        request_id = self.request(2)
        before = self.fixture.state()
        duplicate = self.client.post(
            "/api/edit-request", json={"person_id": self.person["id"], "line_quantities": {str(self.line["id"]): 1}}
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(self.fixture.state(), before)
        self.assertEqual(self.decide(request_id, "reject").status_code, 200)
        self.assertEqual(self.client.get(f"/api/kassa/person/{self.person['id']}").json()["total"], 6)

    def test_negative_admin_adjustment_caps_latest_debt_and_is_not_idempotent(self):
        # New selling price creates a separate remaining snapshot, removed first.
        self.post(
            "/api/admin/drinks/update",
            {"pin": "1234", "item_id": self.item["id"], "name": self.item["name"], "price": 5, "purchase_price": 1},
        )
        self.fixture.book()
        before = self.fixture.state()["transaction_items"]
        payload = {"pin": "1234", "person_id": self.person["id"], "item_id": self.item["id"], "delta": -1}
        self.post("/api/admin/adjust-drink", payload)
        self.assertEqual(self.client.get(f"/api/kassa/person/{self.person['id']}").json()["total"], 6)
        self.post("/api/admin/adjust-drink", payload)
        self.assertEqual(self.client.get(f"/api/kassa/person/{self.person['id']}").json()["total"], 3)
        self.post("/api/admin/adjust-drink", {**payload, "delta": -10})
        self.assertEqual(self.fixture.state()["transaction_items"], before)
        self.assertEqual(self.client.post("/api/admin/adjust-drink", json=payload).status_code, 400)
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                [r[0] for r in conn.execute("SELECT total FROM transactions WHERE type='ADMIN_ADJUSTMENT'")],
                [-5, -3, -3],
            )
            self.assertTrue(all(r[0] >= 0 for r in conn.execute("SELECT quantity FROM order_lines")))

    def test_approval_rejects_insufficient_remaining_quantity_without_partial_audit(self):
        request_id = self.request(2)
        self.post(
            "/api/admin/adjust-drink",
            {"pin": "1234", "person_id": self.person["id"], "item_id": self.item["id"], "delta": -1},
        )
        before = self.fixture.state()
        self.assertEqual(self.decide(request_id).status_code, 400)
        self.assertEqual(self.fixture.state(), before)

    def test_payment_resolves_pending_and_audits_only_remaining_paid_quantity(self):
        self.request()
        result = self.post("/api/pay", {"pin": "1234", "person_id": self.person["id"], "approve_pending": True})
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["pending_handled"], 1)
        with self.legacy.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT status FROM change_requests").fetchone()[0], "APPROVED")
            self.assertEqual(
                conn.execute("SELECT quantity FROM transaction_items WHERE kind='PAID_CASH'").fetchone()[0], 1
            )
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transaction_items WHERE quantity<0").fetchone()[0], 0)

    def test_payment_without_remaining_lines_commits_resolution_before_error(self):
        self.request(2)
        response = self.client.post(
            "/api/pay", json={"pin": "1234", "person_id": self.person["id"], "approve_pending": True}
        )
        self.assertEqual(response.status_code, 400)
        with self.legacy.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT status FROM change_requests").fetchone()[0], "APPROVED")
            self.assertEqual(conn.execute("SELECT SUM(quantity) FROM order_lines").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions WHERE type='PAID_CASH'").fetchone()[0], 0)

    def test_audit_failure_rolls_back_request_decision_adjustment_and_payment(self):
        request_id = self.request()
        calls = (
            ("CHANGE_APPROVED", lambda: self.decide(request_id)),
            (
                "ADMIN_ADJUSTMENT",
                lambda: self.client.post(
                    "/api/admin/adjust-drink",
                    json={"pin": "1234", "person_id": self.person["id"], "item_id": self.item["id"], "delta": -1},
                ),
            ),
            (
                "PAID_CASH",
                lambda: self.client.post(
                    "/api/pay", json={"pin": "1234", "person_id": self.person["id"], "approve_pending": True}
                ),
            ),
        )
        for kind, call in calls:
            with self.subTest(kind=kind):
                with self.legacy.get_conn() as conn:
                    conn.execute(
                        f"CREATE TRIGGER synthetic_correction_fault BEFORE INSERT ON transactions WHEN NEW.type='{kind}' BEGIN SELECT RAISE(ABORT,'synthetic correction audit'); END"
                    )
                    conn.commit()
                before = self.fixture.state()
                with self.assertRaisesRegex(sqlite3.IntegrityError, "synthetic correction audit"):
                    call()
                self.assertEqual(self.fixture.state(), before)
                with self.legacy.get_conn() as conn:
                    conn.execute("DROP TRIGGER synthetic_correction_fault")
                    conn.commit()

    def test_request_audit_failure_rolls_back_pending_insert(self):
        before = self.fixture.state()
        with patch.object(self.legacy, "log_transaction", side_effect=RuntimeError("synthetic request audit")):
            with self.assertRaises(RuntimeError):
                self.request()
        self.assertEqual(self.fixture.state(), before)

    def test_active_payment_blocks_correction_and_resolution_without_partial_writes(self):
        request_id = self.request()
        with self.legacy.get_conn() as conn:
            conn.execute(
                "INSERT INTO self_payment_sessions(person_id,client_payment_id,status,amount_eur,amount_cents,revision,created_at,updated_at) VALUES(?,'synthetic-active','PENDING',6,600,'synthetic','2099-01-01','2099-01-01')",
                (self.person["id"],),
            )
            conn.commit()
        before = self.fixture.state()
        self.assertEqual(self.decide(request_id).status_code, 409)
        self.assertEqual(
            self.client.post(
                "/api/admin/adjust-drink",
                json={"pin": "1234", "person_id": self.person["id"], "item_id": self.item["id"], "delta": -1},
            ).status_code,
            409,
        )
        self.assertEqual(
            self.client.post(
                "/api/pay", json={"pin": "1234", "person_id": self.person["id"], "approve_pending": True}
            ).status_code,
            409,
        )
        self.assertEqual(self.fixture.state(), before)

    def test_remove_helper_retains_snapshot_caps_quantity_and_rejects_nonpositive(self):
        from fastapi import HTTPException

        with self.legacy.get_conn() as conn:
            for qty in (0, -1):
                with self.assertRaises(HTTPException):
                    self.legacy.remove_from_order_line(conn, self.line["id"], qty)
            original, actual = self.legacy.remove_from_order_line(conn, self.line["id"], 10)
            self.assertEqual(dict(original), self.line)
            self.assertEqual(actual, 2)
            after = dict(conn.execute("SELECT * FROM order_lines WHERE id=?", (self.line["id"],)).fetchone())
            for key in self.line.keys() - {"quantity", "updated_at"}:
                self.assertEqual(after[key], self.line[key])
            self.assertEqual(self.legacy.remove_from_order_line(conn, self.line["id"], 1)[1], 0)
            conn.rollback()
