"""Run focused Chromium smoke checks against a disposable loopback-only app."""

from __future__ import annotations

import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def verify() -> None:
    with tempfile.TemporaryDirectory(prefix="drink-pos-browser-") as directory:
        sys.path.insert(0, str(ROOT))
        from scripts.standard_checks import test_environment

        environment = test_environment(Path(directory))
        environment["DRINK_POS_PIN"] = "847296"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        # Drain a pipe rather than an inherited log file handle. Windows subprocess
        # descendants can otherwise retain that file past TemporaryDirectory cleanup.
        lines: list[str] = []
        with subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--workers",
                "1",
            ],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        ) as server:
            assert server.stdout is not None
            reader = threading.Thread(target=lambda: lines.extend(server.stdout), daemon=True)
            reader.start()
            try:
                deadline = time.monotonic() + 30
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
                while True:
                    if server.poll() is not None:
                        raise RuntimeError("Disposable browser server exited")
                    try:
                        with opener.open(base + "/health", timeout=1) as response:
                            assert response.status == 200
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("Disposable browser server did not become ready")
                        time.sleep(0.2)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    try:
                        context = browser.new_context(viewport={"width": 1024, "height": 768}, service_workers="block")
                        errors: list[str] = []
                        page = context.new_page()
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        context.route(
                            "**/*",
                            lambda route: route.continue_()
                            if route.request.url.startswith(base + "/")
                            else route.abort(),
                        )
                        page.goto(base)
                        expect(page.locator(".person-row").first).to_be_visible()
                        page.locator(".person-row").first.click()
                        expect(page.locator("#personDialog")).to_be_visible()
                        with page.expect_response(
                            lambda response: response.url.endswith("/api/add-drink") and response.status == 200
                        ):
                            page.locator("#drinkButtons button").first.click()
                        page.locator(".finish-button").click()
                        expect(page.locator("#personDialog")).not_to_be_visible()
                        # RL-05 first-party negative correction carries a durable
                        # action ID/purpose; replay through served API changes no debt.
                        page.on("dialog", lambda dialog: dialog.accept("847296"))
                        page.locator("#adminButton").click()
                        page.locator(".person-row").first.click()
                        expect(page.locator("#adminAdjustBox")).to_be_visible()
                        with page.expect_response(
                            lambda response: response.url.endswith("/api/admin/adjust-drink") and response.status == 200
                        ) as correction_response:
                            page.locator("#adminAdjustBox button.danger:enabled").first.click()
                        response = correction_response.value
                        payload = response.request.post_data_json
                        assert (
                            payload["correction_operation_id"] and payload["correction_purpose"] == "erroneous_booking"
                        )
                        original_result = response.json()
                        replay = context.request.post(base + "/api/admin/adjust-drink", data=payload)
                        assert replay.status == 200 and replay.json() == original_result
                        page.locator(".finish-button").click()
                        page.evaluate("sessionStorage.removeItem('drinkPosAdminPin')")
                        page.goto(base + "/admin")
                        page.locator("#pinInput").fill("847296")
                        page.get_by_role("button", name="Einloggen", exact=True).click()
                        expect(page.locator("#adminContent")).to_be_visible()
                        expect(page.locator("#loginCard")).not_to_be_visible()
                        api = context.request
                        started = api.post(
                            base + "/api/admin/event/start", data={"pin": "847296", "name": "Browser synthetic event"}
                        )
                        assert started.status == 200, started.text()
                        page.goto(base)
                        expect(page.locator("#eventModeView")).to_be_visible()
                        with page.expect_response(
                            lambda response: response.url.endswith("/api/event/add-drink") and response.status == 200
                        ):
                            page.locator(".event-add-button").first.click()
                        expect(page.locator(".event-remove-button").first).to_be_enabled()
                        with page.expect_response(
                            lambda response: response.url.endswith("/api/event/remove-drink") and response.status == 200
                        ):
                            page.locator(".event-remove-button").first.click()
                        expect(page.locator(".event-remove-button").first).to_be_disabled()
                        closed = api.post(base + "/api/admin/event/end", data={"pin": "847296"})
                        assert closed.status == 200, closed.text()
                        for path in ("/kassa", "/self-pay"):
                            response = page.goto(base + path)
                            assert response and response.status == 200
                            expect(page.locator("body")).to_be_visible()
                        assert not errors, errors
                        context.close()
                    finally:
                        browser.close()
                print(
                    "Browser smoke passed: Chromium/member booking/keyed correction replay/admin/event +1/-1/kassa/self-pay, no page errors."
                )
            except Exception:
                print("".join(lines))
                raise
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
                reader.join(timeout=5)


if __name__ == "__main__":
    verify()
