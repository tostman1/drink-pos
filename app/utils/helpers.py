"""General helpers shared across services."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

try:
    from app.config import database_info, is_production
except ImportError:
    from config import database_info, is_production


def now_text() -> str:
    """Return the current local timestamp in database format."""

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text() -> str:
    """Return the current local date in database format."""

    return datetime.now().strftime("%Y-%m-%d")


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """Return whether a table exists in the connected database."""

    row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (table_name,)).fetchone()
    return row is not None


def column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Return whether a column exists on a table."""

    if not table_exists(conn, table_name):
        return False
    return any(row["name"] == column_name for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall())


def add_column_if_missing(conn: sqlite3.Connection, table: str, column: str, definition: str | None = None) -> None:
    """Add a column if it is missing.

    Args:
        table: Table to alter.
        column: Column name or a full DDL fragment when definition is None.
        definition: SQL definition without the column name.
    """

    ddl = column if definition is None else f"{column} {definition}"
    column_name = ddl.split()[0]
    if not column_exists(conn, table, column_name):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def get_setting(conn: sqlite3.Connection, key: str, default: str | None = None) -> str | None:
    """Read a setting value from the settings table."""

    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Insert or update a setting value."""

    conn.execute(
        """
        INSERT INTO settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        """,
        (key, str(value), now_text()),
    )


def setting_bool(conn: sqlite3.Connection, key: str, default: str = "1") -> bool:
    """Read a setting as a boolean."""

    return get_setting(conn, key, default) in {"1", "true", "True", True}


def row_get(row: sqlite3.Row | dict[str, Any], key: str, default=None):
    """Read a field from either sqlite.Row or dict."""

    if isinstance(row, dict):
        return row.get(key, default)
    return row[key] if key in row.keys() else default


def paginate(items: list[Any], limit: int = 100, offset: int = 0) -> list[Any]:
    """Return a bounded slice of a list."""

    safe_limit = max(1, min(int(limit or 100), 1000))
    safe_offset = max(0, int(offset or 0))
    return items[safe_offset : safe_offset + safe_limit]


__all__ = [
    "add_column_if_missing",
    "column_exists",
    "database_info",
    "get_setting",
    "is_production",
    "now_text",
    "paginate",
    "row_get",
    "set_setting",
    "setting_bool",
    "table_exists",
    "today_text",
]
