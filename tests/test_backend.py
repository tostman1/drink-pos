import asyncio
import codecs
import importlib
import os
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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


async def streaming_response_body(response) -> bytes:
    chunks = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.encode("utf-8") if isinstance(chunk, str) else chunk)
    return b"".join(chunks)


class BackendFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_agent_token = os.environ.pop("DRINK_POS_AGENT_TOKEN", None)
        self.original_build_commit = os.environ.pop("APP_BUILD_COMMIT", None)
        self.original_payment_env = {
            key: os.environ.pop(key, None)
            for key in [
                "PAYMENT_PROVIDER",
                "SUMUP_API_BASE",
                "SUMUP_API_KEY",
                "SUMUP_MERCHANT_CODE",
                "SUMUP_READER_ID",
                "SUMUP_AFFILIATE_KEY",
                "SUMUP_AFFILIATE_APP_ID",
                "SUMUP_CURRENCY",
                "SUMUP_TIMEOUT_SECONDS",
                "DRINK_POS_ALLOW_TEST_CARD_PAYMENTS",
            ]
        }
        os.environ["DRINK_POS_ENV"] = "development"
        os.environ["DRINK_POS_DB"] = str(Path(self.temp_dir.name) / "drink_pos_test.db")
        os.environ["DRINK_POS_PIN"] = PIN
        os.environ["APP_BUILD_COMMIT"] = "test-build-abc"
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
        if self.original_build_commit is None:
            os.environ.pop("APP_BUILD_COMMIT", None)
        else:
            os.environ["APP_BUILD_COMMIT"] = self.original_build_commit
        for key, value in self.original_payment_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
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

    def test_config_and_admin_overview_include_build_commit(self):
        config = self.main.config()
        overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))

        self.assertEqual(config["build"]["commit"], "test-build-abc")
        self.assertEqual(overview["settings"]["build"]["commit"], "test-build-abc")
        self.assertEqual(overview["settings"]["database"]["source"], "DRINK_POS_DB")

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

    def configure_sumup(self):
        os.environ["PAYMENT_PROVIDER"] = "sumup"
        os.environ["SUMUP_API_BASE"] = "https://api.sumup.test"
        os.environ["SUMUP_API_KEY"] = "test-api-key"
        os.environ["SUMUP_MERCHANT_CODE"] = "test-merchant"
        os.environ["SUMUP_READER_ID"] = "test-reader"
        os.environ["SUMUP_AFFILIATE_KEY"] = "test-affiliate-key"
        os.environ["SUMUP_AFFILIATE_APP_ID"] = "drink-pos-test"
        os.environ["SUMUP_CURRENCY"] = "EUR"
        os.environ["SUMUP_TIMEOUT_SECONDS"] = "30"

    def configure_test_card_payments(self):
        self.main.APP_ENV = "test"
        os.environ.pop("PAYMENT_PROVIDER", None)
        for key in [
            "SUMUP_API_KEY",
            "SUMUP_MERCHANT_CODE",
            "SUMUP_READER_ID",
        ]:
            os.environ.pop(key, None)

    def paid_sumup_result(self, amount_cents, provider_checkout_id="sumup-checkout-1"):
        return {
            "status": "paid",
            "provider_checkout_id": provider_checkout_id,
            "transaction_id": "sumup-tx-1",
            "transaction_code": "SUMUPCODE1",
            "auth_code": "AUTH01",
            "amount_cents": amount_cents,
            "currency": "EUR",
            "raw_response": {"status": "SUCCESSFUL"},
        }

    def test_sumup_service_handles_wrapped_reader_status_and_checkout_response(self):
        sumup = importlib.import_module("services.sumup")
        original_request = sumup._request
        calls = []

        def fake_request(cfg, method, path, body=None, timeout=15):
            calls.append((method, path, body))
            if path.endswith("/status"):
                return {"data": {"status": "ONLINE", "state": "IDLE"}}
            if path.endswith("/checkout"):
                return {"data": {"client_transaction_id": "client-tx-123"}}
            self.fail(f"Unexpected SumUp path: {path}")

        sumup._request = fake_request
        try:
            cfg = sumup.SumUpConfig(
                api_base="https://api.sumup.test",
                api_key="test-api-key",
                merchant_code="merchant",
                reader_id="reader",
                affiliate_key="affiliate-key",
                affiliate_app_id="drink-pos-test",
            )
            checkout = sumup.create_reader_checkout(cfg, 250, "Drink POS Test", "selfpay-test")
        finally:
            sumup._request = original_request

        self.assertEqual(checkout["provider_checkout_id"], "client-tx-123")
        checkout_body = calls[-1][2]
        self.assertEqual(checkout_body["total_amount"]["value"], 250)
        self.assertEqual(checkout_body["affiliate"]["foreign_transaction_id"], "selfpay-test")

    def test_sumup_service_terminates_reader_checkout(self):
        sumup = importlib.import_module("services.sumup")
        original_request = sumup._request
        calls = []

        def fake_request(cfg, method, path, body=None, timeout=15):
            calls.append((method, path, body, timeout))
            return {"ok": True}

        sumup._request = fake_request
        try:
            cfg = sumup.SumUpConfig(
                api_base="https://api.sumup.test",
                api_key="test-api-key",
                merchant_code="merchant",
                reader_id="reader",
                timeout_seconds=30,
            )
            result = sumup.terminate_reader_checkout(cfg)
        finally:
            sumup._request = original_request

        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls, [("POST", "/v0.1/merchants/merchant/readers/reader/terminate", None, 20)])

    def test_self_payment_with_sumup_closes_open_lines(self):
        self.configure_sumup()
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.self_pay_person(person["id"])
        calls = []
        original_create = self.main.create_sumup_checkout
        original_poll = self.main.poll_sumup_payment

        def fake_create(cfg, amount_cents, receipt_text="", foreign_transaction_id=None):
            calls.append((cfg, amount_cents, receipt_text, foreign_transaction_id))
            return {"provider_checkout_id": "sumup-checkout-paid-1", "status": "sent_to_reader"}

        def fake_poll(cfg, provider_checkout_id):
            return self.paid_sumup_result(calls[0][1], provider_checkout_id)

        self.main.create_sumup_checkout = fake_create
        self.main.poll_sumup_payment = fake_poll
        payment_id = "selfpay-test-paid-1"
        try:
            paid = self.main.self_pay(
                self.main.SelfPayRequest(
                    person_id=person["id"],
                    expected_revision=preview["revision"],
                    client_payment_id=payment_id,
                )
            )
            duplicate = self.main.self_pay(
                self.main.SelfPayRequest(
                    person_id=person["id"],
                    expected_revision=preview["revision"],
                    client_payment_id=payment_id,
                )
            )
        finally:
            self.main.create_sumup_checkout = original_create
            self.main.poll_sumup_payment = original_poll

        self.assertEqual(paid["status"], "paid")
        self.assertEqual(paid["payment_method"], "SUMUP")
        self.assertEqual(duplicate["status"], "paid")
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(len(calls), 1)
        expected_breakdown = self.main.card_payment_breakdown(preview["total_eur"])
        self.assertEqual(calls[0][1], expected_breakdown["amount_cents"])
        self.assertEqual(paid["base_amount_cents"], expected_breakdown["base_amount_cents"])
        self.assertEqual(paid["card_fee_cents"], expected_breakdown["card_fee_cents"])
        self.assertEqual(paid["rounding_adjustment_cents"], 0)
        self.assertIn("Drink POS", calls[0][2])
        self.assertEqual(calls[0][3], payment_id)
        self.assertEqual(paid["provider_checkout_id"], "sumup-checkout-paid-1")
        self.assertFalse(self.main.kassa_person(person["id"])["lines"])

        payment_status = self.main.self_pay_payment_status(payment_id)
        self.assertEqual(payment_status["status"], "paid")
        self.assertEqual(payment_status["transaction_id"], paid["transaction_id"])

        history = self.main.kassa_person_history(person["id"])
        self.assertEqual(history["history"][-1]["type"], "PAID_SUMUP")
        self.assertEqual(history["history"][-1]["type_label"], "SumUp-Zahlung")

    def test_cancelled_sumup_session_can_still_book_confirmed_payment(self):
        self.configure_sumup()
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.self_pay_person(person["id"])
        create_calls = []
        terminate_calls = []
        cancel_payload = {}
        payment_id = "selfpay-cancel-paid-wins-1"
        original_create = self.main.create_sumup_checkout
        original_poll = self.main.poll_sumup_payment
        original_terminate = self.main.terminate_sumup_checkout

        def fake_create(cfg, amount_cents, receipt_text="", foreign_transaction_id=None):
            create_calls.append(amount_cents)
            return {"provider_checkout_id": "sumup-checkout-cancel-race-1", "status": "sent_to_reader"}

        def fake_poll(cfg, provider_checkout_id):
            cancel_payload.update(self.main.self_pay_cancel_payment(payment_id))
            return self.paid_sumup_result(create_calls[0], provider_checkout_id)

        def fake_terminate(cfg):
            terminate_calls.append(cfg.reader_id)
            return {"ok": True}

        self.main.create_sumup_checkout = fake_create
        self.main.poll_sumup_payment = fake_poll
        self.main.terminate_sumup_checkout = fake_terminate
        try:
            paid = self.main.self_pay(
                self.main.SelfPayRequest(
                    person_id=person["id"],
                    expected_revision=preview["revision"],
                    client_payment_id=payment_id,
                )
            )
        finally:
            self.main.create_sumup_checkout = original_create
            self.main.poll_sumup_payment = original_poll
            self.main.terminate_sumup_checkout = original_terminate

        self.assertEqual(cancel_payload["status"], "cancelled")
        self.assertEqual(terminate_calls, ["test-reader"])
        self.assertEqual(paid["status"], "paid")
        self.assertEqual(paid["payment_method"], "SUMUP")
        self.assertEqual(paid["provider_checkout_id"], "sumup-checkout-cancel-race-1")
        self.assertFalse(self.main.kassa_person(person["id"])["lines"])
        payment_status = self.main.self_pay_payment_status(payment_id)
        self.assertEqual(payment_status["status"], "paid")
        with self.main.get_conn() as conn:
            tx_types = [
                row["type"]
                for row in conn.execute(
                    "SELECT type FROM transactions WHERE person_id = ? ORDER BY id",
                    (person["id"],),
                ).fetchall()
            ]
        self.assertIn("SUMUP_PAYMENT_CANCELLED", tx_types)
        self.assertIn("PAID_SUMUP", tx_types)

    def test_test_environment_card_payment_uses_local_mock_without_sumup(self):
        self.configure_test_card_payments()
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))

        config = self.main.self_pay_config()
        self.assertTrue(config["self_payment_available"])
        self.assertTrue(config["test_payment_mode"])
        self.assertEqual(config["payment_provider"], "test")
        self.assertFalse(config["sumup_missing"])

        preview = self.main.self_pay_person(person["id"])
        paid = self.main.self_pay(
            self.main.SelfPayRequest(
                person_id=person["id"],
                expected_revision=preview["revision"],
                client_payment_id="selfpay-test-mode-1",
            )
        )

        self.assertEqual(paid["status"], "paid")
        self.assertEqual(paid["payment_method"], "TEST_CARD")
        self.assertTrue(paid["test_payment_mode"])
        self.assertTrue(str(paid["provider_checkout_id"]).startswith("test-card-checkout-"))
        self.assertEqual(paid["currency"], "EUR")
        self.assertFalse(self.main.kassa_person(person["id"])["lines"])
        with self.main.get_conn() as conn:
            session = conn.execute("SELECT provider FROM self_payment_sessions WHERE client_payment_id = ?", ("selfpay-test-mode-1",)).fetchone()
            self.assertEqual(session["provider"], "test")

    def test_production_does_not_enable_test_card_provider(self):
        self.main.APP_ENV = "production"
        os.environ["PAYMENT_PROVIDER"] = "test"

        config = self.main.self_pay_config()

        self.assertFalse(config["self_payment_available"])
        self.assertFalse(config["test_payment_mode"])
        self.assertIn("PAYMENT_PROVIDER=sumup", config["sumup_missing"])

    def test_production_can_explicitly_enable_test_card_provider(self):
        self.main.APP_ENV = "production"
        os.environ["PAYMENT_PROVIDER"] = "test"
        os.environ["DRINK_POS_ALLOW_TEST_CARD_PAYMENTS"] = "1"

        config = self.main.self_pay_config()

        self.assertTrue(config["self_payment_available"])
        self.assertTrue(config["test_payment_mode"])
        self.assertEqual(config["payment_provider"], "test")

    def test_self_payment_adds_card_fee_and_rounding_to_sumup_amount(self):
        self.configure_sumup()
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.self_pay_person(person["id"])
        expected = self.main.card_payment_breakdown(preview["total_eur"], "five")
        calls = []
        original_create = self.main.create_sumup_checkout
        original_poll = self.main.poll_sumup_payment

        def fake_create(cfg, amount_cents, receipt_text="", foreign_transaction_id=None):
            calls.append(amount_cents)
            return {"provider_checkout_id": "sumup-checkout-rounded-1", "status": "sent_to_reader"}

        def fake_poll(cfg, provider_checkout_id):
            return self.paid_sumup_result(calls[0], provider_checkout_id)

        self.main.create_sumup_checkout = fake_create
        self.main.poll_sumup_payment = fake_poll
        try:
            paid = self.main.self_pay(
                self.main.SelfPayRequest(
                    person_id=person["id"],
                    expected_revision=preview["revision"],
                    client_payment_id="selfpay-rounded-1",
                    rounding_mode="five",
                )
            )
        finally:
            self.main.create_sumup_checkout = original_create
            self.main.poll_sumup_payment = original_poll

        self.assertEqual(calls, [expected["amount_cents"]])
        self.assertEqual(paid["status"], "paid")
        self.assertEqual(paid["total"], expected["amount_eur"])
        self.assertEqual(paid["base_amount_cents"], expected["base_amount_cents"])
        self.assertEqual(paid["card_fee_cents"], expected["card_fee_cents"])
        self.assertEqual(paid["rounding_mode"], "five")
        self.assertEqual(paid["rounding_adjustment_cents"], expected["rounding_adjustment_cents"])
        self.assertGreaterEqual(paid["card_fee_cents"], 20)

    def test_self_payment_locks_person_while_sumup_is_running(self):
        self.configure_sumup()
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.self_pay_person(person["id"])
        original_create = self.main.create_sumup_checkout
        original_poll = self.main.poll_sumup_payment
        blocked_status = []
        pending_duplicates = []
        create_calls = []
        payment_id = "selfpay-test-pending-1"

        def fake_create(cfg, amount_cents, receipt_text="", foreign_transaction_id=None):
            create_calls.append((amount_cents, receipt_text))
            duplicate = self.main.self_pay(
                self.main.SelfPayRequest(
                    person_id=person["id"],
                    expected_revision=preview["revision"],
                    client_payment_id=payment_id,
                )
            )
            pending_duplicates.append((duplicate["status"], duplicate["duplicate"]))
            with self.assertRaises(HTTPException) as ctx:
                self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
            blocked_status.append(ctx.exception.status_code)
            return {"provider_checkout_id": "sumup-checkout-lock-1", "status": "sent_to_reader"}

        def fake_poll(cfg, provider_checkout_id):
            return self.paid_sumup_result(create_calls[0][0], provider_checkout_id)

        self.main.create_sumup_checkout = fake_create
        self.main.poll_sumup_payment = fake_poll
        try:
            paid = self.main.self_pay(
                self.main.SelfPayRequest(
                    person_id=person["id"],
                    expected_revision=preview["revision"],
                    client_payment_id=payment_id,
                )
            )
        finally:
            self.main.create_sumup_checkout = original_create
            self.main.poll_sumup_payment = original_poll

        self.assertEqual(paid["status"], "paid")
        self.assertEqual(blocked_status, [409])
        self.assertEqual(pending_duplicates, [("created", True)])
        self.assertEqual(len(create_calls), 1)

    def test_self_payment_routes_expose_page_and_open_balance(self):
        page = self.main.self_pay_page()
        page_path = Path(page.path)
        self.assertEqual(page_path.name, "self-pay.html")
        self.assertIn("Selbstzahlung", page_path.read_text(encoding="utf-8"))
        self.assertIn("/self-pay.webmanifest", page_path.read_text(encoding="utf-8"))
        list_page = self.main.home()
        list_html = Path(list_page.path).read_text(encoding="utf-8")
        self.assertIn("cardPayPanel", list_html)
        self.assertIn("adminCardPayButton", list_html)
        self.assertIn("Barzahlung", list_html)
        self.assertIn("Kartenzahlung", list_html)
        self.assertIn("cardRoundingOptions", list_html)
        self.assertIn("Kartenzahlungsgebühr +3 % (min. 0,20 €)", list_html)
        self.assertIn("Mit Karte zahlen", list_html)
        self.assertIn("/api/self-pay/pay", list_html)
        self.assertIn("client_payment_id", list_html)
        kassa_page = self.main.kassa_page()
        kassa_html = Path(kassa_page.path).read_text(encoding="utf-8")
        self.assertIn("confirmCardPayButton", kassa_html)
        self.assertIn("Kartenzahlung +3 % (min. 0,20 €)", kassa_html)
        self.assertIn("kassaCardRoundingOptions", kassa_html)
        self.assertIn("Mit Karte zahlen", kassa_html)
        self.assertIn("/api/self-pay/pay", kassa_html)
        manifest = self.main.self_pay_manifest()
        self.assertEqual(Path(manifest.path).name, "self-pay.webmanifest")
        disabled = self.main.self_pay_config()
        self.assertFalse(disabled["self_payment_available"])

        self.configure_sumup()
        person, item = self.first_person_and_item()
        add = self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.assertEqual(add["status"], "ok")

        config = self.main.self_pay_config()
        self.assertTrue(config["self_payment_available"])
        people = self.main.self_pay_people()
        self.assertGreaterEqual(len(people["people"]), 1)
        detail = self.main.self_pay_person(person["id"])
        self.assertTrue(detail["can_self_pay"])
        self.assertTrue(detail["lines"])

    def test_self_payment_reports_missing_sumup_configuration(self):
        os.environ["PAYMENT_PROVIDER"] = "sumup"
        config = self.main.self_pay_config()
        self.assertFalse(config["self_payment_available"])
        self.assertIn("SUMUP_API_KEY", config["sumup_missing"])
        with self.assertRaises(HTTPException) as ctx:
            self.main.self_pay_people()
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("SumUp", ctx.exception.detail)

    def test_sumup_api_error_keeps_open_lines(self):
        self.configure_sumup()
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.self_pay_person(person["id"])
        original_create = self.main.create_sumup_checkout
        original_poll = self.main.poll_sumup_payment

        def fake_create(cfg, amount_cents, receipt_text="", foreign_transaction_id=None):
            raise self.main.SumUpError("reader_busy", "SumUp Solo ist beschäftigt")

        self.main.create_sumup_checkout = fake_create
        self.main.poll_sumup_payment = lambda *args, **kwargs: self.fail("Polling must not start after API error")
        try:
            with self.assertRaises(HTTPException) as ctx:
                self.main.self_pay(
                    self.main.SelfPayRequest(
                        person_id=person["id"],
                        expected_revision=preview["revision"],
                        client_payment_id="selfpay-api-error-1",
                    )
                )
        finally:
            self.main.create_sumup_checkout = original_create
            self.main.poll_sumup_payment = original_poll

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(ctx.exception.detail["status"], "failed")
        self.assertTrue(self.main.kassa_person(person["id"])["lines"])

    def test_sumup_timeout_or_unknown_keeps_open_lines(self):
        self.configure_sumup()
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.self_pay_person(person["id"])
        original_create = self.main.create_sumup_checkout
        original_poll = self.main.poll_sumup_payment

        try:
            for status in ("timeout", "unknown"):
                with self.subTest(status=status):
                    self.main.create_sumup_checkout = lambda cfg, amount_cents, receipt_text="", foreign_transaction_id=None, status=status: {
                        "provider_checkout_id": f"sumup-checkout-{status}",
                        "status": "sent_to_reader",
                    }
                    self.main.poll_sumup_payment = lambda cfg, provider_checkout_id, status=status: {
                        "status": status,
                        "provider_checkout_id": provider_checkout_id,
                        "message": f"SumUp {status}",
                        "raw_response": {},
                    }
                    result = self.main.self_pay(
                        self.main.SelfPayRequest(
                            person_id=person["id"],
                            expected_revision=preview["revision"],
                            client_payment_id=f"selfpay-{status}-1",
                        )
                    )
                    self.assertEqual(result["status"], status)
                    self.assertTrue(self.main.kassa_person(person["id"])["lines"])
        finally:
            self.main.create_sumup_checkout = original_create
            self.main.poll_sumup_payment = original_poll

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

    def test_kassa_payment_before_cashup_applies_round_deduction_once(self):
        people = self.main.list_people()
        config = self.main.config()
        item = next(item for item in config["user_items"] if item["name"] != "1 Runde")
        other = people[0]
        payer = people[1]
        with self.main.get_conn() as conn:
            round_price = float(self.main.get_setting(conn, "round_item_price_eur", self.main.DEFAULT_ROUND_PRICE_EUR))

        self.main.add_drink(self.main.AddDrinkRequest(person_id=other["id"], item_id=item["id"]))
        self.main.add_drink(self.main.AddDrinkRequest(person_id=payer["id"], item_id=item["id"]))
        self.main.create_round_request(self.main.RoundRequestIn(person_id=payer["id"], quantity=1))

        payer_preview = self.main.kassa_person(payer["id"])
        self.assertEqual(payer_preview["round_deduction_items"], 1)
        self.assertEqual(payer_preview["total"], round_price)

        paid = self.main.kassa_pay(
            self.main.KassaPayRequest(
                pin=PIN,
                person_id=payer["id"],
                expected_revision=payer_preview["revision"],
            )
        )
        self.assertEqual(paid["status"], "paid")
        self.assertEqual(paid["round_deduction_items"], 1)
        self.assertEqual(paid["total"], round_price)

        cashup_preview = self.main.admin_cashup_preview(self.main.CashupRequest(pin=PIN))
        self.assertEqual(cashup_preview["auto_rounds"]["rounds_count"], 1)
        deducted_people = {item["person_id"] for item in cashup_preview["auto_rounds"]["deductions"]}
        self.assertIn(other["id"], deducted_people)
        self.assertNotIn(payer["id"], deducted_people)

        cashup = self.main.admin_cashup(self.main.CashupRequest(pin=PIN))
        self.assertEqual(cashup["status"], "ok")
        self.assertFalse(self.main.kassa_person(other["id"])["lines"])

    def test_paid_round_after_person_payment_does_not_deduct_that_person_again_at_cashup(self):
        self.configure_test_card_payments()
        people = self.main.list_people()
        config = self.main.config()
        item = next(item for item in config["user_items"] if item["name"] != "1 Runde")
        open_round_payer = people[0]
        card_round_payer = people[1]
        consumer = people[2]

        self.main.create_round_request(self.main.RoundRequestIn(person_id=open_round_payer["id"], quantity=1))
        self.main.create_round_request(self.main.RoundRequestIn(person_id=card_round_payer["id"], quantity=1))
        for _ in range(3):
            self.main.add_drink(self.main.AddDrinkRequest(person_id=consumer["id"], item_id=item["id"]))

        consumer_preview = self.main.kassa_person(consumer["id"])
        self.assertEqual(consumer_preview["round_deduction_items"], 2)
        self.assertEqual(consumer_preview["payable_items"], 1)

        paid_consumer = self.main.kassa_pay(
            self.main.KassaPayRequest(
                pin=PIN,
                person_id=consumer["id"],
                expected_revision=consumer_preview["revision"],
            )
        )
        self.assertEqual(paid_consumer["status"], "paid")
        self.assertEqual(paid_consumer["round_deduction_items"], 2)

        card_preview = self.main.self_pay_person(card_round_payer["id"])
        paid_round = self.main.self_pay(
            self.main.SelfPayRequest(
                person_id=card_round_payer["id"],
                expected_revision=card_preview["revision"],
                client_payment_id="round-payer-card-after-consumer-payment",
            )
        )
        self.assertEqual(paid_round["status"], "paid")

        self.main.add_drink(self.main.AddDrinkRequest(person_id=consumer["id"], item_id=item["id"]))

        cashup_preview = self.main.admin_cashup_preview(self.main.CashupRequest(pin=PIN))
        self.assertEqual(cashup_preview["auto_rounds"]["rounds_count"], 2)
        self.assertEqual(cashup_preview["auto_rounds"]["open_rounds_count"], 1)
        self.assertEqual(cashup_preview["auto_rounds"]["already_paid_rounds_count"], 1)
        self.assertEqual(cashup_preview["auto_rounds"]["deducted_items"], 0)
        self.assertEqual(
            [charge["person_id"] for charge in cashup_preview["auto_rounds"]["charges"]],
            [open_round_payer["id"]],
        )
        self.assertFalse(
            any(int(item["person_id"]) == int(consumer["id"]) for item in cashup_preview["auto_rounds"]["deductions"])
        )
        self.assertEqual(
            [round_item["payer_person_id"] for round_item in cashup_preview["auto_rounds"]["rounds"]],
            [open_round_payer["id"], card_round_payer["id"]],
        )
        self.assertEqual(
            [round_item["already_paid"] for round_item in cashup_preview["auto_rounds"]["rounds"]],
            [False, True],
        )

        cashup = self.main.admin_cashup(self.main.CashupRequest(pin=PIN))
        self.assertEqual(cashup["status"], "ok")
        with self.main.get_conn() as conn:
            deducted_count = conn.execute(
                """
                SELECT COALESCE(SUM(ABS(quantity)), 0) AS q
                FROM transaction_items
                WHERE person_id = ? AND kind = 'ROUND_DEDUCTED'
                """,
                (consumer["id"],),
            ).fetchone()["q"]
        self.assertEqual(int(deducted_count), 2)

    def test_cashup_with_only_already_paid_rounds_closes_round_units(self):
        self.configure_test_card_payments()
        people = self.main.list_people()
        config = self.main.config()
        item = next(item for item in config["user_items"] if item["name"] != "1 Runde")
        round_payer = people[0]
        consumer = people[1]

        self.main.create_round_request(self.main.RoundRequestIn(person_id=round_payer["id"], quantity=1))
        round_preview = self.main.self_pay_person(round_payer["id"])
        paid_round = self.main.self_pay(
            self.main.SelfPayRequest(
                person_id=round_payer["id"],
                expected_revision=round_preview["revision"],
                client_payment_id="paid-round-only-before-cashup",
            )
        )
        self.assertEqual(paid_round["status"], "paid")

        preview = self.main.admin_cashup_preview(self.main.CashupRequest(pin=PIN))
        self.assertEqual(preview["gross_items"], 0)
        self.assertEqual(preview["auto_rounds"]["rounds_count"], 1)
        self.assertEqual(preview["auto_rounds"]["open_rounds_count"], 0)
        self.assertEqual(preview["auto_rounds"]["already_paid_rounds_count"], 1)
        self.assertEqual(preview["auto_rounds"]["already_paid_total_eur"], preview["auto_rounds"]["charged_total_eur"])

        cashup = self.main.admin_cashup(self.main.CashupRequest(pin=PIN))
        self.assertEqual(cashup["status"], "ok")
        with self.main.get_conn() as conn:
            open_paid_units = conn.execute(
                "SELECT COUNT(*) AS c FROM paid_round_units WHERE event_open = 1"
            ).fetchone()["c"]
            cashup_count = conn.execute(
                "SELECT COUNT(*) AS c FROM transactions WHERE type = 'CASHUP'"
            ).fetchone()["c"]
        self.assertEqual(int(open_paid_units), 0)
        self.assertEqual(int(cashup_count), 1)

        self.main.add_drink(self.main.AddDrinkRequest(person_id=consumer["id"], item_id=item["id"]))
        next_preview = self.main.admin_cashup_preview(self.main.CashupRequest(pin=PIN))
        self.assertEqual(next_preview["auto_rounds"]["rounds_count"], 0)
        self.assertEqual(next_preview["auto_rounds"]["deducted_items"], 0)

    def test_payments_are_blocked_when_round_deductions_clear_balance(self):
        self.configure_test_card_payments()
        people = self.main.list_people()
        config = self.main.config()
        item = next(item for item in config["user_items"] if item["name"] != "1 Runde")
        round_payer = people[0]
        person = people[1]

        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.main.create_round_request(self.main.RoundRequestIn(person_id=round_payer["id"], quantity=2))

        preview = self.main.kassa_person(person["id"])
        self.assertEqual(preview["round_deduction_items"], 2)
        self.assertEqual(preview["total"], 0.0)
        self.assertFalse(preview["can_pay"])

        self_pay_preview = self.main.self_pay_person(person["id"])
        self.assertFalse(self_pay_preview["can_self_pay"])
        with self.assertRaises(HTTPException) as card_ctx:
            self.main.self_pay(
                self.main.SelfPayRequest(
                    person_id=person["id"],
                    expected_revision=self_pay_preview["revision"],
                    client_payment_id="round-cleared-card-payment",
                )
            )
        self.assertEqual(card_ctx.exception.status_code, 400)
        with self.main.get_conn() as conn:
            sessions = conn.execute(
                "SELECT COUNT(*) AS c FROM self_payment_sessions WHERE client_payment_id = ?",
                ("round-cleared-card-payment",),
            ).fetchone()["c"]
        self.assertEqual(sessions, 0)

        with self.assertRaises(HTTPException) as kassa_ctx:
            self.main.kassa_pay(
                self.main.KassaPayRequest(
                    pin=PIN,
                    person_id=person["id"],
                    expected_revision=preview["revision"],
                )
            )
        self.assertEqual(kassa_ctx.exception.status_code, 400)

        with self.assertRaises(HTTPException) as cash_ctx:
            self.main.pay(self.main.PayRequest(pin=PIN, person_id=person["id"]))
        self.assertEqual(cash_ctx.exception.status_code, 400)

    def test_round_deductions_are_visible_and_sorted_by_cheapest_item(self):
        person, _ = self.first_person_and_item()
        self.main.admin_create_drink(
            self.main.AdminItemCreate(pin=PIN, name="Test teuer", short_label="T", price="5.00", purchase_price="0.50")
        )
        self.main.admin_create_drink(
            self.main.AdminItemCreate(pin=PIN, name="Test billig", short_label="B", price="1.00", purchase_price="0.20")
        )
        config = self.main.config()
        cheap = next(item for item in config["items"] if item["name"] == "Test billig")
        expensive = next(item for item in config["items"] if item["name"] == "Test teuer")

        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=expensive["id"]))
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=cheap["id"]))
        self.main.create_round_request(self.main.RoundRequestIn(person_id=person["id"], quantity=2))

        preview = self.main.kassa_person(person["id"])
        deductions = [line for line in preview["lines"] if line.get("is_round_deduction")]

        self.assertEqual([line["unit_price_eur"] for line in deductions], [1.0, 5.0])
        self.assertEqual([line["quantity"] for line in deductions], [-1, -1])
        self.assertTrue(all(str(line["item"]).startswith("Rundenabzug:") for line in deductions))

    def test_stale_round_deduction_plan_cannot_remove_twice(self):
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.main.create_round_request(self.main.RoundRequestIn(person_id=person["id"], quantity=1))

        with self.main.get_conn() as conn:
            plan = self.main.build_person_round_deduction_plan(conn, person["id"])
            self.assertEqual(plan["deducted_items"], 1)
            self.main.apply_person_round_deductions(conn, person["id"], plan, "Test")
            with self.assertRaises(HTTPException) as ctx:
                self.main.apply_person_round_deductions(conn, person["id"], plan, "Test")
            self.assertEqual(ctx.exception.status_code, 409)

    def test_manual_sumup_cancel_unlocks_person(self):
        person, item = self.first_person_and_item()
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        payment_id = "manual-cancel-1"

        with self.main.get_conn() as conn:
            conn.execute(
                """
                INSERT INTO self_payment_sessions (
                    person_id, client_payment_id, status,
                    base_amount_cents, card_fee_cents, rounding_mode, rounding_adjustment_cents,
                    amount_eur, amount_cents, currency, provider, revision, created_at, updated_at
                ) VALUES (?, ?, 'SENT_TO_READER', 250, 20, 'none', 0, 2.70, 270, 'EUR', 'sumup', ?, ?, ?)
                """,
                (person["id"], payment_id, "test-revision", self.main.now_text(), self.main.now_text()),
            )
            conn.commit()

        cancelled = self.main.self_pay_cancel_payment(payment_id)
        self.assertEqual(cancelled["status"], "cancelled")

        added = self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.assertEqual(added["status"], "ok")

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

    def test_kassa_person_history_hides_approved_corrections(self):
        person, item = self.first_person_and_item()

        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.kassa_person(person["id"])
        line_id = preview["lines"][0]["line_ids"][0]

        self.main.create_edit_request(
            self.main.EditRequestIn(
                person_id=person["id"],
                line_quantities={str(line_id): 1},
                reason="Falsch geklickt",
            )
        )
        with self.main.get_conn() as conn:
            pending = self.main.get_pending_requests_for_person(conn, person["id"])
            request_id = pending[0]["id"]
        self.main.admin_decide_change_request(
            self.main.AdminChangeRequestDecision(pin=PIN, request_id=request_id, decision="APPROVED")
        )

        history = self.main.kassa_person_history(person["id"])
        consume_entries = [entry for entry in history["history"] if entry["type"] == "CONSUME"]
        self.assertEqual(sum(entry["quantity"] for entry in consume_entries), 1)

    def test_admin_person_history_shows_corrections_and_allows_archived_person(self):
        person, item = self.first_person_and_item()

        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person["id"], item_id=item["id"]))
        preview = self.main.kassa_person(person["id"])
        line_id = preview["lines"][0]["line_ids"][0]

        self.main.create_edit_request(
            self.main.EditRequestIn(
                person_id=person["id"],
                line_quantities={str(line_id): 1},
                reason="Falsch geklickt",
            )
        )
        with self.main.get_conn() as conn:
            pending = self.main.get_pending_requests_for_person(conn, person["id"])
            request_id = pending[0]["id"]
        self.main.admin_decide_change_request(
            self.main.AdminChangeRequestDecision(pin=PIN, request_id=request_id, decision="APPROVED")
        )
        self.main.admin_delete_person(self.main.AdminPersonDelete(pin=PIN, person_id=person["id"]))

        history = self.main.admin_person_history(
            self.main.AdminPersonHistoryRequest(pin=PIN, person_id=person["id"])
        )
        entries = history["history"]
        consume_entries = [entry for entry in entries if entry["type"] == "CONSUME"]
        correction = next(entry for entry in entries if entry["type"] == "CHANGE_APPROVED")

        self.assertEqual(sum(entry["quantity"] for entry in consume_entries), 1)
        self.assertEqual(correction["type_label"], "Korrektur gelöscht")
        self.assertEqual(correction["direction"], "correction")
        self.assertEqual(correction["quantity"], -1)
        self.assertEqual(correction["quantity_label"], "-1x")
        self.assertEqual(correction["product"], item["name"])
        self.assertEqual(correction["reason"], "Falsch geklickt")

    def test_kassa_person_history_shows_paid_round_as_orange_row_kind(self):
        person, _ = self.first_person_and_item()

        self.main.create_round_request(self.main.RoundRequestIn(person_id=person["id"], quantity=1))

        history = self.main.kassa_person_history(person["id"])
        round_entry = next(entry for entry in history["history"] if entry["type"] == "ROUND_REQUEST_APPROVED")
        self.assertEqual(round_entry["type_label"], "Runde bezahlt")
        self.assertEqual(round_entry["direction"], "round_payment")
        self.assertEqual(round_entry["quantity"], 1)
        self.assertEqual(round_entry["quantity_label"], "+1x")
        self.assertEqual(round_entry["product"], "1 Runde")

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
            transaction = conn.execute(
                "SELECT timestamp FROM transactions WHERE id = ?",
                (operation["transaction_id"],),
            ).fetchone()
            transaction_item = conn.execute(
                "SELECT timestamp FROM transaction_items WHERE transaction_id = ?",
                (operation["transaction_id"],),
            ).fetchone()
            order_line = conn.execute(
                """
                SELECT consumed_date, created_at
                FROM order_lines
                WHERE person_id = ? AND item_id = ?
                """,
                (person["id"], item["id"]),
            ).fetchone()

        self.assertEqual(quantity, 1)
        self.assertIsNotNone(operation["transaction_id"])
        self.assertTrue(transaction["timestamp"].startswith("2026-05-18 "))
        self.assertTrue(transaction_item["timestamp"].startswith("2026-05-18 "))
        self.assertEqual(order_line["consumed_date"], "2026-05-18")
        self.assertTrue(order_line["created_at"].startswith("2026-05-18 "))

    def test_csv_exports_include_utf8_bom_and_preserve_umlauts(self):
        first_name = "M\u00e4rk"
        last_name = "\u00d6hlinger"
        created = self.main.admin_create_person(
            self.main.AdminPersonCreate(pin=PIN, first_name=first_name, last_name=last_name)
        )
        person_id = created["id"]
        item = next(item for item in self.main.config()["user_items"] if item["name"] != "1 Runde")
        self.main.add_drink(self.main.AddDrinkRequest(person_id=person_id, item_id=item["id"]))

        response = self.main.export_open_balances(self.main.PinRequest(pin=PIN))
        body = asyncio.run(streaming_response_body(response))
        text = body.decode("utf-8-sig")

        self.assertTrue(body.startswith(codecs.BOM_UTF8))
        self.assertIn(f"{last_name} {first_name}", text)
        self.assertNotIn("M\u00c3\u00a4rk", text)

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

    def test_production_blocks_placeholder_pin_login(self):
        original_env = self.main.APP_ENV
        self.main.APP_ENV = "production"
        placeholder_pin = "change-this-pin"
        try:
            with self.main.get_conn() as conn:
                self.main.set_setting(conn, "admin_pin", placeholder_pin)
                with self.assertRaises(HTTPException) as ctx:
                    self.main.ensure_admin_login_allowed(conn)
                self.assertEqual(ctx.exception.status_code, 403)
                with self.assertRaises(HTTPException) as direct_ctx:
                    self.main.require_pin(conn, placeholder_pin)
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

    def start_event_with_two_items(self):
        item = next(item for item in self.main.config()["user_items"] if item["name"] != "1 Runde")
        started = self.main.admin_event_start(self.main.EventStartRequest(pin=PIN, name="Musikball Test"))
        self.assertEqual(started["status"], "ok")
        self.assertEqual(started["event"]["name"], "Musikball Test")
        self.assertIsNotNone(self.main.config()["active_event"])

        first = self.main.event_add_drink(self.main.EventAddDrinkRequest(item_id=item["id"]))
        second = self.main.event_add_drink(self.main.EventAddDrinkRequest(item_id=item["id"]))
        self.assertEqual(first["status"], "ok")
        self.assertEqual(second["status"], "ok")
        event = second["event"]
        self.assertEqual(event["quantity"], 2)
        self.assertEqual(event["lines"][0]["quantity"], 2)
        return item, event

    def test_event_plus_and_minus_are_logged_without_admin_pin(self):
        item, event = self.start_event_with_two_items()
        removed = self.main.event_remove_drink(self.main.EventRemoveDrinkRequest(item_id=item["id"], event_id=event["id"]))
        self.assertEqual(removed["event"]["quantity"], 1)
        self.assertEqual(removed["event"]["subtotal_eur"], item["price"])
        with self.main.get_conn() as conn:
            logs = conn.execute("SELECT * FROM transactions WHERE type IN ('EVENT_ITEM_ADDED', 'EVENT_ITEM_REMOVED') ORDER BY id").fetchall()
        self.assertEqual([row["type"] for row in logs], ["EVENT_ITEM_ADDED", "EVENT_ITEM_ADDED", "EVENT_ITEM_REMOVED"])
        self.assertEqual([row["total"] for row in logs], [item["price"], item["price"], -item["price"]])
        for row in logs:
            self.assertIn(f"Veranstaltung #{event['id']}", row["details"])
            self.assertIn(item["name"], row["details"])
            self.assertTrue(row["timestamp"])
        self.assertIn("+1x", logs[0]["details"])
        self.assertIn("-1x", logs[-1]["details"])

    def test_event_minus_cannot_make_quantity_negative(self):
        item, event = self.start_event_with_two_items()
        request = self.main.EventRemoveDrinkRequest(item_id=item["id"])
        self.main.event_remove_drink(request)
        empty = self.main.event_remove_drink(request)
        self.assertEqual(empty["event"]["quantity"], 0)
        self.assertEqual(empty["event"]["subtotal_eur"], 0)
        self.assertEqual(empty["event"]["lines"], [])
        with self.assertRaises(HTTPException) as ctx:
            self.main.event_remove_drink(request)
        self.assertEqual(ctx.exception.status_code, 400)
        with self.main.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT quantity FROM event_lines WHERE event_id = ?", (event["id"],)).fetchone()["quantity"], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions WHERE type = 'EVENT_ITEM_REMOVED'").fetchone()[0], 2)
        added = self.main.event_add_drink(self.main.EventAddDrinkRequest(item_id=item["id"]))
        self.assertEqual(added["event"]["quantity"], 1)

    def test_event_minus_uses_latest_positive_price_snapshot(self):
        item, _ = self.start_event_with_two_items()
        old_price = float(item["price"])
        with self.main.get_conn() as conn:
            conn.execute("UPDATE items SET price_eur = ? WHERE id = ?", (old_price + 1, item["id"]))
            conn.commit()
        self.main.event_add_drink(self.main.EventAddDrinkRequest(item_id=item["id"]))
        first = self.main.event_remove_drink(self.main.EventRemoveDrinkRequest(item_id=item["id"]))
        self.assertEqual(first["line"]["unit_price_eur"], old_price + 1)
        self.assertEqual(first["event"]["quantity"], 2)
        self.assertEqual(first["event"]["subtotal_eur"], old_price * 2)
        second = self.main.event_remove_drink(self.main.EventRemoveDrinkRequest(item_id=item["id"]))
        self.assertEqual(second["line"]["unit_price_eur"], old_price)
        self.assertEqual(second["event"]["subtotal_eur"], old_price)

    def test_event_changes_reject_stale_or_closed_event(self):
        item, event = self.start_event_with_two_items()
        add = self.main.EventAddDrinkRequest(item_id=item["id"], event_id=event["id"])
        remove = self.main.EventRemoveDrinkRequest(item_id=item["id"], event_id=event["id"])
        self.main.admin_event_end(self.main.EventEndRequest(pin=PIN))
        for action, request in ((self.main.event_add_drink, add), (self.main.event_remove_drink, remove)):
            with self.assertRaises(HTTPException) as ctx:
                action(request)
            self.assertEqual(ctx.exception.status_code, 400)
        self.main.admin_event_start(self.main.EventStartRequest(pin=PIN, name="New event"))
        for action, request in ((self.main.event_add_drink, add), (self.main.event_remove_drink, remove)):
            with self.assertRaises(HTTPException) as ctx:
                action(request)
            self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(self.main.event_active()["event"]["quantity"], 0)

    def test_event_concurrent_minus_only_removes_last_mark_once(self):
        item, _ = self.start_event_with_two_items()
        self.main.event_remove_drink(self.main.EventRemoveDrinkRequest(item_id=item["id"]))

        def remove_one():
            try:
                self.main.event_remove_drink(self.main.EventRemoveDrinkRequest(item_id=item["id"]))
                return 200
            except HTTPException as exc:
                return exc.status_code

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(lambda _: remove_one(), range(2)))
        self.assertEqual(sorted(outcomes), [200, 400])
        self.assertEqual(self.main.event_active()["event"]["quantity"], 0)
        with self.main.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions WHERE type = 'EVENT_ITEM_REMOVED'").fetchone()[0], 2)

    def test_event_mark_changes_roll_back_when_audit_log_fails(self):
        item, _ = self.start_event_with_two_items()
        original_log = self.main.log_transaction

        def fail_log(*args, **kwargs):
            raise RuntimeError("Audit unavailable")

        self.main.log_transaction = fail_log
        try:
            for action, request in (
                (self.main.event_add_drink, self.main.EventAddDrinkRequest(item_id=item["id"])),
                (self.main.event_remove_drink, self.main.EventRemoveDrinkRequest(item_id=item["id"])),
            ):
                with self.assertRaisesRegex(RuntimeError, "Audit unavailable"):
                    action(request)
                self.assertEqual(self.main.event_active()["event"]["quantity"], 2)
        finally:
            self.main.log_transaction = original_log

    def test_event_mode_start_add_discount_csv_pdf_and_close(self):
        self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_iban="AT611904300234573201")
        )
        item, event = self.start_event_with_two_items()
        line_id = str(event["lines"][0]["line_id"])
        preview = self.main.admin_event_preview_end(
            self.main.EventEndPreviewRequest(
                pin=PIN,
                line_discounts={line_id: "10,00"},
                total_discount_percent="20,00",
            )
        )
        expected_subtotal = round(float(item["price"]) * 2, 2)
        expected_line_discount = round(expected_subtotal * 0.10, 2)
        expected_total_discount = round((expected_subtotal - expected_line_discount) * 0.20, 2)
        self.assertEqual(preview["event"]["subtotal_eur"], expected_subtotal)
        self.assertEqual(preview["event"]["lines"][0]["line_discount_percent"], 10.0)
        self.assertEqual(preview["event"]["line_discount_total_eur"], expected_line_discount)
        self.assertEqual(preview["event"]["total_discount_percent"], 20.0)
        self.assertEqual(preview["event"]["total_discount_eur"], expected_total_discount)
        self.assertEqual(preview["event"]["final_total_eur"], round(expected_subtotal - expected_line_discount - expected_total_discount, 2))

        closed = self.main.admin_event_end(
            self.main.EventEndRequest(
                pin=PIN,
                line_discounts={line_id: "10,00"},
                total_discount_percent="20,00",
                create_invoice=True,
                email_invoice=False,
            )
        )
        self.assertEqual(closed["status"], "ok")
        self.assertEqual(closed["event"]["line_discount_total_eur"], expected_line_discount)
        self.assertEqual(closed["event"]["total_discount_eur"], expected_total_discount)
        self.assertEqual(closed["event"]["final_total_eur"], 3.60)
        self.assertIsNone(self.main.event_active()["event"])

        csv_path = Path(closed["artifacts"]["csv_path"])
        pdf_path = Path(closed["artifacts"]["pdf_path"])
        self.assertTrue(csv_path.exists())
        self.assertTrue(pdf_path.exists())
        self.assertTrue(pdf_path.read_bytes().startswith(b"%PDF-"))
        csv_text = csv_path.read_text(encoding="utf-8-sig")
        self.assertIn("Musikball Test", csv_text)
        self.assertIn("Positionsrabatt %", csv_text)
        self.assertIn("10.00", csv_text)
        self.assertIn("20.00", csv_text)
        self.assertIn("3.60", csv_text)
        pdf_text = pdf_path.read_bytes().decode("latin-1", errors="ignore")
        self.assertIn("Positionsrabatt 10.00%", pdf_text)
        self.assertIn("Gesamtrabatt 20.00%", pdf_text)
        self.assertIn("3.60", pdf_text)

    def test_event_mode_invoice_settings_persist_in_admin_overview(self):
        saved = self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(
                pin=PIN,
                invoice_cashier_email="kassier@example.org",
                invoice_recipient="Verein\nz.Hd. Kassier",
                invoice_sender_name="Wirtschaft",
                invoice_sender_address="Dorf 1",
                invoice_number_prefix="EVENT-{YYYY-MM-dd}",
                invoice_iban="at611904300234573201",
                invoice_logo_text="MVH",
                invoice_footer_text="Danke",
                invoice_place="Altach",
                invoice_notes="UID frei",
            )
        )
        self.assertEqual(saved["settings"]["invoice_cashier_email"], "kassier@example.org")
        self.assertEqual(saved["settings"]["invoice_number_prefix"], "EVENT-{YYYY-MM-dd}")
        overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
        self.assertEqual(overview["settings"]["invoice_cashier_email"], "kassier@example.org")
        self.assertEqual(overview["settings"]["invoice_recipient"], "Verein\nz.Hd. Kassier")
        self.assertEqual(overview["settings"]["invoice_iban"], "AT61 1904 3002 3457 3201")
        self.assertEqual(overview["settings"]["invoice_number_prefix"], "EVENT-{YYYY-MM-dd}")

    def test_invoice_number_date_formats_use_closing_date(self):
        cases = [
            ("EVENT", "2026-01-01", "EVENT-0042"),
            ("", "2026-01-01", "EVENT-0042"),
            ("RE-YYYY-MM-dd", "2026-01-01", "RE-YYYY-MM-dd-0042"),
            ("EVENT-{YYYY-MM-dd}", "2026-01-01", "EVENT-2026-01-01-0042"),
            ("RE-{dd.MM.YYYY}", "2028-02-29", "RE-29.02.2028-0042"),
            ("{YYYYMM}", "2026-09-09", "202609-0042"),
            ("RE-{YY}/{MM}/{dd}", "2026-01-01", "RE-26/01/01-0042"),
            ("{YYYY_MM_dd}", "2026-09-09", "2026_09_09-0042"),
            ("{YYYY-MM-dd}", "2021-01-01", "2021-01-01-0042"),
        ]
        for prefix, end_date, expected in cases:
            with self.subTest(prefix=prefix, end_date=end_date):
                summary = {"id": 42, "start_time": "2020-12-31 18:00:00", "end_time": f"{end_date} 01:30:00"}
                actual = self.main.event_service.invoice_number_for_summary(summary, {"invoice_number_prefix": prefix})
                self.assertEqual(actual, expected)

    def test_invoice_settings_reject_invalid_date_placeholders_without_changing_settings(self):
        self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_number_prefix="RE-{YYYY}", invoice_sender_name="Original")
        )
        for prefix in ("RE-{YYYY-MM-DD}", "RE-{YYYY-mm-dd}", "RE-{YYYY-MMM-dd}", "RE-{YYYY", "RE-YYYY}", "RE-{}", "RE-{{YYYY}}", "RE-{date}"):
            with self.subTest(prefix=prefix), self.assertRaises(HTTPException) as ctx:
                self.main.admin_invoice_settings_update(
                    self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_number_prefix=prefix, invoice_sender_name="Changed")
                )
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("Datumsplatzhalter", ctx.exception.detail)
            self.assertIn("EVENT-{YYYY-MM-dd}", ctx.exception.detail)
            overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
            self.assertEqual(overview["settings"]["invoice_number_prefix"], "RE-{YYYY}")
            self.assertEqual(overview["settings"]["invoice_sender_name"], "Original")

    def test_event_close_resolves_date_prefix_and_keeps_template_saved(self):
        self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_number_prefix="RE-{YYYY-MM-dd}")
        )
        self.start_event_with_two_items()
        closed = self.main.admin_event_end(self.main.EventEndRequest(pin=PIN, create_invoice=True))
        event = closed["event"]
        expected = f"RE-{event['end_time'][:10]}-{event['id']:04d}"
        pdf_text = Path(closed["artifacts"]["pdf_path"]).read_bytes().decode("latin-1")
        self.assertIn(expected, pdf_text)
        self.assertNotIn("{YYYY-MM-dd}", pdf_text)
        overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
        self.assertEqual(overview["settings"]["invoice_number_prefix"], "RE-{YYYY-MM-dd}")

    def test_invoice_pdf_includes_payment_text_and_sepa_qr_payload(self):
        summary = {
            "id": 42,
            "name": "Musikball Test",
            "start_time": "2026-01-01 18:00:00",
            "end_time": "2026-01-01 23:00:00",
            "lines": [],
            "subtotal_eur": 123.45,
            "line_discount_total_eur": 0.0,
            "total_discount_percent": 0.0,
            "total_discount_eur": 0.0,
            "final_total_eur": 123.45,
        }
        settings = {
            **self.main.event_service.INVOICE_SETTING_DEFAULTS,
            "invoice_sender_name": "MVH Altach Wirtschaft",
            "invoice_number_prefix": "TEST-{YYYY-MM-dd}",
            "invoice_iban": "AT61 1904 3002 3457 3201",
        }
        path = Path(self.temp_dir.name) / "rechnung.pdf"
        self.main.event_service.write_simple_invoice_pdf(path, summary, settings, include_qr_code=True)
        pdf_text = path.read_bytes().decode("latin-1", errors="ignore")
        self.assertIn("SEPA-QR-Code", pdf_text)
        self.assertGreater(pdf_text.count(" re f "), 500)
        self.assertIn("IBAN AT61 1904 3002 3457 3201", pdf_text)
        self.assertIn("(TEST-2026-01-01-0042)", pdf_text)
        self.assertIn("Verwendungszweck: Rechnung TEST-2026-01-01-0042", pdf_text)
        self.assertNotIn("{YYYY-MM-dd}", pdf_text)
        payload_lines = self.main.event_service.sepa_qr_payload(summary, settings).splitlines()
        self.assertEqual(payload_lines[:4], ["BCD", "002", "1", "SCT"])
        self.assertEqual(payload_lines[6], "AT611904300234573201")
        self.assertEqual(payload_lines[7], "EUR123.45")
        self.assertEqual(payload_lines[10], "Rechnung TEST-2026-01-01-0042")

    def test_invoice_qr_requires_iban_and_keeps_event_open(self):
        self.start_event_with_two_items()
        for options in ({"create_invoice": True}, {"email_invoice": True}):
            with self.subTest(options=options), self.assertRaises(HTTPException) as ctx:
                self.main.admin_event_end(self.main.EventEndRequest(pin=PIN, include_invoice_qr=True, **options))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("IBAN", ctx.exception.detail)
            self.assertIn("Einstellungen speichern", ctx.exception.detail)
            self.assertIsNotNone(self.main.event_active()["event"])
            self.assertFalse(list(Path(self.temp_dir.name).rglob("*.pdf")))

    def test_invoice_settings_reject_invalid_iban(self):
        for iban in ("AT000000000000000000", "AT611904300234573202", "AT61!1904300234573201"):
            with self.subTest(iban=iban), self.assertRaises(HTTPException) as ctx:
                self.main.admin_invoice_settings_update(
                    self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_iban=iban)
                )
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("IBAN", ctx.exception.detail)

    def test_invoice_fails_explicitly_when_qr_dependency_is_missing(self):
        self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_iban="AT611904300234573201")
        )
        self.start_event_with_two_items()
        original = self.main.event_service.qrcode
        self.main.event_service.qrcode = None
        try:
            with self.assertRaises(HTTPException) as ctx:
                self.main.admin_event_end(self.main.EventEndRequest(pin=PIN, create_invoice=True, include_invoice_qr=True))
            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("QR-Code-Bibliothek fehlt", ctx.exception.detail)
            self.assertIsNotNone(self.main.event_active()["event"])
            self.assertFalse(list(Path(self.temp_dir.name).rglob("*.pdf")))
        finally:
            self.main.event_service.qrcode = original

    def test_invoice_without_iban_or_qr_dependency_can_close_event(self):
        self.start_event_with_two_items()
        original = self.main.event_service.qrcode
        self.main.event_service.qrcode = None
        try:
            closed = self.main.admin_event_end(self.main.EventEndRequest(pin=PIN, create_invoice=True))
        finally:
            self.main.event_service.qrcode = original
        text = Path(closed["artifacts"]["pdf_path"]).read_bytes().decode("latin-1")
        self.assertIn("Rechnungsbetrag", text)
        self.assertNotIn("SEPA-QR-Code", text)
        self.assertNotIn("IBAN", text)
        self.assertFalse(closed["artifacts"]["mail_sent"])
        self.assertIsNone(self.main.event_active()["event"])

    def test_invoice_qr_preview_checks_saved_iban(self):
        self.start_event_with_two_items()
        for iban, available in (("", False), ("AT611904300234573202", False), ("AT611904300234573201", True)):
            with self.subTest(iban=iban):
                with self.main.get_conn() as conn:
                    self.main.set_setting(conn, "invoice_iban", iban)
                    conn.commit()
                preview = self.main.admin_event_preview_end(self.main.EventEndPreviewRequest(pin=PIN))
                self.assertEqual(preview["invoice_options"]["qr_code_available"], available)

    def test_invoice_valid_iban_does_not_force_qr(self):
        self.start_event_with_two_items()
        self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_iban="AT611904300234573201")
        )
        closed = self.main.admin_event_end(self.main.EventEndRequest(pin=PIN, create_invoice=True))
        text = Path(closed["artifacts"]["pdf_path"]).read_bytes().decode("latin-1")
        self.assertIn("IBAN AT61 1904 3002 3457 3201", text)
        self.assertNotIn("SEPA-QR-Code", text)

    def test_invoice_qr_selection_creates_pdf(self):
        self.start_event_with_two_items()
        self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_iban="AT611904300234573201")
        )
        closed = self.main.admin_event_end(self.main.EventEndRequest(pin=PIN, include_invoice_qr=True))
        text = Path(closed["artifacts"]["pdf_path"]).read_bytes().decode("latin-1")
        self.assertIn("SEPA-QR-Code", text)
        self.assertGreater(text.count(" re f "), 500)

    def test_mail_settings_persist_sanitized_and_preserve_password(self):
        saved = self.main.admin_mail_settings_update(
            self.main.MailSettingsUpdateRequest(
                pin=PIN,
                mail_smtp_provider="ionos",
                mail_smtp_host="smtp.ionos.com",
                mail_smtp_port="587",
                mail_smtp_username="kassier@example.org",
                mail_smtp_password="secret-pass",
                mail_smtp_encryption="starttls",
            )
        )
        self.assertEqual(saved["settings"]["mail_smtp_host"], "smtp.ionos.com")
        self.assertEqual(saved["settings"]["mail_smtp_from"], "kassier@example.org")
        self.assertTrue(saved["settings"]["mail_smtp_password_set"])
        self.assertNotIn("mail_smtp_password", saved["settings"])

        overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
        self.assertTrue(overview["settings"]["mail_smtp_password_set"])
        self.assertNotIn("mail_smtp_password", overview["settings"])

        self.main.admin_mail_settings_update(
            self.main.MailSettingsUpdateRequest(pin=PIN, mail_smtp_host="smtp2.ionos.com")
        )
        with self.main.get_conn() as conn:
            settings = self.main.event_service.get_mail_settings(conn, include_secret=True)
        self.assertEqual(settings["mail_smtp_password"], "secret-pass")
        self.assertEqual(settings["mail_smtp_host"], "smtp2.ionos.com")
        self.assertEqual(settings["mail_smtp_from"], "kassier@example.org")

    def test_mail_test_recipient_persists_independently_from_cashier(self):
        self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_cashier_email="cashier@example.org")
        )
        saved = self.main.admin_mail_settings_update(
            self.main.MailSettingsUpdateRequest(pin=PIN, mail_test_recipient="  tester@example.org  ")
        )
        self.assertEqual(saved["settings"]["mail_test_recipient"], "tester@example.org")
        self.main.admin_mail_settings_update(
            self.main.MailSettingsUpdateRequest(pin=PIN, mail_smtp_provider="world4you")
        )
        self.main.admin_invoice_settings_update(
            self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_cashier_email="new-cashier@example.org")
        )
        self.main.init_db()
        overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
        self.assertEqual(overview["settings"]["mail_test_recipient"], "tester@example.org")
        self.assertEqual(overview["settings"]["invoice_cashier_email"], "new-cashier@example.org")
        self.main.admin_mail_settings_update(self.main.MailSettingsUpdateRequest(pin=PIN, mail_test_recipient=""))
        overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
        self.assertEqual(overview["settings"]["mail_test_recipient"], "")
        self.assertEqual(overview["settings"]["invoice_cashier_email"], "new-cashier@example.org")

    def test_mail_test_recipient_validation_preserves_saved_value(self):
        self.main.admin_mail_settings_update(self.main.MailSettingsUpdateRequest(pin=PIN, mail_test_recipient="tester@example.org"))
        for recipient in ("not-an-email", "one@example.org two@example.org", "a@example.org\r\nBcc: b@example.org", "x" * 240 + "@example.org"):
            with self.subTest(recipient=recipient), self.assertRaises(HTTPException) as ctx:
                self.main.admin_mail_settings_update(self.main.MailSettingsUpdateRequest(pin=PIN, mail_test_recipient=recipient))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("Test-Empf", ctx.exception.detail)
            overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
            self.assertEqual(overview["settings"]["mail_test_recipient"], "tester@example.org")

    def test_mail_test_uses_saved_or_explicit_recipient_never_cashier(self):
        self.main.admin_invoice_settings_update(self.main.InvoiceSettingsUpdateRequest(pin=PIN, invoice_cashier_email="cashier@example.org"))
        calls = []
        original_send = self.main.event_service.send_smtp_message

        def fake_send(settings, recipient, *args, **kwargs):
            calls.append(recipient)

        self.main.event_service.send_smtp_message = fake_send
        try:
            with self.assertRaises(HTTPException) as ctx:
                self.main.admin_mail_settings_test(self.main.MailTestRequest(pin=PIN))
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertIn("fehlt", ctx.exception.detail)
            self.assertEqual(calls, [])
            self.main.admin_mail_settings_update(self.main.MailSettingsUpdateRequest(pin=PIN, mail_test_recipient="tester@example.org"))
            self.main.admin_mail_settings_test(self.main.MailTestRequest(pin=PIN))
            self.main.admin_mail_settings_test(self.main.MailTestRequest(pin=PIN, recipient="other@example.org"))
            self.assertEqual(calls, ["tester@example.org", "other@example.org"])
            for recipient in ("", "   ", "invalid"):
                with self.subTest(recipient=recipient), self.assertRaises(HTTPException) as ctx:
                    self.main.admin_mail_settings_test(self.main.MailTestRequest(pin=PIN, recipient=recipient))
                self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(calls, ["tester@example.org", "other@example.org"])
            overview = self.main.admin_overview(self.main.PinRequest(pin=PIN))
            self.assertEqual(overview["settings"]["mail_test_recipient"], "tester@example.org")
        finally:
            self.main.event_service.send_smtp_message = original_send

    def test_mail_settings_accept_world4you_provider(self):
        saved = self.main.admin_mail_settings_update(
            self.main.MailSettingsUpdateRequest(
                pin=PIN,
                mail_smtp_provider="world4you",
                mail_smtp_host="smtp.world4you.com",
                mail_smtp_port="587",
                mail_smtp_username="verein@example.org",
                mail_smtp_password="secret-pass",
                mail_smtp_encryption="starttls",
            )
        )
        self.assertEqual(saved["settings"]["mail_smtp_provider"], "world4you")
        self.assertEqual(saved["settings"]["mail_smtp_host"], "smtp.world4you.com")
        self.assertEqual(saved["settings"]["mail_smtp_port"], "587")
        self.assertEqual(saved["settings"]["mail_smtp_encryption"], "starttls")
        self.assertEqual(saved["settings"]["mail_smtp_from"], "verein@example.org")

    def test_mail_test_sends_with_starttls_settings(self):
        calls = []
        original_smtp = self.main.event_service.smtplib.SMTP

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                calls.append(("connect", host, port, timeout))

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def starttls(self):
                calls.append(("starttls",))

            def login(self, username, password):
                calls.append(("login", username, password))

            def send_message(self, message):
                calls.append(("send", message["To"], message["From"], message["Subject"]))

        self.main.event_service.smtplib.SMTP = FakeSMTP
        try:
            self.main.admin_mail_settings_update(
                self.main.MailSettingsUpdateRequest(
                    pin=PIN,
                    mail_smtp_host="smtp.ionos.com",
                    mail_smtp_port="587",
                    mail_smtp_username="kassier@example.org",
                    mail_smtp_password="secret-pass",
                    mail_smtp_encryption="starttls",
                )
            )
            result = self.main.admin_mail_settings_test(
                self.main.MailTestRequest(pin=PIN, recipient="test@example.org")
            )
        finally:
            self.main.event_service.smtplib.SMTP = original_smtp
        self.assertEqual(result["status"], "ok")
        self.assertEqual(calls[0][:3], ("connect", "smtp.ionos.com", 587))
        self.assertIn(("starttls",), calls)
        self.assertIn(("login", "kassier@example.org", "secret-pass"), calls)
        self.assertIn(("send", "test@example.org", "kassier@example.org", "Drink POS Testmail"), calls)

    def test_mail_test_reports_authentication_error(self):
        original_smtp = self.main.event_service.smtplib.SMTP
        auth_error = self.main.event_service.smtplib.SMTPAuthenticationError

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def starttls(self):
                pass

            def login(self, username, password):
                raise auth_error(535, b"Authentication credentials invalid")

            def send_message(self, message):
                raise AssertionError("send_message should not run after failed login")

        self.main.event_service.smtplib.SMTP = FakeSMTP
        try:
            self.main.admin_mail_settings_update(
                self.main.MailSettingsUpdateRequest(
                    pin=PIN,
                    mail_smtp_host="smtp.ionos.com",
                    mail_smtp_port="587",
                    mail_smtp_username="kassier@example.org",
                    mail_smtp_password="wrong-pass",
                    mail_smtp_encryption="starttls",
                )
            )
            with self.assertRaises(HTTPException) as ctx:
                self.main.admin_mail_settings_test(
                    self.main.MailTestRequest(pin=PIN, recipient="test@example.org")
                )
        finally:
            self.main.event_service.smtplib.SMTP = original_smtp
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("SMTP-Login fehlgeschlagen", ctx.exception.detail)
        self.assertIn("Benutzername oder Passwort", ctx.exception.detail)

    def test_mail_test_sends_with_ssl_settings(self):
        calls = []
        original_smtp_ssl = self.main.event_service.smtplib.SMTP_SSL

        class FakeSMTPSSL:
            def __init__(self, host, port, timeout=None):
                calls.append(("ssl-connect", host, port, timeout))

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def login(self, username, password):
                calls.append(("login", username, password))

            def send_message(self, message):
                calls.append(("send", message["To"], message["From"], message["Subject"]))

        self.main.event_service.smtplib.SMTP_SSL = FakeSMTPSSL
        try:
            self.main.admin_mail_settings_update(
                self.main.MailSettingsUpdateRequest(
                    pin=PIN,
                    mail_smtp_provider="magenta",
                    mail_smtp_host="mail.mymagenta.business",
                    mail_smtp_port="465",
                    mail_smtp_username="kassier@example.org",
                    mail_smtp_password="secret-pass",
                    mail_smtp_encryption="ssl",
                )
            )
            result = self.main.admin_mail_settings_test(
                self.main.MailTestRequest(pin=PIN, recipient="test@example.org")
            )
        finally:
            self.main.event_service.smtplib.SMTP_SSL = original_smtp_ssl
        self.assertEqual(result["status"], "ok")
        self.assertEqual(calls[0][:3], ("ssl-connect", "mail.mymagenta.business", 465))
        self.assertIn(("login", "kassier@example.org", "secret-pass"), calls)
        self.assertIn(("send", "test@example.org", "kassier@example.org", "Drink POS Testmail"), calls)

    def test_event_end_requires_csv_before_closing(self):
        self.start_event_with_two_items()
        original = self.main.event_service.save_event_csv

        def fail_csv(db_path, event, summary):
            raise OSError("disk full")

        self.main.event_service.save_event_csv = fail_csv
        try:
            with self.assertRaises(HTTPException) as ctx:
                self.main.admin_event_end(self.main.EventEndRequest(pin=PIN))
            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("CSV konnte nicht gespeichert", ctx.exception.detail)
            self.assertIsNotNone(self.main.event_active()["event"])
        finally:
            self.main.event_service.save_event_csv = original

    def test_event_end_keeps_event_open_when_pdf_fails_after_csv(self):
        _, event = self.start_event_with_two_items()
        line_id = str(event["lines"][0]["line_id"])
        original_pdf = self.main.event_service.generate_event_invoice_pdf

        def fail_pdf(db_path, event, summary, settings, include_qr_code=False):
            raise RuntimeError("pdf boom")

        self.main.event_service.generate_event_invoice_pdf = fail_pdf
        try:
            with self.assertRaises(HTTPException) as ctx:
                self.main.admin_event_end(
                    self.main.EventEndRequest(pin=PIN, line_discounts={line_id: "0"}, create_invoice=True)
                )
            self.assertEqual(ctx.exception.status_code, 500)
            self.assertIn("pdf boom", ctx.exception.detail)
            self.assertIsNotNone(self.main.event_active()["event"])
            csv_dir = Path(self.temp_dir.name) / "events"
            self.assertTrue(any(csv_dir.glob("*.csv")))
        finally:
            self.main.event_service.generate_event_invoice_pdf = original_pdf

    def test_event_end_orders_csv_pdf_mail_and_mail_forces_invoice(self):
        self.start_event_with_two_items()
        calls = []
        original_csv = self.main.event_service.save_event_csv
        original_pdf = self.main.event_service.generate_event_invoice_pdf
        original_mail = self.main.event_service.send_event_invoice_email

        def fake_csv(db_path, event, summary):
            calls.append("csv")
            path = Path(self.temp_dir.name) / "events" / "ordered.csv"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("csv", encoding="utf-8")
            return str(path)

        def fake_pdf(db_path, event, summary, settings, include_qr_code=False):
            calls.append("pdf")
            self.assertEqual(calls, ["csv", "pdf"])
            path = Path(self.temp_dir.name) / "events" / "ordered.pdf"
            path.write_bytes(b"%PDF-1.4\n%test")
            return str(path)

        def fake_mail(pdf_path, summary, settings, copy_to_sender=False, send_to_cashier=True, recipient=None):
            calls.append("mail")
            self.assertEqual(calls, ["csv", "pdf", "mail"])
            self.assertTrue(str(pdf_path).endswith(".pdf"))
            self.assertTrue(copy_to_sender)
            self.assertTrue(send_to_cashier)
            self.assertIsNone(recipient)
            return True

        self.main.event_service.save_event_csv = fake_csv
        self.main.event_service.generate_event_invoice_pdf = fake_pdf
        self.main.event_service.send_event_invoice_email = fake_mail
        try:
            closed = self.main.admin_event_end(
                self.main.EventEndRequest(pin=PIN, create_invoice=False, email_invoice=True, copy_invoice_to_sender=True)
            )
        finally:
            self.main.event_service.save_event_csv = original_csv
            self.main.event_service.generate_event_invoice_pdf = original_pdf
            self.main.event_service.send_event_invoice_email = original_mail
        self.assertEqual(calls, ["csv", "pdf", "mail"])
        self.assertTrue(closed["event"]["invoice_created"])
        self.assertTrue(closed["event"]["invoice_mail_sent"])
        self.assertTrue(closed["artifacts"]["mail_copy_sent"])
        self.assertIsNone(self.main.event_active()["event"])

    def test_event_invoice_mail_copy_uses_smtp_sender_as_bcc(self):
        calls = []
        original_smtp = self.main.event_service.smtplib.SMTP

        class FakeSMTP:
            def __init__(self, host, port, timeout=None):
                calls.append(("connect", host, port))

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def starttls(self):
                calls.append(("starttls",))

            def login(self, username, password):
                calls.append(("login", username, password))

            def send_message(self, message):
                calls.append(("send", message["To"], message["From"], message["Bcc"]))

        pdf_path = Path(self.temp_dir.name) / "rechnung.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%test")
        settings = {
            "invoice_cashier_email": "kassier@example.org",
            "mail_smtp_host": "smtp.example.org",
            "mail_smtp_port": "587",
            "mail_smtp_username": "absender@example.org",
            "mail_smtp_password": "secret-pass",
            "mail_smtp_encryption": "starttls",
        }
        self.main.event_service.smtplib.SMTP = FakeSMTP
        try:
            copied = self.main.event_service.send_event_invoice_email(
                str(pdf_path),
                {"name": "Musikball Test"},
                settings,
                copy_to_sender=True,
            )
        finally:
            self.main.event_service.smtplib.SMTP = original_smtp
        self.assertTrue(copied)
        self.assertIn(("send", "kassier@example.org", "absender@example.org", "absender@example.org"), calls)

    def test_invoice_mail_recipient_options_are_independent(self):
        self.main.admin_mail_settings_update(self.main.MailSettingsUpdateRequest(
            pin=PIN, mail_smtp_host="smtp.example.org", mail_smtp_username="absender@example.org",
        ))
        original = self.main.event_service.send_smtp_message
        calls = []

        def fake_send(settings, recipient, subject, body, attachments=None, cc=None, bcc=None):
            self.assertEqual(len(attachments), 1)
            self.assertTrue(attachments[0].read_bytes().startswith(b"%PDF-"))
            calls.append((recipient, bcc))

        self.main.event_service.send_smtp_message = fake_send
        try:
            for cashier, sender, expected in (
                (False, True, ("absender@example.org", [])),
                (True, False, ("kassier@example.org", [])),
                (True, True, ("kassier@example.org", ["absender@example.org"])),
            ):
                with self.subTest(cashier=cashier, sender=sender):
                    self.main.admin_invoice_settings_update(self.main.InvoiceSettingsUpdateRequest(
                        pin=PIN, invoice_cashier_email="kassier@example.org" if cashier else "",
                    ))
                    self.start_event_with_two_items()
                    closed = self.main.admin_event_end(self.main.EventEndRequest(
                        pin=PIN, email_invoice=cashier, copy_invoice_to_sender=sender,
                    ))
                    self.assertEqual(calls[-1], expected)
                    self.assertTrue(closed["artifacts"]["mail_sent"])
                    self.assertEqual(closed["artifacts"]["mail_copy_sent"], sender)
                    with self.main.get_conn() as conn:
                        row = conn.execute("SELECT invoice_mail_to FROM event_sessions WHERE id = ?", (closed["event"]["id"],)).fetchone()
                    self.assertEqual(row["invoice_mail_to"], ", ".join([expected[0], *expected[1]]))
        finally:
            self.main.event_service.send_smtp_message = original

    def test_external_invoice_recipient_replaces_cashier_and_mail_target(self):
        self.main.admin_mail_settings_update(self.main.MailSettingsUpdateRequest(
            pin=PIN, mail_smtp_host="smtp.example.org", mail_smtp_username="absender@example.org",
        ))
        self.main.admin_invoice_settings_update(self.main.InvoiceSettingsUpdateRequest(
            pin=PIN, invoice_cashier_email="kassier@example.org", invoice_recipient="Verein\nz.Hd. Kassier",
        ))
        original = self.main.event_service.send_smtp_message
        calls = []

        def fake_send(settings, recipient, subject, body, attachments=None, cc=None, bcc=None):
            calls.append((recipient, bcc))
            pdf_text = attachments[0].read_bytes().decode("latin-1", errors="ignore")
            self.assertIn("Max Mustermann GmbH", pdf_text)
            self.assertIn("Hauptstrasse 1", pdf_text)
            self.assertNotIn("z.Hd. Kassier", pdf_text)

        self.main.event_service.send_smtp_message = fake_send
        try:
            self.start_event_with_two_items()
            closed = self.main.admin_event_end(self.main.EventEndRequest(
                pin=PIN,
                email_invoice=True,
                copy_invoice_to_sender=True,
                external_recipient=True,
                external_recipient_name="Max Mustermann GmbH",
                external_recipient_email="extern@example.org",
                external_recipient_address="Hauptstrasse 1\n6844 Altach",
            ))
        finally:
            self.main.event_service.send_smtp_message = original
        self.assertEqual(calls, [("extern@example.org", ["absender@example.org"])])
        self.assertEqual(closed["artifacts"]["mail_copy_sent"], True)
        with self.main.get_conn() as conn:
            row = conn.execute("SELECT invoice_mail_to FROM event_sessions WHERE id = ?", (closed["event"]["id"],)).fetchone()
        self.assertEqual(row["invoice_mail_to"], "extern@example.org, absender@example.org")

    def test_external_invoice_can_be_created_without_mail_and_rejects_missing_fields(self):
        self.start_event_with_two_items()
        with self.assertRaises(HTTPException) as ctx:
            self.main.admin_event_end(self.main.EventEndRequest(
                pin=PIN, create_invoice=True, external_recipient=True,
            ))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Name/Firma", ctx.exception.detail)
        self.assertIsNotNone(self.main.event_active()["event"])

        closed = self.main.admin_event_end(self.main.EventEndRequest(
            pin=PIN,
            create_invoice=True,
            external_recipient=True,
            external_recipient_name="Externer Kunde",
            external_recipient_address="Kundenweg 4\n6800 Feldkirch",
        ))
        pdf_text = Path(closed["artifacts"]["pdf_path"]).read_bytes().decode("latin-1", errors="ignore")
        self.assertIn("Externer Kunde", pdf_text)
        self.assertIn("Kundenweg 4", pdf_text)
        self.assertNotIn("z.Hd. Kassier", pdf_text)
        self.assertFalse(closed["artifacts"]["mail_sent"])

    def test_external_invoice_copy_only_goes_to_sender(self):
        self.main.admin_mail_settings_update(self.main.MailSettingsUpdateRequest(
            pin=PIN, mail_smtp_host="smtp.example.org", mail_smtp_username="absender@example.org",
        ))
        original = self.main.event_service.send_smtp_message
        calls = []

        def fake_send(settings, recipient, subject, body, attachments=None, cc=None, bcc=None):
            calls.append((recipient, bcc))

        self.main.event_service.send_smtp_message = fake_send
        try:
            self.start_event_with_two_items()
            self.main.admin_event_end(self.main.EventEndRequest(
                pin=PIN,
                copy_invoice_to_sender=True,
                external_recipient=True,
                external_recipient_name="Externer Kunde",
                external_recipient_email="extern@example.org",
            ))
        finally:
            self.main.event_service.send_smtp_message = original
        self.assertEqual(calls, [("absender@example.org", [])])

    def test_external_invoice_mail_requires_external_email(self):
        self.start_event_with_two_items()
        with self.assertRaises(HTTPException) as ctx:
            self.main.admin_event_end(self.main.EventEndRequest(
                pin=PIN,
                email_invoice=True,
                external_recipient=True,
                external_recipient_name="Externer Kunde",
            ))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("E-Mail-Adresse", ctx.exception.detail)
        self.assertIsNotNone(self.main.event_active()["event"])

    def test_event_frontend_checkbox_dependency_and_return_to_standard(self):
        html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
        self.assertIn("function syncEventInvoiceOptions()", html)
        self.assertIn("createInvoice.checked = true", html)
        self.assertIn("createInvoice.disabled = true", html)
        self.assertIn("createInvoice.disabled = false", html)
        self.assertIn("eventCopyInvoiceToSender", html)
        self.assertIn("copy_invoice_to_sender", html)
        self.assertIn("eventExternalRecipient", html)
        self.assertIn("external_recipient_email", html)
        self.assertIn("Rechnung per Mail an externen Empfänger senden", html)
        self.assertIn("activeEvent = null", html)
        self.assertIn("standardModeView", html)


if __name__ == "__main__":
    unittest.main()
