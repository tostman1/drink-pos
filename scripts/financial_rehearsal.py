"""RL-04 synthetic served financial scenario, both modes and separate recovery.

Explicit nonexistent owned target only. No live inputs, real provider/mail, queue
replay, repair or deployment. Assertions must remain enabled. Evidence retained.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from unittest.mock import patch


def run_rehearsal(target: Path, commit: str, *, synthetic_only: bool = False) -> dict:
    if sys.flags.optimize or not synthetic_only or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Synthetic opt-in, exact commit and enabled assertions required")
    if os.path.lexists(target):
        raise FileExistsError("Synthetic target already exists")
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
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise RuntimeError(f"Synthetic financial rehearsal failed; retained evidence: {result.stderr}")
    return json.loads((target / "RESULT.json").read_text(encoding="utf-8"))


def worker(target: Path, commit: str) -> dict:
    if sys.flags.optimize or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Exact commit and enabled assertions required")
    for path in (target, *target.parents):
        if os.path.lexists(path) and (path.is_symlink() or getattr(path.lstat(), "st_file_attributes", 0) & 0x400):
            raise ValueError("Synthetic roots must not use links/reparse points")
    target.mkdir(mode=0o700)
    for key in list(os.environ):
        if key.startswith(
            ("DRINK_POS_", "SUMUP_", "SMTP_", "APP_BUILD_", "PAYMENT_PROVIDER", "UVICORN_", "WEB_CONCURRENCY")
        ):
            del os.environ[key]
    os.environ.update(
        DRINK_POS_ENV="production",
        DRINK_POS_PIN="847296",
        DRINK_POS_DB=str(target / "source/source.db"),
        DRINK_POS_MESSAGES=str(target / "source/messages.json"),
    )
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "app"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import main
    from application_recovery import create_backup, verify_application_bundle, restore_application, database_metadata
    from db.migrations import inspect
    from disaster_fixture import seed

    runner = asyncio.Runner()
    runner.get_loop()  # Windows self-pipe infrastructure, before application guard.
    network_attempts = []

    def forbidden(*args, **kwargs):
        network_attempts.append(1)
        raise AssertionError("Synthetic financial scenario attempted network")

    async def request(path, payload=None, expected=200):
        messages = []
        body = json.dumps(payload).encode() if payload is not None else b""

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await main.app(
            {
                "type": "http",
                "asgi": {"version": "3.0"},
                "http_version": "1.1",
                "method": "POST" if payload is not None else "GET",
                "scheme": "http",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "root_path": "",
                "headers": [(b"content-type", b"application/json")],
                "server": ("synthetic.invalid", 80),
                "client": ("127.0.0.1", 1),
            },
            receive,
            send,
        )
        data = json.loads(b"".join(m.get("body", b"") for m in messages))
        assert messages[0]["status"] == expected, (path, data)
        return data

    def api(path, payload=None, expected=200):
        return runner.run(request(path, payload, expected))

    def state():
        with closing(sqlite3.connect(main.DB_PATH)) as conn:
            names = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            return {name: sorted(conn.execute(f'SELECT * FROM "{name}"').fetchall(), key=repr) for name in names}

    def assert_old_snapshots(before, after):
        for table in (
            "transactions",
            "transaction_items",
            "round_events",
            "event_sessions",
            "event_lines",
            "client_operations",
            "self_payment_sessions",
        ):
            old = {r[0]: r for r in before[table]}
            new = {r[0]: r for r in after[table]}
            assert all(new[key] == row for key, row in old.items()), table
        # Remaining quantity/tally/update time may change, original facts may not.
        for old in before["order_lines"]:
            new = next(r for r in after["order_lines"] if r[0] == old[0])
            assert all(new[i] == old[i] for i in range(len(old)) if i not in (3, 10, 12)), "order snapshots"
        for old in before["paid_round_units"]:
            new = next(r for r in after["paid_round_units"] if r[0] == old[0])
            assert all(new[i] == old[i] for i in range(len(old)) if i not in (6, 8)), "paid round snapshots"

    with (
        patch.object(socket.socket, "connect", forbidden),
        patch.object(main.event_service, "send_smtp_message", side_effect=AssertionError("No SMTP authorized")),
    ):
        main.startup()
        seed()  # Several members, priced history, paid rounds/deductions/cashup,
        # idempotency, named invoice+CSV/PDF, messages, provider IDs and sequence gap.
        pin = os.environ["DRINK_POS_PIN"]
        cash_person, card_person, unknown_person = [
            api("/api/admin/people/create", {"pin": pin, "first_name": "RL04", "last_name": name})["id"]
            for name in ("Cash", "Card", "Unknown")
        ]
        api(
            "/api/admin/drinks/create",
            {"pin": pin, "name": "Synthetic zero cost", "short_label": "Zero", "price": 3, "purchase_price": 0},
        )
        with main.get_conn() as conn:
            item_id = conn.execute("SELECT id FROM items WHERE name='Synthetic zero cost'").fetchone()[0]

        def book(person, operation):
            return api("/api/add-drink", {"person_id": person, "item_id": item_id, "client_operation_id": operation})

        for person in (cash_person, card_person, unknown_person):
            book(person, f"rl04-initial-{person}")
        api("/api/pay", {"pin": pin, "person_id": cash_person})
        book(cash_person, "rl04-second")
        with main.get_conn() as conn:
            # Synthetic signed and unusual round originals are not new refund rules.
            round_line = dict(
                conn.execute("SELECT * FROM order_lines WHERE item_name_snapshot='1 Runde' LIMIT 1").fetchone()
            )
            conn.execute("UPDATE order_lines SET unit_purchase_price_eur=4 WHERE id=?", (round_line["id"],))
            tx = main.log_transaction(conn, cash_person, "SYNTHETIC_SIGNED", -3, "not a refund")
            main.log_transaction_item(
                conn,
                tx,
                cash_person,
                {
                    "item_id": item_id,
                    "item_name_snapshot": "Synthetic zero cost",
                    "item_short_label_snapshot": "Zero",
                    "unit_price_eur": 3,
                    "unit_purchase_price_eur": 0,
                },
                -1,
                "SYNTHETIC_SIGNED",
            )
            conn.execute("UPDATE transaction_items SET profit_eur=0 WHERE kind='PAID_CASH' AND item_id=?", (item_id,))
            conn.commit()
        original = state()
        for cost in (1.25, 1.25, 2):
            before = state()
            api(
                "/api/admin/drinks/update",
                {
                    "pin": pin,
                    "item_id": item_id,
                    "name": "Synthetic zero cost",
                    "short_label": "Zero",
                    "price": 4,
                    "purchase_price": cost,
                },
            )
            after = state()
            for table in before.keys() - {"items", "transactions", "sqlite_sequence"}:
                assert after[table] == before[table], table
            assert {r[0]: r for r in after["transactions"]}.items() >= {r[0]: r for r in before["transactions"]}.items()
        before = state()
        for _ in range(3):
            main.startup()
            assert state() == before
        book(cash_person, "rl04-new-current")
        with main.get_conn() as conn:
            assert tuple(
                conn.execute(
                    "SELECT unit_price_eur,unit_purchase_price_eur FROM order_lines WHERE person_id=? ORDER BY id DESC LIMIT 1",
                    (cash_person,),
                ).fetchone()
            ) == (4, 2)
            line_id = conn.execute(
                "SELECT id FROM order_lines WHERE person_id=? AND quantity>0 ORDER BY id DESC LIMIT 1", (cash_person,)
            ).fetchone()[0]
        api("/api/edit-request", {"person_id": cash_person, "line_quantities": {str(line_id): 1}})
        api("/api/pay", {"pin": pin, "person_id": cash_person, "approve_pending": True})
        book(cash_person, "rl04-admin-correction")
        api("/api/admin/adjust-drink", {"pin": pin, "person_id": cash_person, "item_id": item_id, "delta": -1})
        # Mock provider boundary, including matching cents/currency and replay.
        os.environ.update(
            PAYMENT_PROVIDER="sumup",
            SUMUP_API_BASE="https://synthetic.invalid",
            SUMUP_API_KEY="synthetic-not-a-secret",
            SUMUP_MERCHANT_CODE="synthetic",
            SUMUP_READER_ID="synthetic",
        )
        calls = []

        def checkout(cfg, amount_cents, receipt_text="", foreign_transaction_id=None):
            calls.append(amount_cents)
            return {"status": "sent_to_reader", "provider_checkout_id": "rl04-mocked-checkout"}

        def paid(cfg, checkout_id):
            return {
                "status": "paid",
                "provider_checkout_id": checkout_id,
                "transaction_id": "rl04-mocked-provider",
                "amount_cents": calls[-1],
                "currency": "EUR",
                "raw_response": {"synthetic": True},
            }

        preview = api(f"/api/self-pay/person/{card_person}")
        card_payload = {
            "person_id": card_person,
            "expected_revision": preview["revision"],
            "client_payment_id": "rl04-card",
            "rounding_mode": "none",
        }
        with patch.object(main, "create_sumup_checkout", checkout), patch.object(main, "poll_sumup_payment", paid):
            assert api("/api/self-pay/pay", card_payload)["status"] == "paid"
            assert api("/api/self-pay/pay", card_payload)["duplicate"]
        assert len(calls) == 1
        unknown_preview = api(f"/api/self-pay/person/{unknown_person}")
        unknown_payload = {
            "person_id": unknown_person,
            "expected_revision": unknown_preview["revision"],
            "client_payment_id": "rl04-unknown",
        }
        with (
            patch.object(main, "create_sumup_checkout", checkout),
            patch.object(
                main, "poll_sumup_payment", return_value={"status": "unknown", "error": "synthetic uncertainty"}
            ),
        ):
            assert api("/api/self-pay/pay", unknown_payload)["status"] == "unknown"
            assert api("/api/self-pay/pay", unknown_payload)["duplicate"]
        assert len(calls) == 2
        assert api(f"/api/kassa/person/{unknown_person}")["total"] == 3
        api("/api/admin/cashup", {"pin": pin})
        assert_old_snapshots(original, state())
        # Independently prepared exact-current copy: fixture-only objects removed
        # only in an explicitly synthetic source, never for real adoption support.
        with main.get_conn() as conn:
            conn.execute("DROP TRIGGER dr_keep_audit")
            conn.execute("DROP INDEX dr_payment_identity")
            conn.execute("UPDATE items SET active=0,archived_at='synthetic' WHERE name='Synthetic renamed drink'")
            conn.execute("UPDATE people SET active=0,archived_at='synthetic' WHERE id=?", (cash_person,))
            conn.commit()
        source = Path(main.DB_PATH)
        bundle = create_backup(
            source,
            Path(os.environ["DRINK_POS_MESSAGES"]),
            target / "backups",
            deployment_id="rl04-synthetic",
            app_commit=commit,
            quiesced=True,
        )
        manifest = verify_application_bundle(bundle)
        adopted = restore_application(
            bundle, target / "adopted", expected_commit=commit, expected_schema=manifest["database"]["schema_sha256"]
        )
        main.DB_PATH = str(adopted / "state/database.db")
        os.environ["DRINK_POS_MESSAGES"] = str(adopted / "state/messages.json")
        before = state()
        os.environ.update(DRINK_POS_MIGRATION_MODE="versioned", DRINK_POS_ADOPT_LEGACY="1")
        main.startup()
        assert inspect(Path(main.DB_PATH))["state"] == "versioned-current"
        after = state()
        for table in before:
            assert after[table] == before[table], table
        for _ in range(3):
            main.startup()
            assert state() == after
        api(
            "/api/admin/drinks/update",
            {
                "pin": pin,
                "item_id": item_id,
                "name": "Synthetic zero cost",
                "short_label": "Zero",
                "price": 4,
                "purchase_price": 3,
            },
        )
        assert_old_snapshots(after, state())
        book(card_person, "rl04-versioned-current")
        with main.get_conn() as conn:
            assert (
                conn.execute(
                    "SELECT unit_purchase_price_eur FROM order_lines WHERE person_id=? AND quantity>0 ORDER BY id DESC LIMIT 1",
                    (card_person,),
                ).fetchone()[0]
                == 3
            )
        versioned_before_payment = state()
        api("/api/pay", {"pin": pin, "person_id": card_person})
        api("/api/admin/cashup", {"pin": pin})
        assert_old_snapshots(versioned_before_payment, state())
        # Paid zero is intentionally not positive sales, unlike consumption/round
        # formulas. Scope to a synthetic paid-only item using item grouping.
        report = api("/api/admin/report/preview", {"pin": pin, "report_type": "revenue", "group_by": "item"})
        zero_row = next(r for r in report["rows"] if r[0] == "Synthetic zero cost")
        assert zero_row[-1] == "7,00"  # first cash 0 + remaining cash/card 3 each + strict new 1.
        with main.get_conn() as conn:
            stored = conn.execute(
                "SELECT SUM(profit_eur) FROM transaction_items WHERE item_id=? AND kind IN ('PAID_CASH','PAID_SUMUP')",
                (item_id,),
            ).fetchone()[0]
            assert zero_row[-1] == main.decimal_comma(stored)
        recovered = restore_application(
            bundle,
            target / "independent-recovery",
            expected_commit=commit,
            expected_schema=manifest["database"]["schema_sha256"],
        )
        assert (
            database_metadata(
                recovered / "state/database.db", immutable=True, original_references=manifest["event_references"]
            )
            == manifest["database"]
        )
        with main.get_conn() as conn:
            assert conn.execute("PRAGMA integrity_check").fetchall()[0][0] == "ok"
            assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        assert not network_attempts
    runner.close()
    result = {
        "status": "synthetic-financial-integrity-verified",
        "commit": commit,
        "original_tables_preserved": len(before),
        "history_rewritten": False,
        "legacy_repeat_verified": True,
        "versioned_adoption_verified": True,
        "recovery_verified": True,
        "network_attempts": len(network_attempts),
        "mocked_card_creations": len(calls),
        "production_authorized": False,
        "historical_release_evidence": "none; synthetic current state only",
    }
    (target / "RESULT.json").write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if not args.synthetic_only:
        parser.error("Synthetic-only opt-in required")
    result = (
        worker(args.target.absolute(), args.commit)
        if args.worker
        else run_rehearsal(args.target, args.commit, synthetic_only=True)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
