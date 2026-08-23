"""SQLite schema creation, migration, and seed helpers for Drink POS."""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Callable

try:
    from app.config import (
        DB_PATH as DEFAULT_DB_PATH,
        DEFAULT_COST_WARNING_TEMPLATE,
        DEFAULT_ITEMS,
        DEFAULT_NAMES,
        DEFAULT_PAYMENT_REMINDER_TEMPLATE,
        DEFAULT_ROUND_PRICE_EUR,
        ENV_PIN_CODE as DEFAULT_ENV_PIN_CODE,
        ENV_PIN_FROM_ENV as DEFAULT_ENV_PIN_FROM_ENV,
        ROUND_ITEM_NAME,
        ROUND_ITEM_SHORT,
    )
    from app.db.connection import get_conn as default_get_conn
    from app.services import messages as message_service
    from app.utils.formatting import short_label_from_name
    from app.utils.helpers import (
        add_column_if_missing,
        column_exists,
        get_setting,
        now_text,
        set_setting,
        table_exists,
        today_text,
    )
    from app.utils.parsing import display_name, split_name
except ImportError:
    from config import (
        DB_PATH as DEFAULT_DB_PATH,
        DEFAULT_COST_WARNING_TEMPLATE,
        DEFAULT_ITEMS,
        DEFAULT_NAMES,
        DEFAULT_PAYMENT_REMINDER_TEMPLATE,
        DEFAULT_ROUND_PRICE_EUR,
        ENV_PIN_CODE as DEFAULT_ENV_PIN_CODE,
        ENV_PIN_FROM_ENV as DEFAULT_ENV_PIN_FROM_ENV,
        ROUND_ITEM_NAME,
        ROUND_ITEM_SHORT,
    )
    from db.connection import get_conn as default_get_conn
    from services import messages as message_service
    from utils.formatting import short_label_from_name
    from utils.helpers import (
        add_column_if_missing,
        column_exists,
        get_setting,
        now_text,
        set_setting,
        table_exists,
        today_text,
    )
    from utils.parsing import display_name, split_name


DB_PATH = DEFAULT_DB_PATH
ENV_PIN_CODE = DEFAULT_ENV_PIN_CODE
ENV_PIN_FROM_ENV = DEFAULT_ENV_PIN_FROM_ENV
get_conn = default_get_conn


def ensure_messages_file() -> None:
    """Create the editable message catalog next to the active database."""

    message_service.ensure_messages_file(DB_PATH)


def configure_runtime(
    db_path: str,
    env_pin_code: str,
    env_pin_from_env: bool,
    get_conn_factory: Callable,
) -> None:
    """Update schema helpers to use the current legacy runtime configuration."""

    global DB_PATH, ENV_PIN_CODE, ENV_PIN_FROM_ENV, get_conn
    DB_PATH = db_path
    ENV_PIN_CODE = env_pin_code
    ENV_PIN_FROM_ENV = env_pin_from_env
    get_conn = get_conn_factory


def database_unreadable_message(error: Exception) -> str:
    return (
        f"Drink POS database is not readable: {DB_PATH}. "
        f"SQLite reported: {error}. "
        "This is usually a corrupted or incomplete SQLite file, not a schema compatibility problem. "
        "Stop the containers, copy drink_pos.db plus any drink_pos.db-wal/drink_pos.db-shm files aside, "
        "run PRAGMA integrity_check, and restore from data/backups or a NAS snapshot."
    )


