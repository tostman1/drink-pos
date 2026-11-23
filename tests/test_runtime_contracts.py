"""Characterize the served ASGI runtime, not unused extraction scaffolding."""

import importlib
import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts.standard_checks import test_environment


class RuntimeContractTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix="drink-pos-http-")))
        self.stack.enter_context(patch.dict(os.environ, test_environment(directory), clear=True))
        from app import application
        from app.db import schema

        previous = (schema.DB_PATH, schema.ENV_PIN_CODE, schema.ENV_PIN_FROM_ENV, schema.get_conn)
        self.stack.callback(schema.configure_runtime, *previous)
        app, self.legacy = application.create_app("app")
        self.client = self.stack.enter_context(TestClient(app))
        self.person = self.client.get("/api/people").json()[0]
        self.item = self.client.get("/api/config").json()["user_items"][0]

    def post(self, path, payload):
        response = self.client.post(path, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def book(self):
        return self.post("/api/add-drink", {"person_id": self.person["id"], "item_id": self.item["id"]})

    def test_served_routes_enforce_auth_validation_and_safe_config(self):
        health = self.client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertGreater(health.json()["people"], 0)  # startup ran, not prototype /health
        for path in ("/", "/admin", "/kassa", "/self-pay", "/manifest.webmanifest", "/service-worker.js"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        paths = self.client.get("/openapi.json").json()["paths"]
        self.assertIn("/api/event/add-drink", paths)
        self.assertIn("/api/agent/state", paths)
        self.assertEqual(self.client.post("/api/admin/overview", json={"pin": "wrong"}).status_code, 403)
        self.assertEqual(self.client.post("/api/add-drink", json={"person_id": "invalid"}).status_code, 422)
        self.assertEqual(self.client.get("/api/transactions").status_code, 403)
        self.assertEqual(self.client.get("/api/agent/state").status_code, 404)
        self.legacy.APP_ENV = "production"
        self.assertEqual(self.client.get("/health").json()["database"]["path"], "hidden")
        self.assertEqual(self.client.post("/api/admin/overview", json={"pin": "1234"}).status_code, 403)
        self.assertNotIn("sumup_api_key", self.client.get("/api/self-pay/config").json())

    def test_cashup_preserves_debt_and_cash_payment_settles_it(self):
        self.book()
        self.post("/api/admin/cashup", {"pin": "1234"})
        with self.legacy.get_conn() as conn:
            line = conn.execute(
                "SELECT quantity, event_open FROM order_lines WHERE person_id = ?", (self.person["id"],)
            ).fetchone()
            self.assertEqual(tuple(line), (1, 0))
        preview = self.client.get(f"/api/kassa/person/{self.person['id']}").json()
        self.assertEqual(preview["total"], self.item["price"])
        self.assertTrue(preview["can_pay"])
        self.post(
            "/api/kassa/pay", {"pin": "1234", "person_id": self.person["id"], "expected_revision": preview["revision"]}
        )
        self.assertEqual(self.client.get(f"/api/kassa/person/{self.person['id']}").json()["lines"], [])
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT type FROM transactions ORDER BY id DESC LIMIT 1").fetchone()[0], "PAID_CASH"
            )

    def test_snapshot_and_archived_item_debt_remain_payable(self):
        self.book()
        with self.legacy.get_conn() as conn:
            original = dict(
                conn.execute("SELECT * FROM order_lines WHERE person_id = ?", (self.person["id"],)).fetchone()
            )
            conn.execute(
                "UPDATE items SET price_eur = 99, purchase_price_eur = 98, name = 'Changed', short_label = 'X', admin_only = 1, active = 0, archived_at = ? WHERE id = ?",
                (self.legacy.now_text(), self.item["id"]),
            )
            conn.commit()
        preview = self.client.get(f"/api/kassa/person/{self.person['id']}").json()
        self.assertEqual(preview["total"], self.item["price"])
        self.assertTrue(preview["can_pay"])
        self.assertIn(self.item["name"], str(preview["lines"]))
        self.post("/api/pay", {"pin": "1234", "person_id": self.person["id"]})
        with self.legacy.get_conn() as conn:
            paid = dict(conn.execute("SELECT * FROM order_lines WHERE id = ?", (original["id"],)).fetchone())
            self.assertEqual(paid["quantity"], 0)
            for key in (
                "unit_price_eur",
                "unit_purchase_price_eur",
                "item_name_snapshot",
                "item_short_label_snapshot",
                "admin_only_snapshot",
            ):
                self.assertEqual(paid[key], original[key])

    def test_booking_rolls_back_when_audit_fails(self):
        with patch.object(self.legacy, "log_transaction", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaisesRegex(RuntimeError, "audit unavailable"):
                self.book()
        with self.legacy.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM order_lines").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 0)
        self.book()

    def test_top_level_import_still_has_registry(self):
        # Existing test_modular_imports covers package mode; container covers main.
        module = importlib.import_module("app.main")
        self.assertTrue(hasattr(module.app.state, "route_registry"))

    def test_agent_round_request_immediately_charges_but_cannot_pay(self):
        os.environ["DRINK_POS_AGENT_TOKEN"] = "synthetic-agent-token"
        headers = {"Authorization": "Bearer synthetic-agent-token"}
        response = self.client.post(
            "/api/agent/round-request", headers=headers, json={"person_id": self.person["id"], "quantity": 1}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "approved")
        with self.legacy.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT status FROM round_requests").fetchone()[0], "APPROVED")
            self.assertEqual(
                tuple(conn.execute("SELECT item_name_snapshot, quantity FROM order_lines").fetchone()), ("1 Runde", 1)
            )
            self.assertEqual(
                conn.execute("SELECT type FROM transactions ORDER BY id DESC LIMIT 1").fetchone()[0],
                "ROUND_REQUEST_APPROVED",
            )
        pay = self.client.post(
            "/api/pay", headers=headers, json={"person_id": self.person["id"], "pin": "synthetic-agent-token"}
        )
        self.assertEqual(pay.status_code, 403)

    def test_http_kassa_rejects_stale_revision_without_clearing_debt(self):
        self.book()
        preview = self.client.get(f"/api/kassa/person/{self.person['id']}").json()
        self.book()
        response = self.client.post(
            "/api/kassa/pay",
            json={"person_id": self.person["id"], "pin": "1234", "expected_revision": preview["revision"]},
        )
        self.assertEqual(response.status_code, 409)
        with self.legacy.get_conn() as conn:
            self.assertEqual(conn.execute("SELECT SUM(quantity) FROM order_lines").fetchone()[0], 2)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM transactions WHERE type = 'PAID_CASH'").fetchone()[0], 0
            )

    def test_http_event_correction_rejects_stale_id_and_rolls_back_audit_failure(self):
        event = self.post("/api/admin/event/start", {"pin": "1234", "name": "HTTP synthetic event"})["event"]
        payload = {"item_id": self.item["id"], "event_id": event["id"]}
        self.post("/api/event/add-drink", payload)
        stale = self.client.post("/api/event/remove-drink", json={**payload, "event_id": event["id"] + 1})
        self.assertEqual(stale.status_code, 400)
        with patch.object(self.legacy, "log_transaction", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaisesRegex(RuntimeError, "audit unavailable"):
                self.client.post("/api/event/remove-drink", json=payload)
        self.assertEqual(self.client.get("/api/event/active").json()["event"]["quantity"], 1)
        self.post("/api/event/remove-drink", payload)
        self.assertEqual(self.client.get("/api/event/active").json()["event"]["quantity"], 0)
        with self.legacy.get_conn() as conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM transactions WHERE type = 'EVENT_ITEM_REMOVED'").fetchone()[0], 1
            )
