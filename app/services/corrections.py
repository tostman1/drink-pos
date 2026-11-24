"""Append-only ordinary correction provenance and committed operation receipts.

Caller owns BEGIN IMMEDIATE/commit. No nested transaction, historical reconstruction,
current-price lookup, refund, round cancellation or external effects here.
"""

import json

from fastapi import HTTPException

try:
    from app.services.statistics import log_transaction_item
    from app.utils.helpers import now_text
except ImportError:
    from services.statistics import log_transaction_item
    from utils.helpers import now_text


def canonical(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def operation_id(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise HTTPException(
            400, "Korrektur-ID erforderlich (maximal 128 Zeichen); dieselbe ID bei Wiederholung verwenden."
        )
    return value.strip()


def replay(conn, identity, endpoint, payload):
    identity = operation_id(identity)
    row = conn.execute("SELECT * FROM operation_receipts WHERE operation_id=?", (identity,)).fetchone()
    if row is None:
        return None
    if row["endpoint"] != endpoint or row["payload_json"] != canonical(payload):
        raise HTTPException(409, "Diese Vorgangs-ID wurde mit anderen Angaben verwendet.")
    return json.loads(row["result_json"])


def receipt(conn, identity, endpoint, payload, result, transaction_id=None):
    conn.execute(
        "INSERT INTO operation_receipts VALUES(?,?,?,?,?,?)",
        (identity, endpoint, canonical(payload), canonical(result), transaction_id, now_text()),
    )


def intervention(message):
    raise HTTPException(409, {"status": "intervention_required", "message": message})


def guard_uncertain_payment(conn, person_id):
    if conn.execute(
        "SELECT 1 FROM self_payment_sessions WHERE person_id=? AND UPPER(status) IN ('UNKNOWN','CREATED','SENT_TO_READER','PENDING')",
        (person_id,),
    ).fetchone():
        intervention(
            "Aktive oder unklare Kartenzahlung; zuerst Zahlungsstatus gesondert abgleichen, keine Korrektur/Rückzahlung."
        )


def sources_for_correction(conn, line, quantity):
    sources = conn.execute(
        """SELECT ti.*,bs.consumed_date,
        COALESCE((SELECT -SUM(cti.quantity) FROM correction_details cd
                  JOIN transaction_items cti ON cti.id=cd.transaction_item_id
                  WHERE cd.source_transaction_item_id=ti.id),0) AS reversed_quantity
        FROM booking_sources bs JOIN transaction_items ti ON ti.id=bs.transaction_item_id
        WHERE bs.original_order_line_id=? AND ti.kind='CONSUME' AND ti.quantity>0
        ORDER BY ti.id DESC""",
        (line["id"],),
    ).fetchall()
    for source in sources:
        if (
            source["person_id"] != line["person_id"]
            or source["item_id"] != line["item_id"]
            or source["consumed_date"] != line["consumed_date"]
        ):
            intervention("Buchungsquelle widerspricht dem ursprünglichen Posten; keine automatische Korrektur")
    # Mixing tracked and old untracked quantity would imply invented attribution.
    tracked = sum(int(r["quantity"]) - int(r["reversed_quantity"]) for r in sources)
    if tracked < int(line["quantity"]):
        intervention(
            "Historische Buchungszuordnung fehlt; keine automatische Verbrauchskorrektur. Admin-Abgleich erforderlich."
        )
    selected = []
    remaining = quantity
    for source in sources:
        available = int(source["quantity"]) - int(source["reversed_quantity"])
        take = min(remaining, available)
        if take > 0:
            selected.append((source, take))
            remaining -= take
    if remaining:
        intervention("Ursprüngliche Verbrauchsbuchung ist nicht vollständig zugeordnet.")
    return selected


def append_correction(conn, identity, line, quantity, transaction_id, *, reason, authorized_by, request_id=None):
    selected = sources_for_correction(conn, line, quantity)
    timestamp = now_text()
    for source, take in selected:
        # Use original TI snapshot, never current master or derived historical cost.
        log_transaction_item(
            conn, transaction_id, line["person_id"], source, -take, "CONSUMPTION_CORRECTION", timestamp
        )
        detail_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            """INSERT INTO correction_details(operation_id,original_order_line_id,
            source_transaction_item_id,transaction_item_id,change_request_id,purpose,reason,
            authorized_by,consumed_date,corrected_at) VALUES(?,?,?,?,?,'erroneous_booking',?,?,?,?)""",
            (
                identity,
                line["id"],
                source["id"],
                detail_id,
                request_id,
                reason or "",
                authorized_by,
                source["consumed_date"],
                timestamp,
            ),
        )


def link_booking(conn, line_id, transaction_id, kind):
    rows = conn.execute(
        "SELECT id,quantity FROM transaction_items WHERE transaction_id=? AND kind=? ORDER BY id",
        (transaction_id, kind),
    ).fetchall()
    line = conn.execute("SELECT consumed_date,item_name_snapshot FROM order_lines WHERE id=?", (line_id,)).fetchone()
    for row in rows:
        if kind == "CONSUME":
            conn.execute("INSERT INTO booking_sources VALUES(?,?,?)", (row["id"], line_id, line["consumed_date"]))
        if kind != "CONSUME" or line["item_name_snapshot"] == "1 Runde":
            start = conn.execute("SELECT MAX(id) FROM transactions WHERE type='CASHUP'").fetchone()[0]
            for unit in range(1, int(row["quantity"]) + 1):
                conn.execute(
                    "INSERT INTO round_units(original_order_line_id,booking_transaction_item_id,unit_number,event_start_transaction_id) VALUES(?,?,?,?)",
                    (line_id, row["id"], unit, start),
                )