def is_database_unreadable_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        marker in message
        for marker in (
            "database disk image is malformed",
            "file is not a database",
            "unsupported file format",
            "disk i/o error",
        )
    )


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    ensure_messages_file()

    with get_conn() as conn:
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
        except sqlite3.DatabaseError as exc:
            if is_database_unreadable_error(exc):
                raise RuntimeError(database_unreadable_message(exc)) from exc
            raise

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Keep the old 'name' column for compatibility with old transaction joins,
        # but the application now edits first_name/last_name explicitly.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS people (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """
        )
        add_column_if_missing(conn, "people", "first_name TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "people", "last_name TEXT NOT NULL DEFAULT ''")
        add_column_if_missing(conn, "people", "active INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "people", "archived_at TEXT")
        add_column_if_missing(conn, "people", "created_at TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                short_label TEXT NOT NULL,
                price_eur REAL NOT NULL DEFAULT 0,
                purchase_price_eur REAL NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                admin_only INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 100,
                archived_at TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        add_column_if_missing(conn, "items", "purchase_price_eur REAL NOT NULL DEFAULT 0")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS order_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                item_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 0,
                unit_price_eur REAL NOT NULL,
                unit_purchase_price_eur REAL NOT NULL DEFAULT 0,
                item_name_snapshot TEXT NOT NULL,
                item_short_label_snapshot TEXT NOT NULL,
                admin_only_snapshot INTEGER NOT NULL DEFAULT 0,
                consumed_date TEXT NOT NULL,
                event_open INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(item_id) REFERENCES items(id)
            )
            """
        )

        add_column_if_missing(conn, "order_lines", "event_open INTEGER NOT NULL DEFAULT 1")
        add_column_if_missing(conn, "order_lines", "unit_purchase_price_eur REAL NOT NULL DEFAULT 0")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS change_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                order_line_id INTEGER NOT NULL,
                item_id INTEGER,
                quantity_to_remove INTEGER NOT NULL,
                reason TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                requested_at TEXT NOT NULL,
                decided_at TEXT,
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(order_line_id) REFERENCES order_lines(id),
                FOREIGN KEY(item_id) REFERENCES items(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS round_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                item_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 1,
                reason TEXT,
                status TEXT NOT NULL DEFAULT 'PENDING',
                requested_at TEXT NOT NULL,
                decided_at TEXT,
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(item_id) REFERENCES items(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS member_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                message TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                archived_at TEXT
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS member_message_recipients (
                message_id INTEGER NOT NULL,
                person_id INTEGER NOT NULL,
                acknowledged_at TEXT,
                PRIMARY KEY(message_id, person_id),
                FOREIGN KEY(message_id) REFERENCES member_messages(id) ON DELETE CASCADE,
                FOREIGN KEY(person_id) REFERENCES people(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER,
                type TEXT NOT NULL,
                total REAL NOT NULL,
                details TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(person_id) REFERENCES people(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS client_operations (
                client_operation_id TEXT PRIMARY KEY,
                endpoint TEXT NOT NULL,
                transaction_id INTEGER,
                client_time TEXT,
                device_info TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(transaction_id) REFERENCES transactions(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS self_payment_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_id INTEGER NOT NULL,
                client_payment_id TEXT,
                status TEXT NOT NULL,
                base_amount_cents INTEGER NOT NULL DEFAULT 0,
                card_fee_cents INTEGER NOT NULL DEFAULT 0,
                rounding_mode TEXT NOT NULL DEFAULT 'none',
                rounding_adjustment_cents INTEGER NOT NULL DEFAULT 0,
                amount_eur REAL NOT NULL,
                amount_cents INTEGER NOT NULL,
                currency TEXT NOT NULL DEFAULT 'EUR',
                provider TEXT NOT NULL DEFAULT 'sumup',
                provider_checkout_id TEXT,
                revision TEXT NOT NULL,
                terminal_result TEXT,
                terminal_reference TEXT,
                raw_response TEXT,
                error TEXT,
                transaction_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id)
            )
            """
        )
        add_column_if_missing(conn, "self_payment_sessions", "client_payment_id TEXT")
        add_column_if_missing(conn, "self_payment_sessions", "currency TEXT NOT NULL DEFAULT 'EUR'")
        add_column_if_missing(conn, "self_payment_sessions", "provider TEXT NOT NULL DEFAULT 'sumup'")
        add_column_if_missing(conn, "self_payment_sessions", "provider_checkout_id TEXT")
        add_column_if_missing(conn, "self_payment_sessions", "raw_response TEXT")
        add_column_if_missing(conn, "self_payment_sessions", "completed_at TEXT")
        add_column_if_missing(conn, "self_payment_sessions", "base_amount_cents INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "self_payment_sessions", "card_fee_cents INTEGER NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "self_payment_sessions", "rounding_mode TEXT NOT NULL DEFAULT 'none'")
        add_column_if_missing(conn, "self_payment_sessions", "rounding_adjustment_cents INTEGER NOT NULL DEFAULT 0")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paid_round_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_order_line_id INTEGER,
                payer_person_id INTEGER NOT NULL,
                payer_name_snapshot TEXT NOT NULL,
                round_price_eur REAL NOT NULL,
                payment_transaction_id INTEGER,
                event_open INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                closed_at TEXT,
                FOREIGN KEY(source_order_line_id) REFERENCES order_lines(id),
                FOREIGN KEY(payer_person_id) REFERENCES people(id),
                FOREIGN KEY(payment_transaction_id) REFERENCES transactions(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transaction_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                person_id INTEGER,
                item_id INTEGER,
                item_name_snapshot TEXT NOT NULL,
                item_short_label_snapshot TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price_eur REAL NOT NULL,
                unit_purchase_price_eur REAL NOT NULL DEFAULT 0,
                total_eur REAL NOT NULL,
                purchase_total_eur REAL NOT NULL DEFAULT 0,
                profit_eur REAL NOT NULL DEFAULT 0,
                kind TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(transaction_id) REFERENCES transactions(id),
                FOREIGN KEY(person_id) REFERENCES people(id),
                FOREIGN KEY(item_id) REFERENCES items(id)
            )
            """
        )
        add_column_if_missing(conn, "transaction_items", "unit_purchase_price_eur REAL NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "transaction_items", "purchase_total_eur REAL NOT NULL DEFAULT 0")
        add_column_if_missing(conn, "transaction_items", "profit_eur REAL NOT NULL DEFAULT 0")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS round_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER,
                timestamp TEXT NOT NULL,
                round_price_eur REAL NOT NULL,
                deducted_vk_eur REAL NOT NULL,
                deducted_purchase_eur REAL NOT NULL,
                profit_vs_purchase_eur REAL NOT NULL,
                profit_vs_retail_eur REAL NOT NULL,
                details TEXT,
                FOREIGN KEY(transaction_id) REFERENCES transactions(id)
            )
            """
        )

        migrate_people(conn)
        ensure_default_people(conn)
        migrate_items(conn)
        ensure_default_items(conn)
        ensure_round_item(conn)
        migrate_old_orders(conn)
        backfill_missing_purchase_snapshots(conn)
        ensure_settings(conn)
        ensure_indexes(conn)

        conn.commit()


