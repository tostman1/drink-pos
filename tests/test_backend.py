import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException


ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
PIN = "1234"


class BackendFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DRINK_POS_ENV"] = "development"
        os.environ["DRINK_POS_DB"] = str(Path(self.temp_dir.name) / "drink_pos_test.db")
        os.environ["DRINK_POS_PIN"] = PIN

        sys.modules.pop("main", None)
        sys.path.insert(0, str(APP_DIR))
        self.main = importlib.import_module("main")
        self.main.init_db()

    def tearDown(self):
        sys.modules.pop("main", None)
        try:
            sys.path.remove(str(APP_DIR))
        except ValueError:
            pass
        self.temp_dir.cleanup()

    def first_person_and_item(self):
        people = self.main.list_people()
        config = self.main.config()
        item = next(item for item in config["user_items"] if item["name"] != "1 Runde")
        return people[0], item

    def test_sqlite_connection_enforces_foreign_keys_and_busy_timeout(self):
        with self.main.get_conn() as conn:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 15000)

    def test_booking_and_payment_flow(self):
        person, item = self.first_person_and_item()

        add_res = self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.assertEqual(add_res["status"], "ok")

        pay_res = self.main.pay(self.main.PayRequest(pin=PIN, person_id=person["id"]))
        self.assertEqual(pay_res["status"], "paid")
        self.assertGreater(pay_res["total"], 0)

    def test_round_and_cashup_flow(self):
        people = self.main.list_people()
        config = self.main.config()
        item = next(item for item in config["user_items"] if item["name"] != "1 Runde")

        self.main.add_drink(self.main.AddDrinkRequest(person_id=people[0]["id"], item_id=item["id"]))
        round_res = self.main.create_round_request(self.main.RoundRequestIn(person_id=people[1]["id"], quantity=1))
        self.assertEqual(round_res["status"], "approved")

        preview = self.main.admin_cashup_preview(self.main.CashupRequest(pin=PIN))
        self.assertEqual(preview["auto_rounds"]["rounds_count"], 1)
        self.assertGreaterEqual(preview["auto_rounds"]["deducted_items"], 1)

        cashup = self.main.admin_cashup(self.main.CashupRequest(pin=PIN))
        self.assertEqual(cashup["status"], "ok")

    def test_offline_client_operation_is_idempotent(self):
        person, item = self.first_person_and_item()
        operation_id = "offline-test-1"
        payload = {
            "person_id": person["id"],
            "item_id": item["id"],
            "client_operation_id": operation_id,
            "client_time": "2026-05-18T10:00:00.000Z",
            "device_info": "unittest",
            "offline_queued": True,
        }

        first = self.main.add_drink(self.main.AddDrinkRequest(**payload))
        second = self.main.add_drink(self.main.AddDrinkRequest(**payload))

        self.assertEqual(first["status"], "ok")
        self.assertTrue(second["duplicate"])

        with self.main.get_conn() as conn:
            quantity = conn.execute(
                "SELECT SUM(quantity) AS quantity FROM order_lines WHERE person_id = ? AND item_id = ?",
                (person["id"], item["id"]),
            ).fetchone()["quantity"]
            operation = conn.execute(
                "SELECT transaction_id FROM client_operations WHERE client_operation_id = ?",
                (operation_id,),
            ).fetchone()

        self.assertEqual(quantity, 1)
        self.assertIsNotNone(operation["transaction_id"])

    def test_public_transactions_require_pin(self):
        with self.assertRaises(HTTPException) as ctx:
            self.main.transactions()
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIsInstance(self.main.transactions(pin=PIN), list)


if __name__ == "__main__":
    unittest.main()
