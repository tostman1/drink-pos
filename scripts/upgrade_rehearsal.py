"""Opt-in synthetic upgrade rehearsal; never accepts existing installation state.

Requires an explicitly nonexistent target and exact candidate commit. Starts only
synthetic copies with provider configuration cleared and socket connections blocked.
Retains evidence/failed disposable state; no cleanup, image pulls or publication.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path


def run_rehearsal(target: Path, commit: str, *, synthetic_only: bool = False) -> dict:
    if sys.flags.optimize or not synthetic_only or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Synthetic-only opt-in and exact commit required")
    if os.path.lexists(target):
        raise FileExistsError("Rehearsal target already exists")
    environment = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(
            ("DRINK_POS_", "SUMUP_", "SMTP_", "APP_BUILD_", "PAYMENT_PROVIDER", "UVICORN_", "WEB_CONCURRENCY")
        )
    }
    environment.update(
        DRINK_POS_ENV="production",
        DRINK_POS_PIN="847296",
        DRINK_POS_DB=str(target.absolute() / "source/source.db"),
        DRINK_POS_MESSAGES=str(target.absolute() / "source/messages.json"),
        PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(Path(__file__).resolve()),
            "--target",
            str(target.absolute()),
            "--commit",
            commit,
            "--synthetic-only",
            "--worker",
        ],
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError("Synthetic rehearsal failed; inspect retained isolated state")
    return json.loads((target / "RESULT.json").read_text(encoding="utf-8"))


def worker(target: Path, commit: str) -> dict:
    if sys.flags.optimize:
        raise ValueError("Rehearsal assertions must not be disabled")
    for path in (target, *target.parents):
        if os.path.lexists(path) and (path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Rehearsal roots must not use symlinks/reparse points")
    # Also enforce isolation in internal-worker mode; never trust inherited paths
    # or credentials even if a caller bypasses the parent command.
    for key in list(os.environ):
        if key.startswith(
            ("DRINK_POS_", "SUMUP_", "SMTP_", "APP_BUILD_", "PAYMENT_PROVIDER", "UVICORN_", "WEB_CONCURRENCY")
        ):
            del os.environ[key]
    os.environ.update(
        DRINK_POS_ENV="production",
        DRINK_POS_PIN="847296",
        DRINK_POS_DB=str(target.absolute() / "source/source.db"),
        DRINK_POS_MESSAGES=str(target.absolute() / "source/messages.json"),
    )
    # Exclusive creation protects existing targets even if another process races.
    target.mkdir(mode=0o700)
    (target / "source").mkdir(mode=0o700)
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "app"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from application_recovery import (
        database_metadata,
        create_backup,
        restore_application,
        verify_application_bundle,
        digest_json,
    )
    from release_identity import release_identity
    from upgrade_preflight import evaluate
    from disaster_fixture import seed
    import main

    # Windows event-loop self-pipe uses a loopback socketpair. Initialize only
    # that infrastructure before the application network prohibition is installed.
    runner = asyncio.Runner()
    runner.get_loop()

    attempts = []

    def forbidden(*args, **kwargs):
        attempts.append(1)
        raise AssertionError("Synthetic rehearsal attempted network access")

    socket.socket.connect = forbidden
    main.startup()
    seed()
    source = Path(main.DB_PATH)
    # Explicitly synthetic pre-cost snapshot state; NOT an authentic old release.
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("UPDATE order_lines SET unit_purchase_price_eur=0 WHERE item_name_snapshot!='1 Runde'")
        conn.execute(
            "UPDATE transaction_items SET unit_purchase_price_eur=0,purchase_total_eur=0,profit_eur=total_eur WHERE item_name_snapshot!='1 Runde'"
        )
        conn.commit()

    async def api_state():
        async def get(path):
            sent = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                sent.append(message)

            await main.app(
                {
                    "type": "http",
                    "asgi": {"version": "3.0"},
                    "http_version": "1.1",
                    "method": "GET",
                    "scheme": "http",
                    "path": path,
                    "raw_path": path.encode(),
                    "query_string": b"",
                    "root_path": "",
                    "headers": [],
                    "server": ("synthetic.invalid", 80),
                    "client": ("127.0.0.1", 1),
                },
                receive,
                send,
            )
            assert sent[0]["status"] == 200
            return json.loads(b"".join(message.get("body", b"") for message in sent))

        await get("/api/kassa/people")
        with main.get_conn() as conn:
            ids = [row[0] for row in conn.execute("SELECT id FROM people ORDER BY id")]
        totals = [(person, (await get(f"/api/kassa/person/{person}"))["total"]) for person in ids]
        event = await get("/api/event/active")
        assert (await get("/health"))["status"] == "ok"
        return {"debt_totals": totals, "active_event": event}

    before_api = runner.run(api_state())
    identity = release_identity(commit, "verification", "synthetic")
    bundle = create_backup(
        source,
        Path(os.environ["DRINK_POS_MESSAGES"]),
        target / "backups",
        deployment_id="rl01-synthetic",
        app_commit=commit,
        quiesced=True,
        configuration={"DRINK_POS_ENV": "production", "SUMUP_CURRENCY": "EUR"},
    )
    manifest = verify_application_bundle(bundle)
    permitted = ["zero non-round purchase snapshots use current synthetic item cost; cost/profit recomputed"]
    evidence = {
        "format": "drink-pos-upgrade-evidence",
        "format_version": 1,
        "deployment_id": "rl01-synthetic",
        "current_identity_sha256": digest_json(identity),
        "candidate_identity_sha256": digest_json(identity),
        "source_schema_sha256": manifest["database"]["schema_sha256"],
        "target_schema_sha256": manifest["database"]["schema_sha256"],
        "supported": True,
        "approved_by": "synthetic-fixture-contract",
        "permitted_changes": permitted,
        "candidate_configuration": {"DRINK_POS_ENV": "production", "SUMUP_CURRENCY": "EUR"},
        "target_python": f"{sys.version_info.major}.{sys.version_info.minor}",
        "secrets_recovery_verified": True,
        "encryption_required": False,
    }
    preflight = evaluate(
        bundle=bundle,
        current=identity,
        candidate=identity,
        evidence=evidence,
        isolated_copy=True,
        mode="local",
        max_backup_age_seconds=3600,
    )
    assert preflight["exit_code"] == 0
    (target / "PREFLIGHT.json").write_text(json.dumps(preflight, sort_keys=True), encoding="utf-8")
    rehearsal = restore_application(
        bundle, target / "candidate", expected_commit=commit, expected_schema=manifest["database"]["schema_sha256"]
    )
    database = rehearsal / "state/database.db"
    expected = target / "expected.db"
    shutil.copyfile(database, expected)
    # Construct explicit expected changes independently, not by invoking migrations.
    with closing(sqlite3.connect(expected)) as conn:
        conn.execute(
            "UPDATE order_lines SET unit_purchase_price_eur=(SELECT purchase_price_eur FROM items WHERE id=order_lines.item_id) WHERE unit_purchase_price_eur=0 AND item_name_snapshot!='1 Runde'"
        )
        conn.execute(
            "UPDATE transaction_items SET unit_purchase_price_eur=(SELECT purchase_price_eur FROM items WHERE id=transaction_items.item_id), purchase_total_eur=quantity*(SELECT purchase_price_eur FROM items WHERE id=transaction_items.item_id), profit_eur=total_eur-quantity*(SELECT purchase_price_eur FROM items WHERE id=transaction_items.item_id) WHERE unit_purchase_price_eur=0 AND item_name_snapshot!='1 Runde'"
        )
        conn.commit()
    main.DB_PATH = str(database)
    os.environ["DRINK_POS_MESSAGES"] = str(rehearsal / "state/messages.json")
    # Actual served lifecycle path, no listening server or external credentials.
    for handler in main.app.router.on_startup:
        handler()
    assert runner.run(api_state()) == before_api
    actual = database_metadata(database)
    assert actual == database_metadata(expected, immutable=True), "Unexpected financial/operational/schema changes"
    assert actual["schema_sha256"] == manifest["database"]["schema_sha256"]
    main.startup()
    assert database_metadata(database) == actual, "Second startup not logically idempotent for this fixture"
    for name, metadata in manifest["files"].items():
        if name != "state/database.db":
            from database_recovery import file_metadata

            assert file_metadata(rehearsal / name) == metadata
    recovered = restore_application(
        bundle,
        target / "separate-recovery",
        expected_commit=commit,
        expected_schema=manifest["database"]["schema_sha256"],
    )
    assert (
        database_metadata(
            recovered / "state/database.db", immutable=True, original_references=manifest["event_references"]
        )
        == manifest["database"]
    )
    with closing(sqlite3.connect(database)) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert (
            conn.execute(
                "SELECT status FROM self_payment_sessions WHERE client_payment_id='dr-uncertain-id'"
            ).fetchone()[0]
            == "unknown"
        )
    assert not attempts
    runner.close()
    return {
        "status": "synthetic-upgrade-verified",
        "commit": commit,
        "schema_sha256": actual["schema_sha256"],
        "tables_verified": len(actual["tables"]),
        "permitted_changes": permitted,
        "recovery_verified": True,
        "network_attempts": len(attempts),
        "historical_release_evidence": "none; synthetic fixture only",
        "production_authorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if not args.synthetic_only or not re.fullmatch(r"[0-9a-f]{40}", args.commit):
            raise ValueError("Explicit synthetic opt-in required")
        result = (
            worker(args.target, args.commit)
            if args.worker
            else run_rehearsal(args.target, args.commit, synthetic_only=True)
        )
        if args.worker:
            (args.target / "RESULT.json").write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, AssertionError, RuntimeError, sqlite3.Error):
        # Do not hide failures or replace another invocation's result.
        print(json.dumps({"status": "synthetic-rehearsal-failed", "production_authorized": False}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
