"""DP-024 reuse actual served financial regressions under opt-in fresh startup."""

import os
import unittest
from contextlib import ExitStack
from unittest.mock import patch
import tempfile
from pathlib import Path

import test_backend as backend


class VersionedRuntimeTests(unittest.TestCase):
    def check_contract(self, name):
        case = backend.BackendFlowTests(name)
        with patch.dict(os.environ, {"DRINK_POS_MIGRATION_MODE": "versioned", "DRINK_POS_ALLOW_FRESH": "1"}):
            result = unittest.TestResult()
            case.run(result)
        self.assertEqual(result.errors + result.failures, [], result.errors + result.failures)
        self.assertEqual(result.testsRun, 1)

    def test_booking_and_offline_idempotency(self):
        self.check_contract("test_offline_client_operation_is_idempotent")

    def test_round_cashup_and_debt(self):
        self.check_contract("test_round_and_cashup_flow")

    def test_event_audit_and_invoice(self):
        self.check_contract("test_event_mode_start_add_discount_csv_pdf_and_close")

    def test_event_correction_rollback(self):
        self.check_contract("test_event_mark_changes_roll_back_when_audit_log_fails")

    def test_unknown_payment_is_not_success(self):
        # Selected from existing served tests, never a provider network call.
        self.check_contract("test_sumup_timeout_or_unknown_keeps_open_lines")

    def test_served_asgi_restart_cashup_and_payment_parity(self):
        from fastapi.testclient import TestClient
        from scripts.standard_checks import test_environment
        from app import application
        from app.db import schema

        with ExitStack() as stack:
            directory = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            env = test_environment(directory)
            env.update(DRINK_POS_MIGRATION_MODE="versioned", DRINK_POS_ALLOW_FRESH="1")
            stack.enter_context(patch.dict(os.environ, env, clear=True))
            stack.callback(
                schema.configure_runtime, schema.DB_PATH, schema.ENV_PIN_CODE, schema.ENV_PIN_FROM_ENV, schema.get_conn
            )
            app, legacy = application.create_app("app")
            with TestClient(app) as client:
                person = client.get("/api/people").json()[0]
                item = client.get("/api/config").json()["user_items"][0]
                for path in ("/health", "/", "/admin", "/kassa", "/self-pay", "/service-worker.js", "/openapi.json"):
                    self.assertEqual(client.get(path).status_code, 200)
                booking = client.post(
                    "/api/add-drink",
                    json={"person_id": person["id"], "item_id": item["id"], "client_operation_id": "versioned-http"},
                )
                self.assertEqual(booking.status_code, 200)
                self.assertEqual(client.post("/api/admin/cashup", json={"pin": "1234"}).status_code, 200)
                preview = client.get(f"/api/kassa/person/{person['id']}").json()
                self.assertEqual(preview["total"], item["price"])
            # Actual copied startup handlers run again, debt and replay preserved.
            with TestClient(app) as client:
                self.assertEqual(client.get(f"/api/kassa/person/{person['id']}").json(), preview)
                self.assertEqual(
                    client.post(
                        "/api/kassa/pay",
                        json={"pin": "1234", "person_id": person["id"], "expected_revision": preview["revision"]},
                    ).status_code,
                    200,
                )
                self.assertEqual(client.get(f"/api/kassa/person/{person['id']}").json()["lines"], [])
                with legacy.get_conn() as conn:
                    self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
                    self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
