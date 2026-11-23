"""Smoke-test a local image using only owned disposable Docker resources."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], text=True, capture_output=True, check=True).stdout.strip()


def container_base(identity: str) -> str:
    # Docker may reassign a dynamically allocated host port on restart.
    port = docker("port", identity, "8000/tcp").splitlines()[0].rsplit(":", 1)[1]
    return "http://127.0.0.1:" + port


def request(base: str, path: str, payload: dict | None = None) -> bytes:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"})
    # Never route disposable localhost traffic through inherited proxy settings.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=5) as response:
        if response.status != 200:
            raise AssertionError(f"Unexpected HTTP status for {path}: {response.status}")
        return response.read()


def wait_ready(base: str) -> dict:
    deadline = time.monotonic() + 60
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            return json.loads(request(base, "/health"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"Disposable container failed readiness: {last_error}")


def verify(image: str, expected_commit: str | None) -> None:
    identity = "drink-pos-check-" + uuid.uuid4().hex[:12]
    volume = identity + "-data"
    pin = "847296"  # synthetic, never a production credential
    volume_created = False
    container_created = False
    try:
        docker("volume", "create", volume)
        volume_created = True
        docker(
            "run",
            "--detach",
            "--name",
            identity,
            "--pull=never",
            "--publish",
            "127.0.0.1::8000",
            "--mount",
            f"type=volume,source={volume},target=/app/data",
            "--env",
            "DRINK_POS_ENV=production",
            "--env",
            f"DRINK_POS_PIN={pin}",
            "--env",
            "DRINK_POS_DB=/app/data/verification.db",
            "--env",
            "DRINK_POS_MESSAGES=/app/data/messages.json",
            "--env",
            "PAYMENT_PROVIDER=",
            "--env",
            "DRINK_POS_AGENT_TOKEN=",
            image,
        )
        container_created = True
        base = container_base(identity)
        health = wait_ready(base)
        assert health["status"] == "ok" and health["environment"] == "production", health
        assert health["database"]["path"] == "hidden", health
        for path in (
            "/",
            "/admin",
            "/kassa",
            "/self-pay",
            "/service-worker.js",
            "/manifest.webmanifest",
            "/kassa.webmanifest",
            "/self-pay.webmanifest",
            "/icon-192.png",
        ):
            assert request(base, path), path
        config = json.loads(request(base, "/api/config"))
        if expected_commit:
            assert config["build"]["commit"] == expected_commit, config["build"]
            assert config["build"]["channel"] == "verification", config["build"]
        paths = json.loads(request(base, "/openapi.json"))["paths"]
        assert "/api/event/add-drink" in paths and "/api/self-pay/pay" in paths, paths
        person = json.loads(
            request(
                base,
                "/api/admin/people/create",
                {
                    "pin": pin,
                    "first_name": "Container",
                    "last_name": "Verification",
                },
            )
        )
        item = config["user_items"][0]
        booking = json.loads(request(base, "/api/add-drink", {"person_id": person["id"], "item_id": item["id"]}))
        assert booking["status"] == "ok", booking
        before = json.loads(request(base, f"/api/kassa/person/{person['id']}"))
        assert before["total"] == item["price"] and before["lines"], before
        docker("restart", identity)
        base = container_base(identity)
        wait_ready(base)
        after = json.loads(request(base, f"/api/kassa/person/{person['id']}"))
        assert after["total"] == before["total"] and after["revision"] == before["revision"], after
        db_check = (
            "import main; "
            "conn = main.configure_connection(__import__('sqlite3').connect(main.DB_PATH)); "
            "assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'; "
            "assert conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1; "
            "assert conn.execute('PRAGMA journal_mode').fetchone()[0] == 'wal'; "
            "assert conn.execute('PRAGMA busy_timeout').fetchone()[0] == 15000; "
            "assert not conn.execute('PRAGMA foreign_key_check').fetchall(); "
            "assert __import__('pathlib').Path('/app/data/messages.json').is_file(); "
            "conn.close()"
        )
        docker("exec", identity, "python", "-c", db_check)
        recovery_check = (
            "from pathlib import Path; import sqlite3; "
            "from backup_database import export_backup; "
            "from restore_database import restore_backup; "
            "from database_recovery import verify_database; "
            "csv = export_backup(); "
            "target = Path('/app/data/synthetic-recovered.db'); "
            "restore_backup(csv.parent, target); "
            "assert verify_database(target) == verify_database(Path('/app/data/verification.db')); "
            "source = sqlite3.connect('/app/data/verification.db'); "
            "recovered = sqlite3.connect(target); "
            "assert list(source.iterdump()) == list(recovered.iterdump()); "
            "source.close(); recovered.close(); "
            "print('Image backup/new-target restore/table-schema comparison passed')"
        )
        docker("exec", identity, "python", "-c", recovery_check)
        image_info = json.loads(docker("image", "inspect", image))[0]
        assert image_info["Config"]["Healthcheck"]["Test"], "Dockerfile healthcheck missing"
        # Execute the declared healthcheck, not just a hand-rolled different probe.
        healthcheck = image_info["Config"]["Healthcheck"]["Test"]
        assert healthcheck[0] == "CMD-SHELL", healthcheck
        docker("exec", identity, "sh", "-c", healthcheck[1])
        print(
            "Container verification passed: startup/routes/metadata/SQLite/recovery/restart/healthcheck; no publication."
        )
    except Exception:
        if container_created:
            print(docker("logs", identity))
        raise
    finally:
        # Only names generated by this invocation; never prune or remove user data.
        if container_created:
            docker("rm", "--force", identity)
        if volume_created:
            docker("volume", "rm", volume)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="drink-pos:verification")
    parser.add_argument("--expected-commit")
    args = parser.parse_args()
    verify(args.image, args.expected_commit)


if __name__ == "__main__":
    main()
