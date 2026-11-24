"""RL-05 approved net consumption and append-only correction/round contracts."""

import sqlite3
import unittest
import subprocess
import sys
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor

import test_financial_history as fixtures


class TransactionIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.FinancialHistoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.client = self.fixture.client
        self.main = self.fixture.legacy
        self.person = self.fixture.person["id"]
        self.item = self.fixture.item["id"]
        self.post = self.fixture.post

    def book(self, count=1):
        for _ in range(count):
            self.fixture.book()

    def adjust(self, quantity, operation="rl05-adjust", **changes):
        return self.client.post(
            "/api/admin/adjust-drink",
            json={
                "pin": "1234",
                "person_id": self.person,
                "item_id": self.item,
                "delta": -quantity,
                "correction_operation_id": operation,
                "correction_purpose": "erroneous_booking",
                "correction_reason": "synthetic mistake",
                **changes,
            },
        )

    def state(self):
        with self.main.get_conn() as conn:
            return {
                r[0]: sorted((tuple(row) for row in conn.execute(f'SELECT * FROM "{r[0]}"')), key=repr)
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }

    def statistics(self):
        return self.post("/api/admin/statistics", {"pin": "1234", "scope": "all"})

    def test_five_booked_two_corrected_net_three_and_original_history_preserved(self):
        self.book(5)
        before = self.state()
        result = self.adjust(2)
        self.assertEqual(result.status_code, 200, result.text)
        after = self.state()
        self.assertEqual(after["transaction_items"][: len(before["transaction_items"])], before["transaction_items"])
        stats = self.statistics()
        self.assertEqual(stats["kpis"]["quantity"], 3)
        self.assertEqual(stats["kpis"]["gross_quantity"], 5)
        self.assertEqual(stats["kpis"]["corrected_quantity"], 2)
        self.assertEqual(stats["top_items"][0]["quantity"], 3)
        with self.main.get_conn() as conn:
            rows = conn.execute(
                "SELECT quantity,total_eur,purchase_total_eur,profit_eur FROM transaction_items WHERE kind='CONSUMPTION_CORRECTION'"
            ).fetchall()
            self.assertEqual(sum(r[0] for r in rows), -2)
            self.assertEqual(sum(r[1] for r in rows), -6)
            self.assertEqual(sum(r[2] for r in rows), 0)

    def test_admin_replay_conflict_and_unkeyed_policy(self):
        self.book(5)
        first = self.adjust(2)
        self.assertEqual(first.status_code, 200)
        before = self.state()
        replay = self.adjust(2)
        self.assertEqual(replay.json(), first.json())
        self.assertEqual(self.state(), before)
        self.assertEqual(self.adjust(1).status_code, 409)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.adjust(1, operation=None).status_code, 400)
        self.assertEqual(self.state(), before)

    def test_concurrent_same_key_has_exactly_one_effect(self):
        self.book(5)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.adjust(2), range(2)))
        self.assertTrue(all(r.status_code == 200 for r in results))
        self.assertEqual(results[0].json(), results[1].json())
        self.assertEqual(self.statistics()["kpis"]["quantity"], 3)

    def test_member_approval_replay_and_opposing_decision_conflict(self):
        self.book(5)
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT id FROM order_lines").fetchone()[0]
        self.post(
            "/api/edit-request",
            {"person_id": self.person, "line_quantities": {str(line): 2}, "correction_operation_id": "member-request"},
        )
        with self.main.get_conn() as conn:
            request = conn.execute("SELECT id FROM change_requests").fetchone()[0]
        payload = {"pin": "1234", "request_id": request, "decision": "approve"}
        first = self.post("/api/admin/change-request/decide", payload)
        before = self.state()
        self.assertEqual(self.post("/api/admin/change-request/decide", payload), first)
        self.assertEqual(self.state(), before)
        self.assertEqual(
            self.client.post("/api/admin/change-request/decide", json={**payload, "decision": "reject"}).status_code,
            409,
        )
        self.assertEqual(self.statistics()["kpis"]["quantity"], 3)

    def test_payment_correction_only_success_and_replay_without_fake_payment(self):
        self.book()
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT id FROM order_lines").fetchone()[0]
        self.post("/api/edit-request", {"person_id": self.person, "line_quantities": {str(line): 1}})
        payload = {
            "pin": "1234",
            "person_id": self.person,
            "approve_pending": True,
            "payment_operation_id": "cash-correction-only",
        }
        result = self.post("/api/pay", payload)
        self.assertEqual(result["status"], "correction_only")
        self.assertEqual(result["total"], 0)
        before = self.state()
        self.assertEqual(self.post("/api/pay", payload), result)
        self.assertEqual(self.state(), before)
        with self.main.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions WHERE type='PAID_CASH'").fetchone()[0], 0)

    def test_correction_only_mode_reports_remaining_payment_required(self):
        self.book(3)
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT id FROM order_lines").fetchone()[0]
        self.post("/api/edit-request", {"person_id": self.person, "line_quantities": {str(line): 1}})
        result = self.post(
            "/api/pay",
            {
                "pin": "1234",
                "person_id": self.person,
                "approve_pending": True,
                "corrections_only": True,
                "payment_operation_id": "resolution-only",
            },
        )
        self.assertEqual(result["status"], "corrections_applied")
        self.assertTrue(result["payment_required"])
        self.assertEqual(result["total"], 6)
        with self.main.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions WHERE type='PAID_CASH'").fetchone()[0], 0)

    def test_correction_fault_rolls_back_all_state(self):
        self.book(5)
        with self.main.get_conn() as conn:
            conn.execute(
                "CREATE TRIGGER synthetic_fault BEFORE INSERT ON correction_details BEGIN SELECT RAISE(ABORT,'synthetic detail fault'); END"
            )
            conn.commit()
        before = self.state()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "synthetic detail fault"):
            self.adjust(2)
        self.assertEqual(self.state(), before)

    def test_failure_at_each_ordinary_correction_write_rolls_back_and_can_retry(self):
        self.book(5)
        for table, action in (
            ("order_lines", "UPDATE"),
            ("transactions", "INSERT"),
            ("transaction_items", "INSERT"),
            ("correction_details", "INSERT"),
            ("operation_receipts", "INSERT"),
        ):
            with self.subTest(table=table):
                with self.main.get_conn() as conn:
                    conn.execute(
                        f"CREATE TRIGGER synthetic_correction_fault BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'synthetic write fault'); END"
                    )
                    conn.commit()
                before = self.state()
                with self.assertRaisesRegex(sqlite3.IntegrityError, "synthetic write fault"):
                    self.adjust(2)
                self.assertEqual(self.state(), before)
                with self.main.get_conn() as conn:
                    conn.execute("DROP TRIGGER synthetic_correction_fault")
                    conn.commit()
        self.assertEqual(self.adjust(2).status_code, 200)

    def test_payment_after_correction_replay_and_late_failure(self):
        self.book(5)
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT id FROM order_lines").fetchone()[0]
        self.post("/api/edit-request", {"person_id": self.person, "line_quantities": {str(line): 2}})
        with self.main.get_conn() as conn:
            conn.execute(
                "CREATE TRIGGER synthetic_payment_fault BEFORE INSERT ON transaction_items WHEN NEW.kind='PAID_CASH' BEGIN SELECT RAISE(ABORT,'late payment fault'); END"
            )
            conn.commit()
        before = self.state()
        payload = {
            "pin": "1234",
            "person_id": self.person,
            "approve_pending": True,
            "payment_operation_id": "pay-after-correction",
        }
        with self.assertRaisesRegex(sqlite3.IntegrityError, "late payment fault"):
            self.client.post("/api/pay", json=payload)
        self.assertEqual(self.state(), before)
        with self.main.get_conn() as conn:
            conn.execute("DROP TRIGGER synthetic_payment_fault")
            conn.commit()
        result = self.post("/api/pay", payload)
        self.assertEqual(result["total"], 9)
        before = self.state()
        self.assertEqual(self.post("/api/pay", payload), result)
        self.assertEqual(self.state(), before)

    def test_concurrent_distinct_overlapping_corrections_do_not_overdraw(self):
        self.book(3)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda key: self.adjust(2, key), ("first", "second")))
        self.assertTrue(all(r.status_code == 200 for r in results))
        self.assertEqual(self.statistics()["kpis"]["quantity"], 0)
        with self.main.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT SUM(quantity) FROM order_lines").fetchone()[0], 0)

    def test_unknown_payment_blocks_correction_without_writes(self):
        self.book(3)
        with self.main.get_conn() as conn:
            conn.execute(
                "INSERT INTO self_payment_sessions(person_id,client_payment_id,status,amount_eur,amount_cents,revision,created_at,updated_at) VALUES(?,'unknown-card','UNKNOWN',9,900,'synthetic','then','then')",
                (self.person,),
            )
            conn.commit()
        before = self.state()
        self.assertEqual(self.adjust(1).status_code, 409)
        self.assertEqual(self.state(), before)

    def test_archived_item_person_and_original_cost_sources(self):
        self.fixture.update(1.25)
        self.book(3)
        with self.main.get_conn() as conn:
            conn.execute(
                "UPDATE items SET archived_at='synthetic',active=0,purchase_price_eur=9 WHERE id=?", (self.item,)
            )
            conn.execute("UPDATE people SET archived_at='synthetic',active=0 WHERE id=?", (self.person,))
            conn.commit()
        self.assertEqual(self.adjust(2).status_code, 200)
        with self.main.get_conn() as conn:
            self.assertEqual(
                tuple(
                    conn.execute(
                        "SELECT SUM(quantity),SUM(purchase_total_eur),SUM(profit_eur) FROM transaction_items WHERE kind='CONSUMPTION_CORRECTION'"
                    ).fetchone()
                ),
                (-2, -2.5, -3.5),
            )

    def test_untracked_legacy_booking_blocks_automatic_correction(self):
        with self.main.get_conn() as conn:
            item = conn.execute("SELECT * FROM items WHERE id=?", (self.item,)).fetchone()
            self.main.add_order_line(conn, self.person, item, 3)
            conn.commit()
        before = self.state()
        result = self.adjust(1)
        self.assertEqual(result.status_code, 409)
        self.assertEqual(result.json()["detail"]["status"], "intervention_required")
        self.assertEqual(self.state(), before)

    def test_originals_and_provenance_are_immutable_by_database_guards(self):
        self.book(3)
        self.adjust(1)
        before = self.state()
        with self.main.get_conn() as conn:
            for table in ("booking_sources", "correction_details", "operation_receipts"):
                with self.assertRaises(sqlite3.IntegrityError):
                    conn.execute(f'DELETE FROM "{table}"')
        self.assertEqual(self.state(), before)

    def test_busy_write_fails_without_partial_receipt(self):
        self.book(3)
        before = self.state()
        original = self.main.get_conn
        from contextlib import contextmanager

        @contextmanager
        def immediate_timeout():
            with original() as conn:
                conn.execute("PRAGMA busy_timeout=0")
                yield conn

        from unittest.mock import patch

        with original() as writer:
            writer.execute("BEGIN IMMEDIATE")
            with patch.object(self.main, "get_conn", immediate_timeout):
                with self.assertRaises(sqlite3.OperationalError):
                    self.adjust(1)
            writer.rollback()
        self.assertEqual(self.state(), before)

    def test_original_period_cost_and_report_csv_reconcile(self):
        self.post(
            "/api/add-drink",
            {
                "person_id": self.person,
                "item_id": self.item,
                "offline_queued": True,
                "client_time": "2026-01-10T12:00:00",
                "client_operation_id": "historical-synthetic",
            },
        )
        self.fixture.update(2)
        result = self.adjust(1)
        self.assertEqual(result.status_code, 200, result.text)
        payload = {
            "pin": "1234",
            "report_type": "consumption",
            "group_by": "none",
            "date_from": "2026-01-10",
            "date_to": "2026-01-10",
        }
        report = self.post("/api/admin/report/preview", payload)
        self.assertEqual(report["rows"][0], [0, "0,00", "0,00", "0,00", "0,00"])


