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
AGENT_TOKEN = "test-agent-token"


class FakeRequest:
    def __init__(self, token: str | None = None):
        self.headers = {}
        if token:
            self.headers["authorization"] = f"Bearer {token}"


class BackendFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_agent_token = os.environ.pop("DRINK_POS_AGENT_TOKEN", None)
        os.environ["DRINK_POS_ENV"] = "development"
        os.environ["DRINK_POS_DB"] = str(Path(self.temp_dir.name) / "drink_pos_test.db")
        os.environ["DRINK_POS_PIN"] = PIN
        os.environ.pop("DRINK_POS_AGENT_TOKEN", None)

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
        if self.original_agent_token is None:
            os.environ.pop("DRINK_POS_AGENT_TOKEN", None)
        else:
            os.environ["DRINK_POS_AGENT_TOKEN"] = self.original_agent_token
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

    def test_kassa_payment_rejects_stale_revision(self):
        person, item = self.first_person_and_item()

        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.kassa_person(person["id"])
        self.assertTrue(preview["can_pay"])

        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        with self.assertRaises(HTTPException) as ctx:
            self.main.kassa_pay(
                self.main.KassaPayRequest(
                    pin=PIN,
                    person_id=person["id"],
                    expected_revision=preview["revision"],
                )
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("current", ctx.exception.detail)

        fresh = self.main.kassa_person(person["id"])
        pay_res = self.main.kassa_pay(
            self.main.KassaPayRequest(
                pin=PIN,
                person_id=person["id"],
                expected_revision=fresh["revision"],
            )
        )
        self.assertEqual(pay_res["status"], "paid")
        self.assertEqual(pay_res["paid_items"], 2)

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

    def test_kassa_person_history_shows_consumption_and_round_deductions_without_prices(self):
        people = self.main.list_people()
        config = self.main.config()
        item = next(item for item in config["user_items"] if item["name"] != "1 Runde")

        self.main.add_drink(self.main.AddDrinkRequest(person_id=people[0]["id"], item_id=item["id"]))
        self.main.create_round_request(self.main.RoundRequestIn(person_id=people[1]["id"], quantity=1))
        self.main.admin_cashup(self.main.CashupRequest(pin=PIN))

        history = self.main.kassa_person_history(people[0]["id"])
        entries = history["history"]
        consume = next(entry for entry in entries if entry["type"] == "CONSUME")
        deduction = next(entry for entry in entries if entry["type"] == "ROUND_DEDUCTED")

        self.assertEqual(consume["type_label"], "Konsum")
        self.assertEqual(consume["quantity"], 1)
        self.assertEqual(consume["quantity_label"], "+1x")
        self.assertEqual(deduction["type_label"], "Abzug Runde")
        self.assertEqual(deduction["quantity"], -1)
        self.assertEqual(deduction["quantity_label"], "-1x")
        self.assertEqual(deduction["product"], item["name"])
        for entry in entries:
            self.assertRegex(entry["timestamp_label"], r"\d{2}\.\d{2}, \d{2}:\d{2}")
            self.assertNotIn("unit_price_eur", entry)
            self.assertNotIn("total_eur", entry)

    def test_kassa_person_history_ends_with_last_payment_and_hides_older_activity(self):
        person, item = self.first_person_and_item()

        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.main.pay(self.main.PayRequest(pin=PIN, person_id=person["id"]))
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))

        history = self.main.kassa_person_history(person["id"])
        entries = history["history"]
        consume_entries = [entry for entry in entries if entry["type"] == "CONSUME"]

        self.assertEqual(entries[-1]["type"], "PAID_CASH")
        self.assertEqual(entries[-1]["type_label"], "Zahlung")
        self.assertEqual(entries[-1]["direction"], "payment")
        self.assertEqual(entries[-1]["product"], "Rechnung bezahlt")
        self.assertEqual(entries[-1]["quantity_label"], "OK")
        self.assertEqual(len(consume_entries), 1)
        self.assertEqual(consume_entries[0]["quantity"], 1)

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

    def test_cost_notice_config_separates_surfaces_and_placeholders(self):
        cfg = self.main.config()
        self.assertIn("{unteres_limit}", cfg["cost_warning_template"])
        self.assertIn("{oberes_limit}", cfg["payment_reminder_template"])
        self.assertTrue(cfg["cost_warning_show_on_overview"])
        self.assertTrue(cfg["cost_warning_show_in_popup"])
        self.assertTrue(cfg["payment_reminder_show_on_overview"])
        self.assertTrue(cfg["payment_reminder_show_in_popup"])

        self.main.admin_update_settings(
            self.main.SettingsUpdateRequest(
                pin=PIN,
                cost_warning_template="Warnung {betrag} {unteres_limit}",
                cost_warning_show_on_overview=False,
                cost_warning_show_in_popup=True,
                payment_reminder_template="Reminder {betrag} {oberes_limit}",
                payment_reminder_show_on_overview=True,
                payment_reminder_show_in_popup=False,
            )
        )

        updated = self.main.config()
        self.assertEqual(updated["cost_warning_template"], "Warnung {betrag} {unteres_limit}")
        self.assertEqual(updated["payment_reminder_template"], "Reminder {betrag} {oberes_limit}")
        self.assertFalse(updated["cost_warning_show_on_overview"])
        self.assertTrue(updated["cost_warning_show_in_popup"])
        self.assertTrue(updated["payment_reminder_show_on_overview"])
        self.assertFalse(updated["payment_reminder_show_in_popup"])

    def test_agent_api_requires_configured_token(self):
        with self.assertRaises(HTTPException) as disabled_ctx:
            self.main.require_agent_request(FakeRequest(AGENT_TOKEN))
        self.assertEqual(disabled_ctx.exception.status_code, 404)

        os.environ["DRINK_POS_AGENT_TOKEN"] = AGENT_TOKEN
        with self.assertRaises(HTTPException) as forbidden_ctx:
            self.main.require_agent_request(FakeRequest("wrong-token"))
        self.assertEqual(forbidden_ctx.exception.status_code, 403)

        capabilities = self.main.agent_capabilities(FakeRequest(AGENT_TOKEN))
        self.assertEqual(capabilities["interface"], "REST")
        self.assertIn("/api/agent/book-drink", {action["path"] for action in capabilities["actions"]})

    def test_agent_api_can_read_state_and_book_idempotently(self):
        os.environ["DRINK_POS_AGENT_TOKEN"] = AGENT_TOKEN
        person, item = self.first_person_and_item()
        request = FakeRequest(AGENT_TOKEN)
        payload = self.main.AgentBookDrinkRequest(
            person_id=person["id"],
            item_id=item["id"],
            quantity=2,
            client_operation_id="agent-test-1",
            device_info="unittest-agent",
        )

        booked = self.main.agent_book_drink(payload, request)
        duplicate = self.main.agent_book_drink(payload, request)
        state = self.main.agent_state(request)
        preview = self.main.agent_person(self.main.AgentPersonRequest(person_id=person["id"]), request)

        self.assertEqual(booked["status"], "ok")
        self.assertEqual(booked["quantity"], 2)
        self.assertTrue(duplicate["duplicate"])
        self.assertGreaterEqual(state["totals"]["open_items"], 2)
        self.assertEqual(preview["open_items"], 2)

        with self.main.get_conn() as conn:
            quantity = conn.execute(
                "SELECT SUM(quantity) AS quantity FROM order_lines WHERE person_id = ? AND item_id = ?",
                (person["id"], item["id"]),
            ).fetchone()["quantity"]
        self.assertEqual(quantity, 2)

    def test_member_message_acknowledgement_is_per_person(self):
        people = self.main.list_people()
        res = self.main.admin_create_member_message(
            self.main.AdminMemberMessageCreate(
                pin=PIN,
                title="Bitte bezahlen",
                message="Bitte beim naechsten Mal ausgleichen.",
                person_ids=[people[0]["id"], people[1]["id"]],
            )
        )
        message_id = res["id"]

        first = next(person for person in self.main.list_people() if person["id"] == people[0]["id"])
        second = next(person for person in self.main.list_people() if person["id"] == people[1]["id"])
        self.assertEqual(first["member_message_count"], 1)
        self.assertEqual(second["member_message_count"], 1)

        ack = self.main.acknowledge_member_message(
            self.main.MemberMessageAckRequest(person_id=people[0]["id"], message_id=message_id)
        )
        self.assertEqual(ack["status"], "ok")
        self.assertFalse(ack["archived"])

        first_after = next(person for person in self.main.list_people() if person["id"] == people[0]["id"])
        second_after = next(person for person in self.main.list_people() if person["id"] == people[1]["id"])
        self.assertEqual(first_after["member_message_count"], 0)
        self.assertEqual(second_after["member_message_count"], 1)

        final_ack = self.main.acknowledge_member_message(
            self.main.MemberMessageAckRequest(person_id=people[1]["id"], message_id=message_id)
        )
        self.assertEqual(final_ack["status"], "ok")
        self.assertTrue(final_ack["archived"])

        final_second = next(person for person in self.main.list_people() if person["id"] == people[1]["id"])
        overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
        self.assertEqual(final_second["member_message_count"], 0)
        self.assertNotIn(message_id, {message["id"] for message in overview["member_messages"]})

    def test_production_blocks_default_pin_login(self):
        original_env = self.main.APP_ENV
        self.main.APP_ENV = "production"
        try:
            with self.main.get_conn() as conn:
                with self.assertRaises(HTTPException) as ctx:
                    self.main.ensure_admin_login_allowed(conn)
            self.assertEqual(ctx.exception.status_code, 403)
            with self.assertRaises(HTTPException) as direct_ctx:
                self.main.transactions(pin=PIN)
            self.assertEqual(direct_ctx.exception.status_code, 403)
        finally:
            self.main.APP_ENV = original_env

    def test_env_pin_replaces_existing_default_pin(self):
        original_env = self.main.APP_ENV
        original_pin = self.main.ENV_PIN_CODE
        original_from_env = self.main.ENV_PIN_FROM_ENV
        self.main.APP_ENV = "production"
        self.main.ENV_PIN_CODE = "9876"
        self.main.ENV_PIN_FROM_ENV = True
        try:
            with self.main.get_conn() as conn:
                self.main.set_setting(conn, "admin_pin", "1234")
                self.main.ensure_settings(conn)
                self.assertEqual(self.main.configured_admin_pin(conn), "9876")
                self.main.require_pin(conn, "9876")
                with self.assertRaises(HTTPException):
                    self.main.require_pin(conn, "1234")
        finally:
            self.main.APP_ENV = original_env
            self.main.ENV_PIN_CODE = original_pin
            self.main.ENV_PIN_FROM_ENV = original_from_env


if __name__ == "__main__":
    unittest.main()
