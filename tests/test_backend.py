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
