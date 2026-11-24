"""R5-01/02 served reporting reconciliation and exact audit-coverage evidence."""

import csv
import io
import unittest
from unittest.mock import patch

import test_transaction_integrity as fixtures


class ReviewReportingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TransactionIntegrityTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.main = self.fixture.main
        self.client = self.fixture.client
        self.post = self.fixture.post
        self.state = self.fixture.state
        self.person = self.fixture.person
        self.item = self.fixture.item

    def book(self, person=None):
        return self.post("/api/add-drink", {"person_id": person or self.person, "item_id": self.item})

    def prices(self, price, cost):
        self.post(
            "/api/admin/drinks/update",
            {
                "pin": "1234",
                "item_id": self.item,
                "name": self.fixture.fixture.item["name"],
                "short_label": "Gift",
                "price": price,
                "purchase_price": cost,
            },
        )

    def round(self):
        self.post("/api/round-request", {"person_id": self.person, "quantity": 1})
        with self.main.get_conn() as conn:
            return conn.execute("SELECT MAX(id) FROM round_units").fetchone()[0]

    def cancel(self, unit):
        return self.post(
            "/api/admin/rounds/cancel",
            {
                "pin": "1234",
                "round_unit_ids": [unit],
                "correction_operation_id": "review-round-cancel",
                "correction_reason": "synthetic erroneous round",
            },
        )

    def member_request(self, line_id):
        self.post(
            "/api/edit-request",
            {"person_id": self.person, "line_quantities": {str(line_id): 1}, "reason": "synthetic mistake"},
        )
        with self.main.get_conn() as conn:
            return conn.execute("SELECT MAX(id) FROM change_requests").fetchone()[0]

    def approve(self, request_id):
        return self.post(
            "/api/admin/change-request/decide", {"pin": "1234", "request_id": request_id, "decision": "approve"}
        )

    def stats(self):
        return self.post("/api/admin/statistics", {"pin": "1234", "scope": "all", "include_admin_items": True})

    def report(self):
        return self.post("/api/admin/report/preview", {"pin": "1234", "report_type": "profit", "group_by": "none"})

    def assert_coverage(self, ambiguous=0):
        before = self.state()
        result = self.stats()
        self.assertEqual(result["legacy_ambiguous_correction_transactions"], ambiguous)
        self.assertEqual(
            result["historical_correction_coverage"], "unverified" if ambiguous else "new-source-linked-operations"
        )
        self.assertEqual(self.state(), before)

    def assert_round_finance(self, quantity, vk, cost):
        before = self.state()
        report = self.report()
        self.assertEqual(
            report["rows"],
            [
                [
                    quantity,
                    self.main.decimal_comma(vk),
                    "0,00",
                    self.main.decimal_comma(cost),
                    self.main.decimal_comma(-cost),
                ]
            ],
        )
        response = self.client.post(
            "/api/admin/export/report", json={"pin": "1234", "report_type": "profit", "group_by": "none"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        csv_rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(csv_rows, [report["headers"], [str(value) for value in report["rows"][0]]])
        stats = self.stats()
        self.assertEqual(sum(day["vk_value_eur"] for day in stats["finance_by_date"]), vk)
        self.assertEqual(stats["kpis"]["cost_eur"], cost)
        self.assertEqual(stats["kpis"]["profit_eur"], -cost)
        self.assertEqual(stats["kpis"]["revenue_eur"], 0)
        self.assertEqual(stats["rounds"]["deducted_vk_eur"], vk)
        self.assertEqual(stats["rounds"]["deducted_purchase_eur"], cost)
        self.assertEqual(stats["rounds"]["profit_vs_purchase_eur"], -cost)
        self.assertEqual(stats["rounds"]["profit_vs_retail_eur"], -vk)
        round_preview = self.post("/api/admin/report/preview", {"pin": "1234", "report_type": "rounds"})
        round_export = self.client.post("/api/admin/export/report", json={"pin": "1234", "report_type": "rounds"})
        self.assertEqual(round_export.status_code, 200)
        exported = list(csv.reader(io.StringIO(round_export.content.decode("utf-8-sig")), delimiter=";"))
        self.assertEqual(
            exported,
            [round_preview["headers"], *[[str(value) for value in values] for values in round_preview["rows"]]],
        )
        for field, expected in (
            ("deducted_vk_eur", vk),
            ("deducted_ek_eur", cost),
            ("gewinn_ek_zu_rundenpreis_eur", -cost),
            ("gewinn_verlust_vk_zu_rundenpreis_eur", -vk),
        ):
            index = round_preview["headers"].index(field)
            self.assertEqual(sum(float(values[index].replace(",", ".")) for values in round_preview["rows"]), expected)
        self.assertEqual(self.state(), before)

    def reversal_scenario(self, multiple=False):
        self.prices(3, 1)
        self.book()
        people = [self.person]
        if multiple:
            other = self.post(
                "/api/admin/people/create", {"pin": "1234", "first_name": "Review", "last_name": "Other"}
            )["id"]
            self.prices(5, 2.5)
            self.book(other)
            people.append(other)
        unit = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": unit})
        original = self.state()
        self.assert_round_finance(-len(people), 8 if multiple else 3, 3.5 if multiple else 1)
        self.cancel(unit)
        self.assert_round_finance(0, 0, 0)
        self.assertEqual(self.stats()["kpis"]["quantity"], len(people))
        self.assertEqual(self.stats()["kpis"]["gross_quantity"], len(people))
        self.assertEqual(self.stats()["kpis"]["corrected_quantity"], 0)
        current = self.state()
        for table in ("transactions", "transaction_items", "round_events", "round_deductions", "booking_sources"):
            self.assertTrue(set(original[table]).issubset(current[table]), table)
        with self.main.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM transaction_items WHERE kind='CONSUME'").fetchone()[0], len(people)
            )
            for person, price, cost in ((self.person, 3, 1), *([(people[1], 5, 2.5)] if multiple else [])):
                self.assertEqual(
                    tuple(
                        conn.execute(
                            "SELECT quantity,unit_price_eur,unit_purchase_price_eur FROM order_lines WHERE person_id=? AND item_id=?",
                            (person, self.item),
                        ).fetchone()
                    ),
                    (1, price, cost),
                )
        self.cancel(unit)
        self.assertEqual(self.state(), current)
        self.assert_round_finance(0, 0, 0)

    def test_r5_01_deduction_and_reversal_cancel_vk_cost_profit_without_consumption_write(self):
        self.reversal_scenario()

    def test_r5_01_multiple_member_price_cost_snapshots_reconcile(self):
        self.reversal_scenario(multiple=True)

    def test_r5_02_complete_ordinary_admin_and_member_corrections(self):
        self.book()
        self.book()
        response = self.fixture.adjust(1)
        self.assertEqual(response.status_code, 200)
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT id FROM order_lines WHERE quantity>0").fetchone()[0]
        self.approve(self.member_request(line))
        self.assert_coverage()

    def test_r5_02_member_round_approval_before_and_after_deduction_has_complete_parent(self):
        for deduct in (False, True):
            with self.subTest(deduct=deduct):
                if deduct:
                    self.book()
                unit = self.round()
                if deduct:
                    self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": unit})
                with self.main.get_conn() as conn:
                    line = conn.execute(
                        "SELECT original_order_line_id FROM round_units WHERE id=?", (unit,)
                    ).fetchone()[0]
                request = self.member_request(line)
                self.approve(request)
                with self.main.get_conn() as conn:
                    parent = conn.execute(
                        "SELECT transaction_id FROM operation_receipts WHERE operation_id=?",
                        (f"member-decision:{request}",),
                    ).fetchone()[0]
                    self.assertIsNotNone(parent)
                    self.assertEqual(
                        conn.execute("SELECT type FROM transactions WHERE id=?", (parent,)).fetchone()[0],
                        "CHANGE_APPROVED",
                    )
                self.assert_coverage()

    def test_r5_02_direct_and_generic_admin_round_cancellations_are_complete(self):
        unit = self.round()
        self.cancel(unit)
        self.assert_coverage()
        self.book()
        unit = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": unit})
        with self.main.get_conn() as conn:
            round_item = conn.execute(
                "SELECT item_id FROM order_lines WHERE id=(SELECT original_order_line_id FROM round_units WHERE id=?)",
                (unit,),
            ).fetchone()[0]
        self.post(
            "/api/admin/adjust-drink",
            {
                "pin": "1234",
                "person_id": self.person,
                "item_id": round_item,
                "delta": -1,
                "correction_operation_id": "generic-round",
                "correction_purpose": "erroneous_booking",
            },
        )
        self.assert_coverage()

    def test_r5_02_old_t_only_corrections_remain_unverified_even_beside_complete_round(self):
        unit = self.round()
        self.cancel(unit)
        with self.main.get_conn() as conn:
            self.main.log_transaction(conn, self.person, "CHANGE_APPROVED", 0, "old T-only")
            self.main.log_transaction(conn, self.person, "ADMIN_ADJUSTMENT", -3, "old negative T-only")
            conn.commit()
        self.assert_coverage(2)

    def test_r5_02_missing_reversal_is_not_complete(self):
        self.book()
        unit = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": unit})
        self.cancel(unit)
        # Owned synthetic damage only; never relax application guards/migrations.
        with self.main.get_conn() as conn:
            conn.execute("DROP TRIGGER round_reversals_immutable_delete")
            conn.execute("DELETE FROM round_reversals")
            conn.commit()
        self.assert_coverage(1)

    def test_r5_02_partial_ordinary_detail_is_unverified(self):
        self.book()
        self.book()
        self.assertEqual(self.fixture.adjust(2).status_code, 200)
        with self.main.get_conn() as conn:
            conn.execute("DROP TRIGGER correction_details_immutable_delete")
            conn.execute("DELETE FROM correction_details WHERE id=(SELECT MAX(id) FROM correction_details)")
            conn.commit()
        self.assert_coverage(1)

    def test_r5_02_receipt_with_unrelated_parent_cannot_verify_member_approval(self):
        unit = self.round()
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT original_order_line_id FROM round_units WHERE id=?", (unit,)).fetchone()[0]
        request = self.member_request(line)
        self.approve(request)
        self.assert_coverage()
        with self.main.get_conn() as conn:
            conn.execute("DROP TRIGGER operation_receipts_immutable_update")
            unrelated = self.main.log_transaction(conn, None, "CHANGE_APPROVED", 0, "unrelated approval without source")
            conn.execute(
                "UPDATE operation_receipts SET transaction_id=? WHERE operation_id=?",
                (unrelated, f"member-decision:{request}"),
            )
            conn.commit()
        # A receipt rebound to an unrelated approval must not verify either audit.
        self.assert_coverage(3)

    def test_r5_02_null_parent_receipt_is_not_backfilled_or_inferred(self):
        unit = self.round()
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT original_order_line_id FROM round_units WHERE id=?", (unit,)).fetchone()[0]
        request = self.member_request(line)
        self.approve(request)
        with self.main.get_conn() as conn:
            conn.execute("DROP TRIGGER operation_receipts_immutable_update")
            conn.execute(
                "UPDATE operation_receipts SET transaction_id=NULL WHERE operation_id=?",
                (f"member-decision:{request}",),
            )
            conn.commit()
        self.assert_coverage(2)

    def test_r5_02_inconsistent_round_event_and_malformed_receipt_stay_unverified(self):
        self.book()
        unit = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": unit})
        self.cancel(unit)
        self.assert_coverage()
        with self.main.get_conn() as conn:
            event_id = conn.execute("SELECT round_event_id FROM round_reversals").fetchone()[0]
            conn.execute("UPDATE round_events SET deducted_vk_eur=99 WHERE id=?", (event_id,))
            conn.commit()
        self.assert_coverage(1)
        with self.main.get_conn() as conn:
            conn.execute("UPDATE round_events SET deducted_vk_eur=-3 WHERE id=?", (event_id,))
            conn.execute("DROP TRIGGER operation_receipts_immutable_update")
            conn.execute(
                "UPDATE operation_receipts SET payload_json='not-json' WHERE operation_id='review-round-cancel'"
            )
            conn.commit()
        self.assert_coverage(1)

    def test_r5_02_missing_cancellation_detail_is_not_complete(self):
        unit = self.round()
        self.cancel(unit)
        with self.main.get_conn() as conn:
            conn.execute("DROP TRIGGER round_cancellations_immutable_delete")
            conn.execute("DELETE FROM round_cancellations")
            conn.commit()
        self.assert_coverage(1)

    def test_r5_02_missing_operation_receipt_cannot_verify_round(self):
        unit = self.round()
        self.cancel(unit)
        with self.main.get_conn() as conn:
            conn.execute("DROP TRIGGER operation_receipts_immutable_delete")
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("DELETE FROM operation_receipts WHERE operation_id='review-round-cancel'")
            conn.commit()
            self.assertTrue(conn.execute("PRAGMA foreign_key_check").fetchall())
        # Broken independently owned synthetic evidence must not become verified.
        self.assert_coverage(1)

    def test_r5_02_chronological_writes_crossing_seconds_remain_complete(self):
        unit = self.round()
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT original_order_line_id FROM round_units WHERE id=?", (unit,)).fetchone()[0]
        request = self.member_request(line)
        from app.services import corrections
        from app.services import statistics

        # Actual writers intentionally obtain their timestamps independently.
        day = self.main.today_text()
        with (
            patch.object(self.main, "now_text", return_value=f"{day} 00:00:02"),
            patch.object(statistics, "now_text", side_effect=[f"{day} 00:00:00", f"{day} 00:00:01", f"{day} 00:00:03"]),
            patch.object(corrections, "now_text", return_value=f"{day} 00:00:04"),
        ):
            self.approve(request)
        self.assert_coverage()

    def test_r5_02_incomplete_multi_line_round_operation_is_unverified_as_a_whole(self):
        first = self.round()
        self.post(
            "/api/admin/drinks/update",
            {
                "pin": "1234",
                "item_id": self.item,
                "name": self.fixture.fixture.item["name"],
                "price": 3,
                "purchase_price": 1,
            },
        )
        self.post("/api/admin/settings/update", {"pin": "1234", "round_item_price_eur": 12})
        second = self.round()
        with self.main.get_conn() as conn:
            round_item = conn.execute(
                "SELECT item_id FROM order_lines WHERE id=(SELECT original_order_line_id FROM round_units WHERE id=?)",
                (first,),
            ).fetchone()[0]
        self.post(
            "/api/admin/adjust-drink",
            {
                "pin": "1234",
                "person_id": self.person,
                "item_id": round_item,
                "delta": -2,
                "correction_operation_id": "multi-line-round",
                "correction_purpose": "erroneous_booking",
            },
        )
        self.assert_coverage()
        with self.main.get_conn() as conn:
            conn.execute("DROP TRIGGER round_cancellations_immutable_delete")
            conn.execute("DELETE FROM round_cancellations WHERE round_unit_id=?", (second,))
            conn.commit()
        self.assert_coverage(2)

    def test_paid_stored_zero_profit_is_unchanged_by_round_reporting(self):
        self.prices(3, 1)
        self.book()
        self.post("/api/pay", {"pin": "1234", "person_id": self.person})
        with self.main.get_conn() as conn:
            conn.execute("UPDATE transaction_items SET profit_eur=0 WHERE kind='PAID_CASH'")
            paid = [tuple(row) for row in conn.execute("SELECT * FROM transaction_items WHERE kind='PAID_CASH'")]
            conn.commit()
        self.book()
        unit = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": unit})
        self.cancel(unit)
        self.assertEqual(self.stats()["kpis"]["revenue_eur"], 3)
        self.assertEqual(self.stats()["kpis"]["profit_eur"], 0)
        self.assertEqual(self.report()["rows"], [[1, "3,00", "3,00", "1,00", "0,00"]])
        with self.main.get_conn() as conn:
            self.assertEqual(
                [tuple(row) for row in conn.execute("SELECT * FROM transaction_items WHERE kind='PAID_CASH'")], paid
            )
