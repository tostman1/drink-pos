"""Round request service functions."""

from __future__ import annotations

import sqlite3
from typing import Any

try:
    from app.config import ROUND_ITEM_NAME
    from app.utils.helpers import now_text
except ImportError:
    from config import ROUND_ITEM_NAME
    from utils.helpers import now_text


def create_round_request(conn: sqlite3.Connection, person_id: int, quantity: int = 1, reason: str | None = None) -> int:
    """Create a pending round request and return its id."""

    item = conn.execute("SELECT id FROM items WHERE name = ? AND archived_at IS NULL", (ROUND_ITEM_NAME,)).fetchone()
    cur = conn.execute(
        """
        INSERT INTO round_requests (person_id, item_id, quantity, reason, status, requested_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?)
        """,
        (person_id, item["id"] if item else None, int(quantity), reason, now_text()),
    )
    return int(cur.lastrowid)


def get_pending_round_requests(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return pending round requests."""

    return list(conn.execute("SELECT * FROM round_requests WHERE status = 'PENDING' ORDER BY requested_at, id").fetchall())


def deduct_round_logic(conn: sqlite3.Connection, pin: str | None = None) -> dict[str, Any]:
    """Return a lightweight round deduction preview.

    Full deduction behavior remains in the legacy module while route extraction
    continues.
    """

    pending = get_pending_round_requests(conn)
    return {"pending_round_requests": len(pending), "details": [dict(row) for row in pending]}


def admin_decide_round_request(conn: sqlite3.Connection, request_id: int, approved: bool) -> None:
    """Approve or reject a pending round request."""

    status = "APPROVED" if approved else "REJECTED"
    conn.execute(
        "UPDATE round_requests SET status = ?, decided_at = ? WHERE id = ? AND status = 'PENDING'",
        (status, now_text(), request_id),
    )
