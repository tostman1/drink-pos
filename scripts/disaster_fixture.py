"""Synthetic-only commands executed in isolated verification image containers."""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

# This file is explicitly copied into disposable containers, not shipped in image.
sys.path.insert(0, "/app")
from application_recovery import database_metadata, file_metadata  # noqa: E402


def seed():
    import main

    pin = os.environ["DRINK_POS_PIN"]
    a = main.admin_create_person(main.AdminPersonCreate(pin=pin, first_name="Synthetic", last_name="Debtor"))
    b = main.admin_create_person(main.AdminPersonCreate(pin=pin, first_name="Synthetic", last_name="Roundpayer"))
    item = main.admin_create_drink(
        main.AdminItemCreate(pin=pin, name="Synthetic historical drink", price="2,50", purchase_price="1,40")
    )
    item_id = item.get("id") or item.get("item", {}).get("id")
    if item_id is None:
        with main.get_conn() as conn:
            item_id = conn.execute("SELECT id FROM items WHERE name='Synthetic historical drink'").fetchone()[0]
    main.add_drink(main.AddDrinkRequest(person_id=a["id"], item_id=item_id, client_operation_id="dr-offline-1"))
    main.add_drink(main.AddDrinkRequest(person_id=b["id"], item_id=item_id))
    main.create_round_request(main.RoundRequestIn(person_id=b["id"], quantity=1))
    preview = main.kassa_person(b["id"])
    main.kassa_pay(main.KassaPayRequest(pin=pin, person_id=b["id"], expected_revision=preview["revision"]))
    main.admin_cashup(main.CashupRequest(pin=pin))
    # New open debt across price changes, immutable consumption-time snapshots.
    main.add_drink(main.AddDrinkRequest(person_id=a["id"], item_id=item_id, client_operation_id="dr-offline-2"))
    main.admin_update_drink(
        main.AdminItemUpdate(
            pin=pin, item_id=item_id, name="Synthetic renamed drink", price="3,00", purchase_price="1,50"
        )
    )
    main.add_drink(main.AddDrinkRequest(person_id=a["id"], item_id=item_id, client_operation_id="dr-offline-3"))
    with main.get_conn() as conn:
        line_id = conn.execute(
            "SELECT id FROM order_lines WHERE person_id=? AND quantity>0 ORDER BY id LIMIT 1", (a["id"],)
        ).fetchone()[0]
    main.create_edit_request(
        main.EditRequestIn(person_id=a["id"], line_quantities={str(line_id): 1}, reason="synthetic correction request")
    )
    message = main.admin_create_member_message(
        main.AdminMemberMessageCreate(pin=pin, title="Synthetic", message="Disaster rehearsal", person_ids=[a["id"]])
    )
    main.admin_event_start(main.EventStartRequest(pin=pin, name="Synthetic disaster invoice"))
    main.event_add_drink(main.EventAddDrinkRequest(item_id=item_id))
    main.admin_event_end(main.EventEndRequest(pin=pin, create_invoice=True))
    # Provider correlation is synthetic local data, never a real provider call.
    with main.get_conn() as conn:
        transaction = conn.execute("SELECT id FROM transactions WHERE type='PAID_CASH' ORDER BY id LIMIT 1").fetchone()[
            0
        ]
        conn.execute(
            """INSERT INTO self_payment_sessions(person_id,client_payment_id,status,base_amount_cents,
                     card_fee_cents,rounding_mode,rounding_adjustment_cents,amount_eur,amount_cents,currency,
                     provider,provider_checkout_id,revision,terminal_reference,transaction_id,created_at,updated_at)
                     VALUES(?,'dr-paid-id','paid',250,20,'none',0,2.7,270,'EUR','sumup','synthetic-checkout-paid',
                     'synthetic-revision','synthetic-terminal',?,'2026-01-01','2026-01-01')""",
            (b["id"], transaction),
        )
        conn.execute(
            """INSERT INTO self_payment_sessions(person_id,client_payment_id,status,amount_eur,amount_cents,
                     currency,provider,provider_checkout_id,revision,created_at,updated_at)
                     VALUES(?,'dr-uncertain-id','unknown',2.7,270,'EUR','sumup','synthetic-checkout-unknown',
                     'synthetic-uncertain-revision','2026-01-01','2026-01-01')""",
            (a["id"],),
        )
        # Raise sequence beyond surviving IDs; indexes/trigger are real schema state.
        conn.execute(
            "CREATE TRIGGER dr_keep_audit BEFORE DELETE ON transactions BEGIN SELECT RAISE(ABORT,'immutable'); END"
        )
        conn.execute("CREATE INDEX dr_payment_identity ON self_payment_sessions(client_payment_id)")
        conn.execute("UPDATE sqlite_sequence SET seq=seq+100 WHERE name='transactions'")
        conn.commit()
    Path(os.environ["DRINK_POS_MESSAGES"]).write_text(
        '{"dr_synthetic":"Disaster recovery wording ä"}', encoding="utf-8"
    )
    assert main.kassa_person(a["id"])["total"] > 0
    with closing(sqlite3.connect(main.DB_PATH)) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        assert conn.execute("SELECT COUNT(*) FROM round_events").fetchone()[0] > 0
        assert conn.execute("SELECT COUNT(*) FROM paid_round_units").fetchone()[0] > 0
    print(json.dumps({"status": "synthetic-seeded", "message_created": bool(message)}))


