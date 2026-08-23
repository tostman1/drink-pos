"""Database initialization facade."""

from __future__ import annotations

try:
    from app.db import schema
except ImportError:
    from db import schema


def init_db() -> None:
    """Create and migrate the Drink POS SQLite database."""

    schema.init_db()


def ensure_indexes(conn) -> None:
    """Ensure database indexes exist."""

    schema.ensure_indexes(conn)


def migrate_people(conn) -> None:
    """Apply people table migrations."""

    schema.migrate_people(conn)


def migrate_items(conn) -> None:
    """Apply item table migrations."""

    schema.migrate_items(conn)


def ensure_settings(conn) -> None:
    """Ensure all required settings rows exist."""

    schema.ensure_settings(conn)