class RoundCancellationTests(unittest.TestCase):
    setUp = TransactionIntegrityTests.setUp
    book = TransactionIntegrityTests.book
    state = TransactionIntegrityTests.state
    statistics = TransactionIntegrityTests.statistics

    def round(self, quantity=1):
        self.post("/api/round-request", {"person_id": self.person, "quantity": quantity})
        with self.main.get_conn() as conn:
            return [r[0] for r in conn.execute("SELECT id FROM round_units ORDER BY id")]

    def cancel(self, units, operation="cancel-round"):
        return self.client.post(
            "/api/admin/rounds/cancel",
            json={
                "pin": "1234",
                "round_unit_ids": units,
                "correction_operation_id": operation,
                "correction_reason": "synthetic wrong round",
            },
        )

    def test_book_deduct_cancel_replay_and_no_additional_free_drinks(self):
        self.book(3)
        units = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": units[0]})
        with self.main.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT quantity FROM order_lines WHERE item_id=?", (self.item,)).fetchone()[0], 2
            )
        self.assertEqual(self.cancel(units).status_code, 200)
        before = self.state()
        self.assertEqual(self.cancel(units).status_code, 200)
        self.assertEqual(self.state(), before)
        self.assertEqual(self.statistics()["kpis"]["quantity"], 3)
        self.assertEqual(
            self.client.post("/api/deduct-round", json={"pin": "1234", "round_unit_id": units[0]}).status_code, 409
        )
        with self.main.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT quantity FROM order_lines WHERE item_id=?", (self.item,)).fetchone()[0], 3
            )
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM round_reversals").fetchone()[0], 1)

    def test_two_rounds_cancel_one_keeps_exact_other_allocation(self):
        self.book(5)
        units = self.round(2)
        for unit in units:
            self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": unit})
        self.assertEqual(self.cancel([units[0]]).status_code, 200)
        with self.main.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT quantity FROM order_lines WHERE item_id=?", (self.item,)).fetchone()[0], 4
            )
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM round_reversals").fetchone()[0], 1)
        self.assertEqual(
            self.client.post("/api/deduct-round", json={"pin": "1234", "round_unit_id": units[1]}).status_code, 200
        )  # Committed manual operation replays; it does not re-deduct.

    def test_paid_and_closed_rounds_block_without_state_change(self):
        units = self.round()
        self.post("/api/pay", {"pin": "1234", "person_id": self.person})
        before = self.state()
        result = self.cancel(units)
        self.assertEqual(result.status_code, 409)
        self.assertEqual(result.json()["detail"]["status"], "intervention_required")
        self.assertEqual(self.state(), before)

    def test_cashup_blocks_reversal_without_changing_originals(self):
        self.book(3)
        units = self.round()
        self.post("/api/admin/cashup", {"pin": "1234"})
        before = self.state()
        self.assertEqual(self.cancel(units).status_code, 409)
        self.assertEqual(self.state(), before)

    def test_multiple_people_restored_and_no_new_physical_consumption(self):
        self.book(3)
        other = self.post("/api/admin/people/create", {"pin": "1234", "first_name": "Synthetic", "last_name": "Other"})[
            "id"
        ]
        self.post("/api/add-drink", {"person_id": other, "item_id": self.item})
        units = self.round()
        before = self.state()["transaction_items"]
        result = self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": units[0]})
        self.assertEqual(result["removed_count"], 2)
        self.assertEqual(self.cancel(units).status_code, 200)
        with self.main.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT SUM(quantity) FROM transaction_items WHERE kind='CONSUME'").fetchone()[0], 4
            )
            self.assertEqual(
                conn.execute("SELECT SUM(quantity) FROM order_lines WHERE item_id=?", (self.item,)).fetchone()[0], 4
            )
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM round_reversals").fetchone()[0], 2)
        current = {row[0]: row for row in self.state()["transaction_items"]}
        self.assertTrue(all(current[row[0]] == row for row in before))

    def test_unattributed_current_history_blocks_new_round_and_cancel(self):
        self.book(3)
        units = self.round()
        with self.main.get_conn() as conn:
            tx = self.main.log_transaction(conn, self.person, "ROUND_DEDUCTED", 3, "unattributed historical")
            line = conn.execute("SELECT * FROM order_lines WHERE item_id=?", (self.item,)).fetchone()
            self.main.log_transaction_item(conn, tx, self.person, line, -1, "ROUND_DEDUCTED")
            conn.commit()
        before = self.state()
        self.assertEqual(self.cancel(units).status_code, 409)
        self.assertEqual(
            self.client.post("/api/deduct-round", json={"pin": "1234", "round_unit_id": units[0]}).status_code, 409
        )
        self.assertEqual(self.state(), before)

    def test_concurrent_cancel_same_unit_restores_once(self):
        self.book(3)
        units = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": units[0]})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.cancel(units), range(2)))
        self.assertTrue(all(r.status_code == 200 for r in results))
        self.assertEqual(results[0].json(), results[1].json())
        with self.main.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM round_reversals").fetchone()[0], 1)

    def test_concurrent_cancel_vs_cashup_is_all_reversed_or_closed_never_partial(self):
        self.book(3)
        units = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": units[0]})
        with ThreadPoolExecutor(max_workers=2) as pool:
            cancel = pool.submit(self.cancel, units)
            cashup = pool.submit(self.client.post, "/api/admin/cashup", json={"pin": "1234"})
            cancelled = cancel.result()
            self.assertEqual(cashup.result().status_code, 200)
        self.assertIn(cancelled.status_code, (200, 409))
        with self.main.get_conn() as conn:
            reversal_count = conn.execute("SELECT COUNT(*) FROM round_reversals").fetchone()[0]
            self.assertEqual(reversal_count, 1 if cancelled.status_code == 200 else 0)
            self.assertEqual(
                conn.execute("SELECT quantity FROM order_lines WHERE item_id=?", (self.item,)).fetchone()[0],
                3 if reversal_count else 2,
            )

    def test_concurrent_cancel_vs_payment_is_compensated_or_paid_not_both(self):
        self.book(3)
        units = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": units[0]})
        with ThreadPoolExecutor(max_workers=2) as pool:
            cancel = pool.submit(self.cancel, units)
            pay = pool.submit(
                self.client.post,
                "/api/pay",
                json={"pin": "1234", "person_id": self.person, "payment_operation_id": "concurrent-cash"},
            )
            cancelled, paid = cancel.result(), pay.result()
        self.assertEqual(paid.status_code, 200)
        self.assertIn(cancelled.status_code, (200, 409))
        with self.main.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM round_reversals").fetchone()[0],
                1 if cancelled.status_code == 200 else 0,
            )
            self.assertEqual(conn.execute("SELECT SUM(quantity) FROM order_lines").fetchone()[0], 0)

    def test_pending_round_request_holds_eligibility_then_reject_restores_once(self):
        self.book(3)
        units = self.round(2)
        with self.main.get_conn() as conn:
            line = conn.execute("SELECT original_order_line_id FROM round_units LIMIT 1").fetchone()[0]
        self.post("/api/edit-request", {"person_id": self.person, "line_quantities": {str(line): 1}})
        self.assertEqual(
            self.client.post("/api/deduct-round", json={"pin": "1234", "round_unit_id": units[0]}).status_code, 409
        )
        with self.main.get_conn() as conn:
            request = conn.execute("SELECT id FROM change_requests").fetchone()[0]
        self.post("/api/admin/change-request/decide", {"pin": "1234", "request_id": request, "decision": "reject"})
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": units[0]})
        self.assertEqual(self.cancel([units[0]]).status_code, 200)

    def test_every_round_reversal_write_fault_rolls_back_full_operation(self):
        self.book(3)
        units = self.round()
        self.post("/api/deduct-round", {"pin": "1234", "round_unit_id": units[0]})
        for table, action in (
            ("round_units", "UPDATE"),
            ("order_lines", "UPDATE"),
            ("transactions", "INSERT"),
            ("transaction_items", "INSERT"),
            ("round_events", "INSERT"),
            ("round_reversals", "INSERT"),
            ("operation_receipts", "INSERT"),
        ):
            with self.subTest(table=table):
                with self.main.get_conn() as conn:
                    conn.execute(
                        f"CREATE TRIGGER synthetic_reversal_fault BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'synthetic reversal fault'); END"
                    )
                    conn.commit()
                before = self.state()
                with self.assertRaisesRegex(sqlite3.IntegrityError, "synthetic reversal fault"):
                    self.cancel(units)
                self.assertEqual(self.state(), before)
                with self.main.get_conn() as conn:
                    conn.execute("DROP TRIGGER synthetic_reversal_fault")
                    conn.commit()


class TransactionMigrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.FinancialHistoryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def v1(self):
        from app.db import migrations as migration, schema

        database = self.root / "independent-v1.db"
        with closing(sqlite3.connect(database)) as conn:
            conn.row_factory = sqlite3.Row
            schema._init_legacy(connection=conn)
            conn.execute(migration.LEDGER_SQL)
            conn.execute(
                "INSERT INTO schema_migrations VALUES(?,?,?,?,?,?,?,?)",
                (
                    1,
                    migration.MIGRATION_ID,
                    0,
                    migration.CHECKSUM,
                    "",
                    migration.BASELINE_SCHEMA,
                    "initialize",
                    "2026-01-01T00:00:00+00:00",
                ),
            )
            conn.execute("PRAGMA user_version=1")
            conn.execute(f"PRAGMA application_id={migration.APPLICATION_ID}")
            conn.commit()
        return database

    def test_actual_v1_to_v2_preserves_original_tables_and_sequence(self):
        from app.db import migrations as migration
        from app.application_recovery import database_metadata

        database = self.v1()
        self.assertEqual(migration.inspect(database)["state"], "versioned-upgrade-required")
        with closing(sqlite3.connect(database)) as conn:
            original = {
                r[0]: conn.execute(f'SELECT * FROM "{r[0]}"').fetchall()
                for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
        migration.migrate(database)
        self.assertEqual(migration.inspect(database)["version"], 2)
        with closing(sqlite3.connect(database)) as conn:
            for table, rows in original.items():
                if table != "schema_migrations":
                    self.assertEqual(conn.execute(f'SELECT * FROM "{table}"').fetchall(), rows)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM round_units").fetchone()[0], 0)
        before = database_metadata(database)
        migration.migrate(database)
        self.assertEqual(database_metadata(database), before)

    def test_v1_transition_faults_and_interruption_preserve_history(self):
        from app.db import migrations as migration
        from app.application_recovery import database_metadata

        database = self.v1()
        before = database_metadata(database)
        for stage in ("after-schema", "after-transaction-schema", "after-ledger", "before-commit"):

            def fault(point, conn):
                if point == stage:
                    raise sqlite3.OperationalError("synthetic v2 fault")

            with self.assertRaises(sqlite3.OperationalError):
                migration.migrate(database, fault=fault)
            self.assertEqual(database_metadata(database), before)
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                "import os,sys; from app.db import migrations; migrations.migrate(sys.argv[1],fault=lambda p,c: os._exit(37) if p=='before-commit' else None)",
                str(database),
            ],
            capture_output=True,
        )
        self.assertEqual(result.returncode, 37)
        self.assertEqual(migration.inspect(database)["state"], "recovery-required")
        with closing(sqlite3.connect(database)) as conn:
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(database_metadata(database), before)