def validate(root: Path, expected: dict):
    database = root / "state/database.db"
    metadata = database_metadata(database, original_references=expected["event_references"])
    assert metadata == expected["database"], "Complete normalized DB/sequence/schema differs"
    for name, values in expected["files"].items():
        if name != "state/database.db":
            assert file_metadata(root / name) == values, "Recovered artifact differs"
    with closing(sqlite3.connect(database)) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
        assert conn.execute("SELECT SUM(quantity*unit_price_eur) FROM order_lines WHERE quantity>0").fetchone()[0] > 0
        assert conn.execute("SELECT COUNT(*) FROM transactions WHERE type='CASHUP'").fetchone()[0] > 0
        assert conn.execute("SELECT COUNT(*) FROM round_events").fetchone()[0] > 0
        assert conn.execute("SELECT COUNT(*) FROM client_operations").fetchone()[0] >= 3
        assert (
            conn.execute(
                "SELECT status FROM self_payment_sessions WHERE client_payment_id='dr-uncertain-id'"
            ).fetchone()[0]
            == "unknown"
        )
        for csv, pdf in conn.execute("SELECT csv_path,pdf_path FROM event_sessions"):
            assert Path(csv).is_file() and Path(pdf).is_file()
        try:
            conn.execute("DELETE FROM transactions")
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Immutable audit trigger lost")
    return {"status": "complete-state-verified", "tables_verified": len(metadata["tables"]), "external_effects": "none"}


def main():
    command = sys.argv[1]
    if command == "seed":
        seed()
    elif command == "validate":
        print(json.dumps(validate(Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")))))
    elif command == "startup":
        # Explicit synthetic reconciliation gate, before any startup/import.
        expected = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
        record = json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
        assert record == {
            "scope": "synthetic-only",
            "uncertain_card": "held-no-retry",
            "post_snapshot": "held-no-replay",
            "browser_queue": "held-no-replay",
            "invoice_mail": "held-no-resend",
        }
        assert not any(
            os.getenv(key) for key in ("SUMUP_API_KEY", "SUMUP_MERCHANT_CODE", "SUMUP_READER_ID", "DRINK_POS_SMTP_HOST")
        )
        root = Path(sys.argv[2])
        validate(root, expected)
        import main as application

        # Fail if startup attempts *any* socket connection; external services absent.
        original = socket.socket.connect

        def forbidden(*args, **kwargs):
            raise AssertionError("Startup attempted a network connection")

        socket.socket.connect = forbidden
        try:
            application.startup()
        finally:
            socket.socket.connect = original
        validate(root, expected)
        assert application.health()["status"] == "ok"
        print(
            json.dumps(
                {
                    "status": "isolated-synthetic-startup-verified",
                    "network_attempts": 0,
                    "reconciliation": "synthetic-holds-only",
                }
            )
        )


if __name__ == "__main__":
    main()
