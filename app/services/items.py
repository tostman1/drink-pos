"""Item service functions."""

from __future__ import annotations

import sqlite3
from typing import Any

try:
    from app.config import is_system_item_name
    from app.utils.formatting import short_label_from_name
    from app.utils.helpers import now_text
except ImportError:
    from config import is_system_item_name
    from utils.formatting import short_label_from_name
    from utils.helpers import now_text


def get_items(conn: sqlite3.Connection, include_archived: bool = False) -> list[sqlite3.Row]:
    """Return items ordered for display."""

    sql = "SELECT * FROM items"
    if not include_archived:
        sql += " WHERE archived_at IS NULL"
    sql += " ORDER BY sort_order, name COLLATE NOCASE"
    return list(conn.execute(sql).fetchall())


def get_item_by_id(conn: sqlite3.Connection, item_id: int) -> sqlite3.Row | None:
    """Return an active item by id."""

    return conn.execute("SELECT * FROM items WHERE id = ? AND archived_at IS NULL", (item_id,)).fetchone()


def get_item_by_name(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    """Return an active item by exact name."""

    return conn.execute("SELECT * FROM items WHERE name = ? AND archived_at IS NULL", (name.strip(),)).fetchone()


def list_admin_items(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all non-archived items available to admins."""

    return get_items(conn, include_archived=False)


def list_user_items(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return non-archived, active, public items."""

    return list(
        conn.execute(
            """
            SELECT *
            FROM items
            WHERE active = 1 AND admin_only = 0 AND archived_at IS NULL
            ORDER BY sort_order, name COLLATE NOCASE
            """
        ).fetchall()
    )


def create_item(conn: sqlite3.Connection, item: dict[str, Any]) -> int:
    """Create an item and return its id."""

    name = str(item["name"]).strip()
    short_label = str(item.get("short_label") or short_label_from_name(name)).strip()
    cur = conn.execute(
        """
        INSERT INTO items (
            name, short_label, price_eur, purchase_price_eur, active,
            admin_only, sort_order, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            short_label,
            float(item.get("price_eur", item.get("price", 0)) or 0),
            float(item.get("purchase_price_eur", item.get("purchase_price", 0)) or 0),
            1 if item.get("active", True) else 0,
            1 if item.get("admin_only", False) else 0,
            int(item.get("sort_order", 100) or 100),
            now_text(),
        ),
    )
    return int(cur.lastrowid)


def update_item(conn: sqlite3.Connection, item_id: int, updates: dict[str, Any]) -> None:
    """Update editable item fields."""

    allowed = {
        "name",
        "short_label",
        "price_eur",
        "purchase_price_eur",
        "active",
        "admin_only",
        "sort_order",
    }
    fields = {key: value for key, value in updates.items() if key in allowed}
    if not fields:
        raise ValueError("No supported item fields to update")
    if get_item_by_id(conn, item_id) is None:
        raise LookupError("Item not found")
    assignments = ", ".join(f"{key} = ?" for key in fields)
    conn.execute(f"UPDATE items SET {assignments} WHERE id = ?", [*fields.values(), item_id])


def delete_item(conn: sqlite3.Connection, item_id: int) -> None:
    """Archive an item unless it is a reserved system item."""

    item = get_item_by_id(conn, item_id)
    if item is None:
        raise LookupError("Item not found")
    if is_system_item_name(item["name"]):
        raise ValueError("System items cannot be deleted")
    conn.execute("UPDATE items SET active = 0, archived_at = ? WHERE id = ?", (now_text(), item_id))
