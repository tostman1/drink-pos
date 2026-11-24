"""Read-time correction coverage, not historical reconstruction or authorization.

A parent audit is verified only by a complete committed, source-linked operation.
Free text, current balances/prices, a matching name or one partial detail are not
evidence. No writes, no replacement of recorded financial fields. This is report
coverage of stored relationships, not authentication of external historical facts.
"""

import json
from datetime import datetime


def row(conn, table, identity):
    if type(identity) is not int:
        return None
    return conn.execute(f"SELECT * FROM {table} WHERE id=?", (identity,)).fetchone()


def ordered_timestamps(*values):
    """Writes may cross a second boundary; require valid chronological evidence."""
    try:
        parsed = [datetime.fromisoformat(value) for value in values]
        return all(first <= second for first, second in zip(parsed, parsed[1:]))
    except (ValueError, TypeError):
        return False


def signed_snapshot_matches(detail, source, quantity):
    """Match original identifiers/fields and the logging contract's signed totals."""
    return (
        detail is not None
        and source is not None
        and detail["quantity"] == quantity
        and all(
            detail[key] == source[key]
            for key in (
                "person_id",
                "item_id",
                "item_name_snapshot",
                "item_short_label_snapshot",
                "unit_price_eur",
                "unit_purchase_price_eur",
            )
        )
        and detail["total_eur"] == round(quantity * source["unit_price_eur"], 2)
        and detail["purchase_total_eur"] == round(quantity * source["unit_purchase_price_eur"], 2)
        and detail["profit_eur"] == round(quantity * (source["unit_price_eur"] - source["unit_purchase_price_eur"]), 2)
    )


