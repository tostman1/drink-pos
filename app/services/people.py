"""People service functions.

Service functions accept an explicit SQLite connection and keep HTTP concerns
out of the business layer.
"""

from __future__ import annotations

import sqlite3
from typing import Any

try:
    from app.utils.helpers import now_text
except ImportError:
    from utils.helpers import now_text


def get_person(conn: sqlite3.Connection, person_id: int, allow_archived: bool = True) -> sqlite3.Row | None:
    """Return one person row by id.

    Args:
        conn: Open SQLite connection.
        person_id: Person primary key.
        allow_archived: Include inactive or archived people when true.

    Returns:
        A sqlite.Row when found, otherwise None.
    """

    sql = "SELECT * FROM people WHERE id = ?"
    if not allow_archived:
        sql += " AND active = 1 AND archived_at IS NULL"
    return conn.execute(sql, (person_id,)).fetchone()


def list_people(conn: sqlite3.Connection, include_archived: bool = False) -> list[sqlite3.Row]:
    """List people in display order."""

    sql = "SELECT * FROM people"
    if not include_archived:
        sql += " WHERE active = 1 AND archived_at IS NULL"
    sql += " ORDER BY last_name COLLATE NOCASE, first_name COLLATE NOCASE, name COLLATE NOCASE"
    return list(conn.execute(sql).fetchall())


def update_person(conn: sqlite3.Connection, person_id: int, updates: dict[str, Any]) -> None:
    """Update editable person fields.

    Raises:
        ValueError: If no supported fields are provided.
        LookupError: If the person does not exist.
    """

    allowed = {"first_name", "last_name", "name", "active", "archived_at"}
    fields = {key: value for key, value in updates.items() if key in allowed}
    if not fields:
        raise ValueError("No supported person fields to update")
    if get_person(conn, person_id) is None:
        raise LookupError("Person not found")
    assignments = ", ".join(f"{key} = ?" for key in fields)
    conn.execute(f"UPDATE people SET {assignments} WHERE id = ?", [*fields.values(), person_id])


def get_member_messages_for_person(conn: sqlite3.Connection, person_id: int) -> list[dict[str, Any]]:
    """Return active, unacknowledged member messages for a person."""

    rows = conn.execute(
        """
        SELECT m.id, m.title, m.message, m.created_at
        FROM member_messages m
        JOIN member_message_recipients r ON r.message_id = m.id
        WHERE r.person_id = ?
          AND m.active = 1
          AND m.archived_at IS NULL
          AND r.acknowledged_at IS NULL
        ORDER BY m.created_at DESC, m.id DESC
        """,
        (person_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def archive_member_message_if_completed(conn: sqlite3.Connection, message_id: int) -> bool:
    """Archive a message once all recipients have acknowledged it."""

    remaining = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM member_message_recipients
        WHERE message_id = ? AND acknowledged_at IS NULL
        """,
        (message_id,),
    ).fetchone()["c"]
    if int(remaining or 0) > 0:
        return False
    conn.execute(
        "UPDATE member_messages SET active = 0, archived_at = ? WHERE id = ? AND archived_at IS NULL",
        (now_text(), message_id),
    )
    return True
