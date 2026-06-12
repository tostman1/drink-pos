"""Database initialization facade.

The legacy initializer remains the source of truth while migrations are moved
out of the monolith. These wrappers give new route and service modules a stable
import path without changing schema behavior.
"""

from __future__ import annotations

import importlib
from types import ModuleType


def _legacy() -> ModuleType:
    """Return the legacy module in package or script import mode."""

    for name in ("app.legacy_main", "legacy_main", "main"):
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    raise ImportError("Could not import legacy Drink POS database initializer")


def init_db() -> None:
    """Create and migrate the Drink POS SQLite database."""

    _legacy().init_db()


def ensure_indexes(conn) -> None:
    """Ensure database indexes exist."""

    _legacy().ensure_indexes(conn)


def migrate_people(conn) -> None:
    """Apply people table migrations."""

    _legacy().migrate_people(conn)


def migrate_items(conn) -> None:
    """Apply item table migrations."""

    _legacy().migrate_items(conn)


def ensure_settings(conn) -> None:
    """Ensure all required settings rows exist."""

    _legacy().ensure_settings(conn)