def ensure_indexes(conn: sqlite3.Connection):
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_transaction_items_kind_timestamp ON transaction_items(kind, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_transaction_items_timestamp ON transaction_items(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_order_lines_quantity_event ON order_lines(quantity, event_open)",
        "CREATE INDEX IF NOT EXISTS idx_order_lines_person_quantity_event ON order_lines(person_id, quantity, event_open)",
        "CREATE INDEX IF NOT EXISTS idx_round_events_timestamp ON round_events(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_type_timestamp ON transactions(type, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_person_timestamp ON transactions(person_id, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_change_requests_status ON change_requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_change_requests_line_status ON change_requests(order_line_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_round_requests_status ON round_requests(status)",
        "CREATE INDEX IF NOT EXISTS idx_round_requests_person_status ON round_requests(person_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_member_messages_active ON member_messages(active, archived_at)",
        "CREATE INDEX IF NOT EXISTS idx_member_message_recipients_person_ack ON member_message_recipients(person_id, acknowledged_at)",
        "CREATE INDEX IF NOT EXISTS idx_member_message_recipients_message ON member_message_recipients(message_id)",
        "CREATE INDEX IF NOT EXISTS idx_self_payment_sessions_person_status ON self_payment_sessions(person_id, status, updated_at)",
        "CREATE INDEX IF NOT EXISTS idx_self_payment_sessions_status_updated ON self_payment_sessions(status, updated_at)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_self_payment_sessions_client_payment_id ON self_payment_sessions(client_payment_id)",
        "CREATE INDEX IF NOT EXISTS idx_self_payment_sessions_provider_checkout ON self_payment_sessions(provider, provider_checkout_id)",
        "CREATE INDEX IF NOT EXISTS idx_paid_round_units_event ON paid_round_units(event_open, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_paid_round_units_source ON paid_round_units(source_order_line_id)",
    ]
    for sql in indexes:
        conn.execute(sql)


def migrate_people(conn: sqlite3.Connection):
    rows = conn.execute("SELECT id, name, first_name, last_name, created_at FROM people").fetchall()
    for row in rows:
        first = row["first_name"] or ""
        last = row["last_name"] or ""
        created = row["created_at"]
        if not first and not last:
            first, last = split_name(row["name"])
        name = display_name(first, last) or row["name"]
        conn.execute(
            """
            UPDATE people
            SET first_name = ?, last_name = ?, name = ?, created_at = COALESCE(created_at, ?)
            WHERE id = ?
            """,
            (first, last, name, now_text(), row["id"]),
        )


def is_placeholder_name(name: str) -> bool:
    return bool(re.fullmatch(r"Person\s+\d+", (name or "").strip()))


def ensure_default_people(conn: sqlite3.Connection):
    existing = conn.execute("SELECT id, name FROM people ORDER BY id").fetchall()
    if existing and all(is_placeholder_name(row["name"]) for row in existing):
        for index, row in enumerate(existing[: len(DEFAULT_NAMES)]):
            first, last = split_name(DEFAULT_NAMES[index])
            conn.execute(
                """
                UPDATE people
                SET first_name = ?, last_name = ?, name = ?, active = 1, archived_at = NULL
                WHERE id = ?
                """,
                (first, last, display_name(first, last), row["id"]),
            )

    for full_name in DEFAULT_NAMES:
        first, last = split_name(full_name)
        name = display_name(first, last)
        row = conn.execute("SELECT id FROM people WHERE name = ?", (name,)).fetchone()
        if not row:
            conn.execute(
                """
                INSERT INTO people (name, first_name, last_name, active, archived_at, created_at)
                VALUES (?, ?, ?, 1, NULL, ?)
                """,
                (name, first, last, now_text()),
            )


def migrate_items(conn: sqlite3.Connection):
    if not table_exists(conn, "drinks"):
        return
    old_drinks = conn.execute("SELECT * FROM drinks").fetchall()
    for index, row in enumerate(old_drinks, start=1):
        name = row["name"]
        price = float(row["price"] if "price" in row.keys() else 0)
        active = int(row["active"] if "active" in row.keys() else 1)
        sort_order = int(row["sort_order"] if "sort_order" in row.keys() else index)
        existing = conn.execute("SELECT id FROM items WHERE name = ?", (name,)).fetchone()
        if not existing:
            conn.execute(
                """
                INSERT INTO items (name, short_label, price_eur, purchase_price_eur, active, admin_only, sort_order, created_at)
                VALUES (?, ?, ?, 0, ?, 0, ?, ?)
                """,
                (name, short_label_from_name(name), price, active, sort_order, now_text()),
            )


def ensure_default_items(conn: sqlite3.Connection):
    for index, item in enumerate(DEFAULT_ITEMS, start=1):
        default_purchase = float(item.get("purchase_price_eur", 0) or 0)
        row = conn.execute("SELECT id, purchase_price_eur FROM items WHERE name = ?", (item["name"],)).fetchone()
        if not row:
            conn.execute(
                """
                INSERT INTO items (name, short_label, price_eur, purchase_price_eur, active, admin_only, sort_order, created_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    item["name"],
                    item["short_label"],
                    float(item["price_eur"]),
                    default_purchase,
                    1 if item.get("admin_only") else 0,
                    index,
                    now_text(),
                ),
            )
        elif default_purchase > 0 and float(row["purchase_price_eur"] or 0) == 0:
            # Upgrade alter Installationen: Vor dem EK-Feature existierende Standardartikel
            # hatten automatisch EK=0. Beim ersten Start mit dieser Version bekommen sie
            # sinnvolle Default-EKs, solange noch kein eigener EK gepflegt wurde.
            conn.execute(
                "UPDATE items SET purchase_price_eur = ? WHERE id = ? AND purchase_price_eur = 0",
                (default_purchase, row["id"]),
            )


def ensure_round_item(conn: sqlite3.Connection):
    """Internal helper item for billing a paid round.

    The round is intentionally not a normal drink/article: only its sales price
    is configurable in settings. Its purchase cost is always computed from the
    actual drinks deducted by /api/deduct-round, not from this helper item.
    """
    row = conn.execute("SELECT id FROM items WHERE name = ?", (ROUND_ITEM_NAME,)).fetchone()
    price = float(get_setting(conn, "round_item_price_eur", DEFAULT_ROUND_PRICE_EUR) or DEFAULT_ROUND_PRICE_EUR)
    if not row:
        max_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) AS max_order FROM items").fetchone()["max_order"]
        conn.execute(
            """
            INSERT INTO items (name, short_label, price_eur, purchase_price_eur, active, admin_only, sort_order, created_at)
            VALUES (?, ?, ?, 0, 1, 1, ?, ?)
            """,
            (ROUND_ITEM_NAME, ROUND_ITEM_SHORT, price, int(max_order) + 1, now_text()),
        )
    else:
        conn.execute(
            """
            UPDATE items
            SET name = ?, short_label = ?, price_eur = ?, purchase_price_eur = 0,
                active = 1, admin_only = 1, archived_at = NULL
            WHERE id = ?
            """,
            (ROUND_ITEM_NAME, ROUND_ITEM_SHORT, price, row["id"]),
        )


def migrate_old_orders(conn: sqlite3.Connection):
    if not table_exists(conn, "orders"):
        return
    existing_new = conn.execute("SELECT COUNT(*) AS c FROM order_lines").fetchone()["c"]
    if existing_new:
        return
    if not column_exists(conn, "orders", "drink"):
        return
    rows = conn.execute("SELECT person_id, drink, quantity FROM orders WHERE quantity > 0").fetchall()
    for row in rows:
        item = conn.execute("SELECT * FROM items WHERE name = ?", (row["drink"],)).fetchone()
        if not item:
            conn.execute(
                """
                INSERT INTO items (name, short_label, price_eur, purchase_price_eur, active, admin_only, sort_order, created_at)
                VALUES (?, ?, 0, 0, 0, 0, 999, ?)
                """,
                (row["drink"], short_label_from_name(row["drink"]), now_text()),
            )
            item = conn.execute("SELECT * FROM items WHERE name = ?", (row["drink"],)).fetchone()
        conn.execute(
            """
            INSERT INTO order_lines (
                person_id, item_id, quantity, unit_price_eur, unit_purchase_price_eur, item_name_snapshot,
                item_short_label_snapshot, admin_only_snapshot, consumed_date, event_open, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["person_id"],
                item["id"],
                int(row["quantity"]),
                float(item["price_eur"]),
                float(item["purchase_price_eur"] if "purchase_price_eur" in item.keys() else 0),
                item["name"],
                item["short_label"],
                int(item["admin_only"]),
                today_text(),
                1,
                now_text(),
                now_text(),
            ),
        )


def backfill_missing_purchase_snapshots(conn: sqlite3.Connection):
    """Backfill EK-Snapshots for data created before the EK feature existed.

    New consumptions always snapshot the item's EK at consumption time. Older rows from
    previous app versions can have 0.00 simply because the column did not exist yet.
    For those rows only, use the current item EK so reports do not show false zero cost.
    """
    conn.execute(
        """
        UPDATE order_lines
        SET unit_purchase_price_eur = (
            SELECT purchase_price_eur FROM items WHERE items.id = order_lines.item_id
        )
        WHERE item_id IS NOT NULL
          AND COALESCE(unit_purchase_price_eur, 0) = 0
          AND COALESCE((SELECT purchase_price_eur FROM items WHERE items.id = order_lines.item_id), 0) > 0
        """
    )
    conn.execute(
        """
        UPDATE transaction_items
        SET
            unit_purchase_price_eur = (
                SELECT purchase_price_eur FROM items WHERE items.id = transaction_items.item_id
            ),
            purchase_total_eur = quantity * (
                SELECT purchase_price_eur FROM items WHERE items.id = transaction_items.item_id
            ),
            profit_eur = total_eur - (quantity * (
                SELECT purchase_price_eur FROM items WHERE items.id = transaction_items.item_id
            ))
        WHERE item_id IS NOT NULL
          AND COALESCE(unit_purchase_price_eur, 0) = 0
          AND COALESCE((SELECT purchase_price_eur FROM items WHERE items.id = transaction_items.item_id), 0) > 0
        """
    )
    # „1 Runde“ ist ein interner Runden-Preis, kein Getränk mit eigenem EK.
    # Falls eine frühere Version dort versehentlich einen EK-Snapshot gespeichert
    # hat, wird dieser korrigiert. Der Runden-EK kommt ausschließlich aus den
    # tatsächlich abgezogenen Getränken im round_events-Bericht.
    conn.execute(
        """
        UPDATE order_lines
        SET unit_purchase_price_eur = 0
        WHERE item_name_snapshot = ?
           OR item_id IN (SELECT id FROM items WHERE name = ?)
        """,
        (ROUND_ITEM_NAME, ROUND_ITEM_NAME),
    )
    conn.execute(
        """
        UPDATE transaction_items
        SET unit_purchase_price_eur = 0,
            purchase_total_eur = 0,
            profit_eur = total_eur
        WHERE item_name_snapshot = ?
           OR item_id IN (SELECT id FROM items WHERE name = ?)
        """,
        (ROUND_ITEM_NAME, ROUND_ITEM_NAME),
    )


def ensure_settings(conn: sqlite3.Connection):
    current_admin_pin = get_setting(conn, "admin_pin")
    if current_admin_pin is None:
        set_setting(conn, "admin_pin", ENV_PIN_CODE)
    elif current_admin_pin == "1234" and ENV_PIN_FROM_ENV and ENV_PIN_CODE != "1234":
        set_setting(conn, "admin_pin", ENV_PIN_CODE)
    if get_setting(conn, "round_item_price_eur") is None:
        set_setting(conn, "round_item_price_eur", DEFAULT_ROUND_PRICE_EUR)
    if get_setting(conn, "currency") is None:
        set_setting(conn, "currency", "EUR")
    if get_setting(conn, "app_name") is None:
        set_setting(conn, "app_name", "Drink POS")
    if get_setting(conn, "show_total_on_overview") is None:
        set_setting(conn, "show_total_on_overview", "1")
    if get_setting(conn, "tally_roughness") is None:
        set_setting(conn, "tally_roughness", "4")
    if get_setting(conn, "overview_name_size_px") is None:
        set_setting(conn, "overview_name_size_px", "15.5")
    if get_setting(conn, "overview_summary_size_percent") is None:
        set_setting(conn, "overview_summary_size_percent", "100")
    if get_setting(conn, "show_summary_label_on_overview") is None:
        set_setting(conn, "show_summary_label_on_overview", "1")
    if get_setting(conn, "overview_summary_label_text") is None:
        set_setting(conn, "overview_summary_label_text", "Gesamt:")
    if get_setting(conn, "tally_size_percent") is None:
        set_setting(conn, "tally_size_percent", "100")
    if get_setting(conn, "show_sync_status") is None:
        set_setting(conn, "show_sync_status", "1")
    if get_setting(conn, "show_person_popup_total") is None:
        set_setting(conn, "show_person_popup_total", "1")
    if get_setting(conn, "sync_status_size_percent") is None:
        set_setting(conn, "sync_status_size_percent", "100")
    if get_setting(conn, "enable_delete_requests") is None:
        set_setting(conn, "enable_delete_requests", "1")
    if get_setting(conn, "app_background_color") is None:
        set_setting(conn, "app_background_color", "#f3f4f6")
    if get_setting(conn, "person_card_background_color") is None:
        set_setting(conn, "person_card_background_color", "#ffffff")
    if get_setting(conn, "person_card_border_color") is None:
        set_setting(conn, "person_card_border_color", "#bfdbfe")
    if get_setting(conn, "person_card_border_width_px") is None:
        set_setting(conn, "person_card_border_width_px", "2")
    if get_setting(conn, "person_card_gap_px") is None:
        set_setting(conn, "person_card_gap_px", "10")
    if get_setting(conn, "drink_feedback_enabled") is None:
        set_setting(conn, "drink_feedback_enabled", "1")
    if get_setting(conn, "drink_feedback_style") is None:
        set_setting(conn, "drink_feedback_style", "strong")
    if get_setting(conn, "drink_feedback_duration_ms") is None:
        set_setting(conn, "drink_feedback_duration_ms", "1400")
    if get_setting(conn, "drink_feedback_animation_intensity_percent") is None:
        set_setting(conn, "drink_feedback_animation_intensity_percent", "100")
    if get_setting(conn, "drink_feedback_position") is None:
        set_setting(conn, "drink_feedback_position", "above")
    if get_setting(conn, "drink_booking_sound_enabled") is None:
        set_setting(conn, "drink_booking_sound_enabled", "1")
    if get_setting(conn, "drink_booking_sound_preset") is None:
        set_setting(conn, "drink_booking_sound_preset", "warm")
    if get_setting(conn, "drink_celebration_mode") is None:
        set_setting(conn, "drink_celebration_mode", "condition")
    if get_setting(conn, "drink_celebration_condition_round") is None:
        set_setting(conn, "drink_celebration_condition_round", "1")
    if get_setting(conn, "drink_celebration_condition_debt") is None:
        set_setting(conn, "drink_celebration_condition_debt", "1")
    if get_setting(conn, "drink_celebration_debt_threshold_eur") is None:
        set_setting(conn, "drink_celebration_debt_threshold_eur", "50.00")
    if get_setting(conn, "drink_celebration_confetti_intensity_percent") is None:
        set_setting(conn, "drink_celebration_confetti_intensity_percent", "100")
    if get_setting(conn, "drink_celebration_sound_enabled") is None:
        set_setting(conn, "drink_celebration_sound_enabled", "1")
    if get_setting(conn, "cost_warning_enabled") is None:
        set_setting(conn, "cost_warning_enabled", "1")
    if get_setting(conn, "cost_warning_threshold_eur") is None:
        set_setting(conn, "cost_warning_threshold_eur", "30.00")
    if get_setting(conn, "cost_warning_template") is None:
        set_setting(conn, "cost_warning_template", DEFAULT_COST_WARNING_TEMPLATE)
    if get_setting(conn, "payment_reminder_enabled") is None:
        set_setting(conn, "payment_reminder_enabled", "1")
    if get_setting(conn, "payment_reminder_threshold_eur") is None:
        set_setting(conn, "payment_reminder_threshold_eur", "50.00")
    if get_setting(conn, "payment_reminder_template") is None:
        set_setting(conn, "payment_reminder_template", DEFAULT_PAYMENT_REMINDER_TEMPLATE)
    if get_setting(conn, "cost_warning_show_on_overview") is None:
        set_setting(conn, "cost_warning_show_on_overview", get_setting(conn, "cost_notice_show_on_overview", "1") or "1")
    if get_setting(conn, "cost_warning_show_in_popup") is None:
        set_setting(conn, "cost_warning_show_in_popup", get_setting(conn, "cost_notice_show_in_popup", "1") or "1")
    if get_setting(conn, "payment_reminder_show_on_overview") is None:
        set_setting(conn, "payment_reminder_show_on_overview", get_setting(conn, "cost_notice_show_on_overview", "1") or "1")
    if get_setting(conn, "payment_reminder_show_in_popup") is None:
        set_setting(conn, "payment_reminder_show_in_popup", get_setting(conn, "cost_notice_show_in_popup", "1") or "1")
    if get_setting(conn, "cost_notice_show_on_overview") is None:
        set_setting(conn, "cost_notice_show_on_overview", "1")
    if get_setting(conn, "cost_notice_show_in_popup") is None:
        set_setting(conn, "cost_notice_show_in_popup", "1")
    if get_setting(conn, "member_messages_show_on_overview") is None:
        set_setting(conn, "member_messages_show_on_overview", "1")
    if get_setting(conn, "member_messages_show_in_popup") is None:
        set_setting(conn, "member_messages_show_in_popup", "1")
    if get_setting(conn, "self_payment_enabled") is None:
        set_setting(conn, "self_payment_enabled", "0")