def operation(conn, identity):
    receipt = conn.execute("SELECT * FROM operation_receipts WHERE operation_id=?", (identity,)).fetchone()
    if receipt is None:
        return None
    try:
        payload = json.loads(receipt["payload_json"])
        result = json.loads(receipt["result_json"])
    except (ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or not isinstance(result, dict):
        return None
    return receipt, payload, result


def ordinary_complete(conn, transaction, details):
    if not details or any(detail["kind"] != "CONSUMPTION_CORRECTION" for detail in details):
        return False
    metadata = []
    for detail in details:
        correction = conn.execute(
            "SELECT * FROM correction_details WHERE transaction_item_id=?", (detail["id"],)
        ).fetchone()
        if correction is None or correction["purpose"] != "erroneous_booking" or not correction["authorized_by"]:
            return False
        source = row(conn, "transaction_items", correction["source_transaction_item_id"])
        booking = conn.execute(
            "SELECT * FROM booking_sources WHERE transaction_item_id=?", (correction["source_transaction_item_id"],)
        ).fetchone()
        line = row(conn, "order_lines", correction["original_order_line_id"])
        if (
            source is None
            or source["kind"] != "CONSUME"
            or source["quantity"] <= 0
            or detail["quantity"] >= 0
            or not signed_snapshot_matches(detail, source, detail["quantity"])
            or booking is None
            or line is None
            or booking["original_order_line_id"] != line["id"]
            or correction["consumed_date"] != booking["consumed_date"]
            or booking["consumed_date"] != line["consumed_date"]
            or source["person_id"] != line["person_id"]
            or source["item_id"] != line["item_id"]
            or correction["corrected_at"] != detail["timestamp"]
        ):
            return False
        reversed_quantity = conn.execute(
            "SELECT COALESCE(-SUM(ti.quantity),0) FROM correction_details cd JOIN transaction_items ti ON ti.id=cd.transaction_item_id WHERE cd.source_transaction_item_id=?",
            (source["id"],),
        ).fetchone()[0]
        if reversed_quantity > source["quantity"]:
            return False
        metadata.append(correction)
    identities = {item["operation_id"] for item in metadata}
    if len(identities) != 1:
        return False
    found = operation(conn, identities.pop())
    if found is None:
        return False
    receipt, payload, result = found
    if receipt["transaction_id"] != transaction["id"] or result.get("status") != "ok":
        return False
    removed = -sum(item["quantity"] for item in details)
    if transaction["type"] == "CHANGE_APPROVED":
        request_id = payload.get("request_id")
        request = row(conn, "change_requests", request_id)
        return (
            receipt["endpoint"] == "member-decision"
            and payload.get("decision") == "APPROVED"
            and receipt["operation_id"] == f"member-decision:{request_id}"
            and request is not None
            and request["status"] == "APPROVED"
            and result.get("request_id") == request_id
            and result.get("decision") == "APPROVED"
            and result.get("person_id") == request["person_id"] == transaction["person_id"]
            and ordered_timestamps(request["decided_at"], transaction["timestamp"], receipt["created_at"])
            and transaction["total"] == 0
            and removed == request["quantity_to_remove"]
            and all(
                item["change_request_id"] == request_id and item["original_order_line_id"] == request["order_line_id"]
                for item in metadata
            )
        )
    return (
        receipt["endpoint"] == "admin-adjust"
        and payload.get("correction_purpose") == "erroneous_booking"
        and isinstance(payload.get("delta"), int)
        and payload["delta"] < 0
        and 0 < removed <= -payload["delta"]
        and payload.get("person_id") == transaction["person_id"]
        and all(
            detail["person_id"] == transaction["person_id"]
            and (payload.get("item_id") is None or detail["item_id"] == payload["item_id"])
            for detail in details
        )
        and all(item["change_request_id"] is None for item in metadata)
        and transaction["total"] == round(sum(detail["total_eur"] for detail in details), 2)
    )


def round_complete(conn, transaction):
    """Validate the whole cancellation operation, including every required reversal."""
    cancellations = conn.execute(
        "SELECT rc.* FROM round_cancellations rc JOIN transaction_items ti ON ti.id=rc.transaction_item_id WHERE ti.transaction_id=?",
        (transaction["id"],),
    ).fetchall()
    if not cancellations or transaction["type"] != "ROUND_CANCELLED" or transaction["total"] != 0:
        return False
    identities = {item["operation_id"] for item in cancellations}
    if len(identities) != 1:
        return False
    found = operation(conn, identities.pop())
    if found is None:
        return False
    receipt, payload, result = found
    cancellations = conn.execute(
        "SELECT * FROM round_cancellations WHERE operation_id=?", (receipt["operation_id"],)
    ).fetchall()
    expected_details = set()
    parent_ids = set()
    operation_units = {
        item[0]
        for item in conn.execute(
            "SELECT round_unit_id FROM round_cancellations WHERE operation_id=?", (receipt["operation_id"],)
        )
    }
    cancelled_units = {
        item[0]
        for item in conn.execute(
            "SELECT id FROM round_units WHERE cancelled_operation_id=?", (receipt["operation_id"],)
        )
    }
    if operation_units != cancelled_units:
        return False
    for cancellation in cancellations:
        unit = row(conn, "round_units", cancellation["round_unit_id"])
        detail = row(conn, "transaction_items", cancellation["transaction_item_id"])
        if unit is None or detail is None or unit["cancelled_operation_id"] != receipt["operation_id"]:
            return False
        parent = row(conn, "transactions", detail["transaction_id"])
        if parent is None or parent["type"] != "ROUND_CANCELLED" or parent["total"] != 0:
            return False
        parent_ids.add(parent["id"])
        line = row(conn, "order_lines", unit["original_order_line_id"])
        source = row(conn, "transaction_items", unit["booking_transaction_item_id"])
        if (
            line is None
            or source is None
            or source["kind"] not in {"ROUND_REQUEST_APPROVED", "CONSUME"}
            or source["item_name_snapshot"] != "1 Runde"
            or not 0 < unit["unit_number"] <= source["quantity"]
            or source["person_id"] != line["person_id"]
            or source["item_id"] != line["item_id"]
            or source["unit_price_eur"] != line["unit_price_eur"]
            or detail["kind"] != "ROUND_CANCELLATION"
            or not signed_snapshot_matches(detail, line, -1)
            or not cancellation["authorized_by"]
            or not ordered_timestamps(
                parent["timestamp"], detail["timestamp"], cancellation["cancelled_at"], receipt["created_at"]
            )
        ):
            return False
        expected_details.add(detail["id"])
        deductions = conn.execute("SELECT * FROM round_deductions WHERE round_unit_id=?", (unit["id"],)).fetchall()
        for deduction in deductions:
            original = row(conn, "transaction_items", deduction["transaction_item_id"])
            drink = row(conn, "order_lines", deduction["original_order_line_id"])
            event = row(conn, "round_events", deduction["round_event_id"])
            reversal = conn.execute("SELECT * FROM round_reversals WHERE deduction_id=?", (deduction["id"],)).fetchone()
            if (
                original is None
                or drink is None
                or event is None
                or reversal is None
                or original["kind"] != "ROUND_DEDUCTED"
                or not signed_snapshot_matches(original, drink, -1)
                or original["person_id"] != deduction["person_id"]
                or drink["consumed_date"] != deduction["consumed_date"]
                or event["transaction_id"] != original["transaction_id"]
                or reversal["operation_id"] != receipt["operation_id"]
            ):
                return False
            event_details = conn.execute(
                "SELECT ti.* FROM round_deductions rd JOIN transaction_items ti ON ti.id=rd.transaction_item_id WHERE rd.round_event_id=?",
                (event["id"],),
            ).fetchall()
            event_vk = round(-sum(item["total_eur"] for item in event_details), 2)
            event_cost = round(-sum(item["purchase_total_eur"] for item in event_details), 2)
            if (
                event["deducted_vk_eur"] != event_vk
                or event["deducted_purchase_eur"] != event_cost
                or event["profit_vs_purchase_eur"] != round(event["round_price_eur"] - event_cost, 2)
                or event["profit_vs_retail_eur"] != round(event["round_price_eur"] - event_vk, 2)
            ):
                return False
            compensating = row(conn, "transaction_items", reversal["transaction_item_id"])
            compensating_event = row(conn, "round_events", reversal["round_event_id"])
            if (
                compensating is None
                or compensating["kind"] != "ROUND_DEDUCTION_REVERSAL"
                or compensating["transaction_id"] != parent["id"]
                or not signed_snapshot_matches(compensating, original, 1)
                or not ordered_timestamps(
                    parent["timestamp"], compensating["timestamp"], reversal["reversed_at"], receipt["created_at"]
                )
                or compensating_event is None
                or compensating_event["transaction_id"] != parent["id"]
                or compensating_event["round_price_eur"] != 0
                or compensating_event["deducted_vk_eur"] != -original["unit_price_eur"]
                or compensating_event["deducted_purchase_eur"] != -original["unit_purchase_price_eur"]
                or compensating_event["profit_vs_purchase_eur"] != original["unit_purchase_price_eur"]
                or compensating_event["profit_vs_retail_eur"] != original["unit_price_eur"]
            ):
                return False
            expected_details.add(compensating["id"])
    actual_details = {
        item[0]
        for parent_id in parent_ids
        for item in conn.execute("SELECT id FROM transaction_items WHERE transaction_id=?", (parent_id,))
    }
    if expected_details != actual_details:
        return False
    if receipt["endpoint"] == "round-cancel":
        return (
            receipt["transaction_id"] == transaction["id"]
            and result.get("status") == "round_cancelled"
            and result.get("transaction_id") == transaction["id"]
            and isinstance(payload.get("round_unit_ids"), list)
            and all(type(identity) is int for identity in payload["round_unit_ids"])
            and len(payload["round_unit_ids"]) == len(operation_units)
            and set(payload["round_unit_ids"]) == operation_units
            and result.get("round_unit_ids") == payload["round_unit_ids"]
            and result.get("restored_drinks") == len(expected_details) - len(cancellations)
        )
    if receipt["endpoint"] == "member-decision":
        request_id = payload.get("request_id")
        if type(request_id) is not int:
            return False
        request = row(conn, "change_requests", request_id)
        approval = row(conn, "transactions", receipt["transaction_id"])
        reservations = {
            item[0]
            for item in conn.execute(
                "SELECT round_unit_id FROM round_request_units WHERE change_request_id=?", (request_id,)
            )
        }
        return (
            request is not None
            and request["status"] == "APPROVED"
            and payload.get("decision") == "APPROVED"
            and result.get("decision") == "APPROVED"
            and result.get("status") == "ok"
            and result.get("request_id") == request_id
            and result.get("person_id") == request["person_id"]
            and receipt["operation_id"] == f"member-decision:{request_id}"
            and approval is not None
            and approval["type"] == "CHANGE_APPROVED"
            and approval["total"] == 0
            and approval["person_id"] == request["person_id"]
            and ordered_timestamps(request["decided_at"], approval["timestamp"], receipt["created_at"])
            and len(operation_units) == request["quantity_to_remove"]
            and reservations == operation_units
            and all(
                item["change_request_id"] == request_id
                and row(conn, "round_units", item["round_unit_id"])["original_order_line_id"]
                == request["order_line_id"]
                for item in cancellations
            )
        )
    # Generic negative round adjustments legitimately have a receipt without a
    # single parent T: one operation may cancel several source lines/ROUND_CANCELLEDs.
    return (
        receipt["endpoint"] == "admin-adjust"
        and result.get("status") == "ok"
        and payload.get("correction_purpose") == "erroneous_booking"
        and isinstance(payload.get("delta"), int)
        and len(operation_units) == -payload["delta"] > 0
        and all(
            item["change_request_id"] is None
            and row(conn, "order_lines", row(conn, "round_units", item["round_unit_id"])["original_order_line_id"])[
                "person_id"
            ]
            == payload.get("person_id")
            and (
                payload.get("item_id") is None
                or row(conn, "order_lines", row(conn, "round_units", item["round_unit_id"])["original_order_line_id"])[
                    "item_id"
                ]
                == payload["item_id"]
            )
            for item in cancellations
        )
    )


def ambiguous_correction_transactions(conn):
    """Count unverified parent audits, including incomplete new round operations."""
    transactions = conn.execute(
        "SELECT * FROM transactions WHERE type IN ('CHANGE_APPROVED','ROUND_CANCELLED') OR (type='ADMIN_ADJUSTMENT' AND total<0)"
    ).fetchall()
    ambiguous = 0
    for transaction in transactions:
        if transaction["type"] == "ROUND_CANCELLED":
            complete = round_complete(conn, transaction)
        else:
            details = conn.execute(
                "SELECT * FROM transaction_items WHERE transaction_id=?", (transaction["id"],)
            ).fetchall()
            complete = ordinary_complete(conn, transaction, details)
            if not complete and transaction["type"] == "CHANGE_APPROVED" and not details:
                receipt = conn.execute(
                    "SELECT operation_id FROM operation_receipts WHERE endpoint='member-decision' AND transaction_id=?",
                    (transaction["id"],),
                ).fetchone()
                if receipt:
                    parents = conn.execute(
                        "SELECT DISTINCT t.* FROM transactions t JOIN transaction_items ti ON ti.transaction_id=t.id JOIN round_cancellations rc ON rc.transaction_item_id=ti.id WHERE rc.operation_id=?",
                        (receipt["operation_id"],),
                    ).fetchall()
                    complete = bool(parents) and all(round_complete(conn, parent) for parent in parents)
        ambiguous += not complete
    return ambiguous
