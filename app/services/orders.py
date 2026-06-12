"""Order service functions."""

from __future__ import annotations

import sqlite3
from typing import Any

try:
    from app.utils.helpers import now_text
except ImportError:
    from utils.helpers import now_text


def add_order_line(conn: sqlite3.Connection, person_id: int, item_id: int, quantity: int = 1) -> int:
    """Add an order line for a person and return the line id."""

    item = conn.execute("SELECT * FROM items WHERE id = ? AND archived_at IS NULL", (item_id,)).fetchone()
    if item is None:
        raise LookupError("Item not found")
    now = now_text()
    cur = conn.execute(
        """
        INSERT INTO order_lines (
            person_id, item_id, quantity, unit_price_eur, unit_purchase_price_eur,
            item_name_snapshot, item_short_label_snapshot, admin_only_snapshot,
            consumed_date, event_open, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        (
            person_id,
            item_id,
            int(quantity),
            float(item["price_eur"] or 0),
            float(item["purchase_price_eur"] or 0),
            item["name"],
            item["short_label"],
            int(item["admin_only"] or 0),
            now[:10],
            now,
            now,
        ),
    )
    return int(cur.lastrowid)


def remove_from_order_line(conn: sqlite3.Connection, line_id: int, quantity: int) -> int:
    """Remove quantity from an open order line and return the remaining amount."""

    row = conn.execute("SELECT quantity FROM order_lines WHERE id = ?", (line_id,)).fetchone()
    if row is None:
        raise LookupError("Order line not found")
    remaining = max(0, int(row["quantity"] or 0) - int(quantity))
    conn.execute("UPDATE order_lines SET quantity = ?, updated_at = ? WHERE id = ?", (remaining, now_text(), line_id))
    return remaining


def get_open_lines(conn: sqlite3.Connection, person_id: int | None = None) -> list[sqlite3.Row]:
    """Return open order lines, optionally for one person."""

    params: tuple[Any, ...] = ()
    where = "WHERE quantity > 0 AND event_open = 1"
    if person_id is not None:
        where += " AND person_id = ?"
        params = (person_id,)
    return list(
        conn.execute(
            f"""
            SELECT *
            FROM order_lines
            {where}
            ORDER BY consumed_date, id
            """,
            params,
        ).fetchall()
    )


def get_order_total(conn: sqlite3.Connection, person_id: int) -> float:
    """Return the open retail total for a person."""

    row = conn.execute(
        """
        SELECT COALESCE(SUM(quantity * unit_price_eur), 0) AS total
        FROM order_lines
        WHERE person_id = ? AND quantity > 0 AND event_open = 1
        """,
        (person_id,),
    ).fetchone()
    return round(float(row["total"] or 0), 2)


def make_payment_detail_lines(lines: list[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convert order rows to payment detail dictionaries."""

    return [
        {
            "line_id": int(line["id"]),
            "item_id": line["item_id"],
            "name": line["item_name_snapshot"],
            "short_label": line["item_short_label_snapshot"],
            "quantity": int(line["quantity"] or 0),
            "unit_price_eur": float(line["unit_price_eur"] or 0),
            "subtotal_eur": round(int(line["quantity"] or 0) * float(line["unit_price_eur"] or 0), 2),
        }
        for line in lines
    ]


def make_summary_lines(lines: list[sqlite3.Row]) -> list[dict[str, Any]]:
    """Group order rows into item summary lines."""

    grouped: dict[tuple[int | None, str], dict[str, Any]] = {}
    for line in lines:
        key = (line["item_id"], line["item_name_snapshot"])
        entry = grouped.setdefault(
            key,
            {
                "item_id": line["item_id"],
                "name": line["item_name_snapshot"],
                "short_label": line["item_short_label_snapshot"],
                "quantity": 0,
                "subtotal_eur": 0.0,
            },
        )
        qty = int(line["quantity"] or 0)
        entry["quantity"] += qty
        entry["subtotal_eur"] = round(entry["subtotal_eur"] + qty * float(line["unit_price_eur"] or 0), 2)
    return list(grouped.values())


def clear_person_orders(conn: sqlite3.Connection, person_id: int) -> int:
    """Close all open lines for a person and return the count changed."""

    lines = get_open_lines(conn, person_id)
    conn.execute(
        "UPDATE order_lines SET quantity = 0, updated_at = ? WHERE person_id = ? AND quantity > 0 AND event_open = 1",
        (now_text(), person_id),
    )
    return len(lines)
