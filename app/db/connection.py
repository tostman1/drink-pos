"""SQLite connection management for Drink POS.

Connections are intentionally short-lived and configured consistently at the
boundary: row access by name, foreign keys enabled, and a busy timeout so WAL
writers have time to complete.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

try:
    from app.config import DB_BUSY_TIMEOUT_MS, DB_PATH, DB_TIMEOUT_SECONDS
except ImportError:
    from config import DB_BUSY_TIMEOUT_MS, DB_PATH, DB_TIMEOUT_SECONDS


def configure_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    """Apply the app's SQLite pragmas to a connection and return it."""

    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS}")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Yield a configured SQLite connection and always close it afterwards."""

    conn = configure_connection(sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT_SECONDS))
    try:
        yield conn
    finally:
        conn.close()
