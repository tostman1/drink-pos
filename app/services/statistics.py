"""Statistics and transaction service helpers."""

from __future__ import annotations

import sqlite3
from typing import Any

try:
    from app.utils.helpers import now_text, row_get
except ImportError:
    from utils.helpers import now_text, row_get


def log_transaction(conn: sqlite3.Connection, person_id: int | None, typ: str, total_eur: float, details: str) -> int:
    """Insert a transaction row and return its id."""

    cur = conn.execute(
        "INSERT INTO transactions (person_id, type, total, details, timestamp) VALUES (?, ?, ?, ?, ?)",
        (person_id, typ, round(float(total_eur), 2), details, now_text()),
    )
    return int(cur.lastrowid)


def log_transaction_item(
    conn: sqlite3.Connection,
    transaction_id: int,
    person_id: int | None,
    line: sqlite3.Row | dict[str, Any],
    quantity: int,
    kind: str,
) -> None:
    """Insert a transaction item snapshot."""

    qty = int(quantity)
    price = float(row_get(line, "unit_price_eur", 0) or 0)
    purchase = float(row_get(line, "unit_purchase_price_eur", 0) or 0)
    conn.execute(
        """
        INSERT INTO transaction_items (
            transaction_id, person_id, item_id, item_name_snapshot, item_short_label_snapshot,
            quantity, unit_price_eur, unit_purchase_price_eur, total_eur,
            purchase_total_eur, profit_eur, kind, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            transaction_id,
            person_id,
            row_get(line, "item_id"),
            row_get(line, "item_name_snapshot"),
            row_get(line, "item_short_label_snapshot"),
            qty,
            price,
            purchase,
            round(qty * price, 2),
            round(qty * purchase, 2),
            round(qty * (price - purchase), 2),
            kind,
            now_text(),
        ),
    )


def build_report_rows(conn: sqlite3.Connection, filters: dict[str, Any]) -> list[sqlite3.Row]:
    """Build basic transaction report rows for later route formatting."""

    limit = max(1, min(int(filters.get("limit", 500) or 500), 5000))
    return list(
        conn.execute(
            """
            SELECT t.id, t.person_id, p.name AS person_name, t.type, t.total, t.details, t.timestamp
            FROM transactions t
            LEFT JOIN people p ON p.id = t.person_id
            ORDER BY t.timestamp DESC, t.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    )


def calculate_cashup_preview(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return a simple cashup preview over currently open lines."""

    rows = conn.execute(
        """
        SELECT COUNT(*) AS line_count, COALESCE(SUM(quantity * unit_price_eur), 0) AS total
        FROM order_lines
        WHERE quantity > 0 AND event_open = 1
        """
    ).fetchone()
    return {"line_count": int(rows["line_count"] or 0), "total": round(float(rows["total"] or 0), 2)}


def build_auto_round_plan(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return a placeholder-friendly list of open paid round units."""

    return [dict(row) for row in conn.execute("SELECT * FROM paid_round_units WHERE event_open = 1").fetchall()]


def apply_auto_round_deductions(conn: sqlite3.Connection, plan: list[dict[str, Any]]) -> int:
    """Mark planned round units closed and return the count."""

    count = 0
    for row in plan:
        conn.execute("UPDATE paid_round_units SET event_open = 0, closed_at = ? WHERE id = ?", (now_text(), row["id"]))
        count += 1
    return count
