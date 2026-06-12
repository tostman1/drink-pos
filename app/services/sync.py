"""Sync payload service functions."""

from __future__ import annotations

import sqlite3
from typing import Any

try:
    from app.utils.helpers import now_text
except ImportError:
    from utils.helpers import now_text


def get_sync_state(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return a compact revision marker for clients."""

    timestamp_checks = [
        ("transactions", "timestamp"),
        ("order_lines", "updated_at"),
        ("settings", "updated_at"),
        ("change_requests", "requested_at"),
        ("change_requests", "decided_at"),
        ("round_requests", "requested_at"),
        ("round_requests", "decided_at"),
        ("round_events", "timestamp"),
    ]
    timestamps: list[str] = []
    for table, column in timestamp_checks:
        try:
            value = conn.execute(f"SELECT MAX({column}) AS v FROM {table}").fetchone()["v"]
        except sqlite3.Error:
            value = None
        if value:
            timestamps.append(str(value))
    try:
        max_transaction_id = int(conn.execute("SELECT COALESCE(MAX(id), 0) AS v FROM transactions").fetchone()["v"] or 0)
    except sqlite3.Error:
        max_transaction_id = 0
    db_changed_at = max(timestamps) if timestamps else now_text()
    return {
        "db_changed_at": db_changed_at,
        "max_transaction_id": max_transaction_id,
        "db_revision": f"{max_transaction_id}:{db_changed_at}",
    }


def get_config_payload(conn: sqlite3.Connection) -> dict[str, Any]:
    """Return settings as a key/value payload plus sync state."""

    settings = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM settings").fetchall()}
    return {"settings": settings, **get_sync_state(conn)}


def update_sync_revision(conn: sqlite3.Connection) -> None:
    """Touch the sync revision by updating a harmless setting row."""

    conn.execute(
        """
        INSERT INTO settings (key, value, updated_at)
        VALUES ('sync_revision_touch', ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (now_text(), now_text()),
    )
