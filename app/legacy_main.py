"""Legacy monolithic Drink POS application.

The new ``app.main`` module is the bootstrap entrypoint. This file preserves the
existing route handlers and helpers while the application is split into focused
modules.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from collections.abc import Iterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse

try:
    from .models.requests import (
        AddDrinkRequest,
        AdminAdjustItemRequest,
        AdminChangeRequestDecision,
        AdminItemCreate,
        AdminItemDelete,
        AdminItemUpdate,
        AdminMemberMessageArchive,
        AdminMemberMessageCreate,
        AdminPersonCreate,
        AdminPersonDelete,
        AdminPersonUpdate,
        AdminRoundRequestDecision,
        AgentBookDrinkRequest,
        AgentPersonRequest,
        AgentRoundRequest,
        CashupRequest,
        ClientEventRequest,
        EditRequestIn,
        KassaPayRequest,
        MemberMessageAckRequest,
        PayRequest,
        PinRequest,
        ReportRequest,
        RoundRequestIn,
        SelfPayRequest,
        SettingsUpdateRequest,
        StatisticsRequest,
        SumUpPairReaderRequest,
        TransactionFilterRequest,
    )
    from .services.sumup import (
        SumUpConfig,
        SumUpError,
        create_reader_checkout as sumup_create_reader_checkout,
        list_readers as sumup_list_readers,
        pair_reader as sumup_pair_reader,
        poll_checkout_status as sumup_poll_checkout_status,
        reader_status as sumup_reader_status,
    )
except ImportError:
    from models.requests import (
        AddDrinkRequest,
        AdminAdjustItemRequest,
        AdminChangeRequestDecision,
        AdminItemCreate,
        AdminItemDelete,
        AdminItemUpdate,
        AdminMemberMessageArchive,
        AdminMemberMessageCreate,
        AdminPersonCreate,
        AdminPersonDelete,
        AdminPersonUpdate,
        AdminRoundRequestDecision,
        AgentBookDrinkRequest,
        AgentPersonRequest,
        AgentRoundRequest,
        CashupRequest,
        ClientEventRequest,
        EditRequestIn,
        KassaPayRequest,
        MemberMessageAckRequest,
        PayRequest,
        PinRequest,
        ReportRequest,
        RoundRequestIn,
        SelfPayRequest,
        SettingsUpdateRequest,
        StatisticsRequest,
        SumUpPairReaderRequest,
        TransactionFilterRequest,
    )
    from services.sumup import (
        SumUpConfig,
        SumUpError,
        create_reader_checkout as sumup_create_reader_checkout,
        list_readers as sumup_list_readers,
        pair_reader as sumup_pair_reader,
        poll_checkout_status as sumup_poll_checkout_status,
        reader_status as sumup_reader_status,
    )

try:
    from .core.build import build_info
    from .core import security as security_service
    from .db import schema as schema_service
    from .services import messages as message_service
    from .services.statistics import log_transaction, log_transaction_item
    from .services.sync import get_sync_state
    from .utils.formatting import (
        decimal_comma,
        eur_text,
        normalize_decimal_text,
        normalize_for_sort,
        normalize_hex_color,
        short_label_from_name,
    )
    from .utils.helpers import (
        get_setting,
        now_text,
        row_get,
        set_setting,
        setting_bool,
        today_text,
    )
    from .utils.parsing import display_name, split_name
except ImportError:
    from core.build import build_info
    import core.security as security_service
    import db.schema as schema_service
    from services import messages as message_service
    from services.statistics import log_transaction, log_transaction_item
    from services.sync import get_sync_state
    from utils.formatting import (
        decimal_comma,
        eur_text,
        normalize_decimal_text,
        normalize_for_sort,
        normalize_hex_color,
        short_label_from_name,
    )
    from utils.helpers import (
        get_setting,
        now_text,
        row_get,
        set_setting,
        setting_bool,
        today_text,
    )
    from utils.parsing import display_name, split_name

APP_ENV = os.getenv("DRINK_POS_ENV", "development").strip().lower()
RAW_ENV_PIN_CODE = os.getenv("DRINK_POS_PIN")
ENV_PIN_CODE = (RAW_ENV_PIN_CODE or "1234").strip() or "1234"
ENV_PIN_FROM_ENV = RAW_ENV_PIN_CODE is not None and RAW_ENV_PIN_CODE.strip() != ""
AGENT_API_TOKEN = os.getenv("DRINK_POS_AGENT_TOKEN", "").strip()
APP_DIR = Path(__file__).resolve().parent
TEST_PAYMENT_APP_ENVS = {"test", "testing"}
TEST_PAYMENT_PROVIDER_ENVS = {"development", "dev", "local", *TEST_PAYMENT_APP_ENVS}
TEST_PAYMENT_PROVIDERS = {"test", "mock", "demo"}
TEST_PAYMENT_FLAG_ENV = "DRINK_POS_ALLOW_TEST_CARD_PAYMENTS"


def default_db_path_for_env(env: str) -> str:
    """Use a separate database automatically for development/test operation."""
    normalized = (env or "development").strip().lower()
    if normalized in {"prod", "production"}:
        return "/app/data/drink_pos.db"
    return "/app/data/drink_pos_dev.db"


DB_PATH = os.getenv("DRINK_POS_DB") or default_db_path_for_env(APP_ENV)
DB_PATH_SOURCE = "DRINK_POS_DB" if os.getenv("DRINK_POS_DB") else "environment-default"
DB_TIMEOUT_SECONDS = 15
DB_BUSY_TIMEOUT_MS = 15000
DEFAULT_MESSAGES_PATH = message_service.DEFAULT_MESSAGES_PATH
MESSAGES_PATH = message_service.runtime_messages_path(DB_PATH)
ADMIN_LOGIN_RATE_WINDOW_SECONDS = 300
ADMIN_LOGIN_RATE_LIMIT = 8
ADMIN_LOGIN_ATTEMPTS: dict[str, list[float]] = {}

DEFAULT_ITEMS = [
    {"name": "Bier gross", "short_label": "Gross", "price_eur": 2.50, "purchase_price_eur": 1.40, "admin_only": False},
    {"name": "Bier klein", "short_label": "Klein", "price_eur": 1.80, "purchase_price_eur": 1.00, "admin_only": False},
    {"name": "Limo", "short_label": "Limo", "price_eur": 1.00, "purchase_price_eur": 0.45, "admin_only": False},
]

ROUND_ITEM_NAME = "1 Runde"
ROUND_ITEM_SHORT = "Runde"
DEFAULT_ROUND_PRICE_EUR = "10.00"
DEFAULT_COST_WARNING_TEMPLATE = "Offen: {betrag}. Unteres Limit {unteres_limit} erreicht."
DEFAULT_PAYMENT_REMINDER_TEMPLATE = "Offen: {betrag}. Oberes Limit {oberes_limit} erreicht. Bitte bei Gelegenheit bezahlen."
SYSTEM_ITEM_NAMES = {ROUND_ITEM_NAME}
PAID_TRANSACTION_TYPES = ("PAID_CASH", "PAID_SUMUP")
PAID_TRANSACTION_KINDS = ("PAID_CASH", "PAID_SUMUP")
CARD_PAYMENT_FEE_RATE_PERCENT = 3
CARD_PAYMENT_MIN_FEE_CENTS = 20
CARD_PAYMENT_ROUNDING_STEPS = {
    "none": 1,
    "euro": 100,
    "five": 500,
    "ten": 1000,
}


def is_system_item_name(name: str | None) -> bool:
    return (name or "").strip().lower() in {item.lower() for item in SYSTEM_ITEM_NAMES}

DEFAULT_NAMES = [
    "Demo Person 01",
    "Demo Person 02",
    "Demo Person 03",
    "Demo Person 04",
    "Demo Person 05",
    "Demo Person 06",
    "Demo Person 07",
    "Demo Person 08",
    "Demo Person 09",
    "Demo Person 10",
    "Demo Person 11",
    "Demo Person 12",
]

app = FastAPI(title="Drink POS")


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def is_production() -> bool:
    return APP_ENV in {"prod", "production"}


def database_info() -> dict:
    info = {
        "source": DB_PATH_SOURCE,
        "profile": "production" if is_production() else "development",
    }
    info["path"] = "hidden" if is_production() else DB_PATH
    return info


def ensure_messages_file() -> None:
    """Compatibility wrapper for the message catalog service."""

    message_service.ensure_messages_file(DB_PATH)


def load_message_catalog() -> dict:
    """Compatibility wrapper for the message catalog service."""

    return message_service.load_message_catalog(DB_PATH)


def message_text(key: str, default: str = "", **values) -> str:
    """Compatibility wrapper for the message catalog service."""

    return message_service.message_text(key, default, db_path=DB_PATH, values=values)


def configured_admin_pin(conn: sqlite3.Connection) -> str:
    """Compatibility wrapper for the admin PIN security service."""

    return security_service.configured_admin_pin(conn, ENV_PIN_CODE)


def ensure_admin_login_allowed(conn: sqlite3.Connection) -> None:
    """Compatibility wrapper for the admin PIN security service."""

    security_service.ensure_admin_login_allowed(conn, production=is_production(), env_pin=ENV_PIN_CODE)


def require_pin(conn: sqlite3.Connection, pin: str) -> None:
    """Compatibility wrapper for the admin PIN security service."""

    security_service.require_pin(conn, pin, production=is_production(), env_pin=ENV_PIN_CODE)


def configure_connection(conn: sqlite3.Connection) -> sqlite3.Connection:
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT_MS}")
    return conn


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    conn = configure_connection(sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT_SECONDS))
    try:
        yield conn
    finally:
        conn.close()


def clean_notice_template(value: str | None, default: str) -> str:
    text = " ".join(str(value or "").strip().split())
    if not text:
        return default
    return text[:300]


def parse_decimal_value(value, field_name: str = "Wert") -> float:
    """Accept decimal values with either German comma or technical dot notation."""
    if value is None:
        raise HTTPException(status_code=400, detail=f"{field_name} fehlt")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("€", "").replace(" ", "").replace("\u00a0", "")
    if not text:
        raise HTTPException(status_code=400, detail=f"{field_name} fehlt")
    if "," in text and "." in text:
        # German thousands + decimal: 1.234,56 -> 1234.56
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            # Technical thousands + decimal: 1,234.56 -> 1234.56
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{field_name} ist keine gültige Zahl")


# ---------------------------------------------------------------------------
# Database setup + migration from prototype tables
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Database setup + migration from prototype tables
# ---------------------------------------------------------------------------

def _configure_schema_runtime() -> None:
    schema_service.configure_runtime(DB_PATH, ENV_PIN_CODE, ENV_PIN_FROM_ENV, get_conn)


def init_db():
    _configure_schema_runtime()
    return schema_service.init_db()


def ensure_indexes(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.ensure_indexes(conn)


def migrate_people(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.migrate_people(conn)


def is_placeholder_name(name: str) -> bool:
    return schema_service.is_placeholder_name(name)


def ensure_default_people(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.ensure_default_people(conn)


def migrate_items(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.migrate_items(conn)


def ensure_default_items(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.ensure_default_items(conn)


def ensure_round_item(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.ensure_round_item(conn)


def migrate_old_orders(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.migrate_old_orders(conn)


def backfill_missing_purchase_snapshots(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.backfill_missing_purchase_snapshots(conn)


def ensure_settings(conn: sqlite3.Connection):
    _configure_schema_runtime()
    return schema_service.ensure_settings(conn)


@app.on_event("startup")
def startup():
    init_db()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_person(conn: sqlite3.Connection, person_id: int, allow_archived: bool = True):
    sql = "SELECT * FROM people WHERE id = ?"
    if not allow_archived:
        sql += " AND active = 1 AND archived_at IS NULL"
    row = conn.execute(sql, (person_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Person nicht gefunden")
    return row


def get_item_by_id_or_name(conn: sqlite3.Connection, item_id: int | None, name: str | None):
    if item_id is not None:
        item = conn.execute("SELECT * FROM items WHERE id = ? AND archived_at IS NULL", (item_id,)).fetchone()
    elif name:
        item = conn.execute("SELECT * FROM items WHERE name = ? AND archived_at IS NULL", (name.strip(),)).fetchone()
    else:
        item = None
    if not item:
        raise HTTPException(status_code=400, detail="Artikel nicht gefunden")
    return item


def get_items(conn: sqlite3.Connection, include_archived: bool = False):
    where = ""
    if not include_archived:
        where = "WHERE archived_at IS NULL"
    rows = conn.execute(
        f"""
        SELECT id, name, short_label, price_eur, purchase_price_eur, active, admin_only, sort_order, archived_at
        FROM items
        {where}
        ORDER BY archived_at IS NOT NULL ASC, active DESC, sort_order ASC, name ASC
        """
    ).fetchall()
    return [
        {
            "id": row["id"],
            "name": row["name"],
            "short_label": row["short_label"],
            "price": round(float(row["price_eur"]), 2),
            "price_eur": round(float(row["price_eur"]), 2),
            "purchase_price": round(float(row["purchase_price_eur"]), 2),
            "purchase_price_eur": round(float(row["purchase_price_eur"]), 2),
            "active": bool(row["active"]),
            "admin_only": bool(row["admin_only"]),
            "sort_order": int(row["sort_order"]),
            "archived": row["archived_at"] is not None,
            "system_item": is_system_item_name(row["name"]),
            "can_user_add": bool(row["active"] and not row["admin_only"] and row["archived_at"] is None),
            "can_admin_add": row["archived_at"] is None,
        }
        for row in rows
    ]


def get_open_lines(conn: sqlite3.Connection, person_id: int | None = None):
    params: list[object] = []
    where = ["ol.quantity > 0"]
    if person_id is not None:
        where.append("ol.person_id = ?")
        params.append(person_id)
    rows = conn.execute(
        f"""
        SELECT
            ol.*,
            i.name AS current_item_name,
            i.short_label AS current_item_short_label,
            i.admin_only AS current_admin_only,
            i.sort_order AS current_sort_order,
            i.active AS item_active,
            i.archived_at AS item_archived_at,
            COALESCE((
                SELECT SUM(cr.quantity_to_remove)
                FROM change_requests cr
                WHERE cr.order_line_id = ol.id AND cr.status = 'PENDING'
            ), 0) AS pending_remove
        FROM order_lines ol
        LEFT JOIN items i ON i.id = ol.item_id
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(i.sort_order, 9999) ASC, ol.consumed_date ASC, ol.created_at ASC, ol.id ASC
        """,
        params,
    ).fetchall()
    return rows


def serialize_open_line(row: sqlite3.Row) -> dict:
    qty = int(row["quantity"])
    price = float(row["unit_price_eur"])
    pending = int(row["pending_remove"] or 0)
    current_name = row["current_item_name"] or row["item_name_snapshot"]
    current_short = row["current_item_short_label"] or row["item_short_label_snapshot"]
    admin_only = bool(row["current_admin_only"] if row["current_admin_only"] is not None else row["admin_only_snapshot"])
    snapshot_name = row["item_name_snapshot"]
    snapshot_short = row["item_short_label_snapshot"]
    renamed = current_name != snapshot_name or current_short != snapshot_short
    round_line = is_system_item_name(snapshot_name)
    can_request_delete = (not admin_only or round_line) and max(0, qty - pending) > 0
    return {
        "line_id": row["id"],
        "id": row["id"],
        "item_id": row["item_id"],
        "name": current_name,
        "short_label": current_short,
        "snapshot_name": snapshot_name,
        "snapshot_short_label": snapshot_short,
        "label_changed_since_consumption": bool(renamed),
        "quantity": qty,
        "price": round(price, 2),
        "unit_price_eur": round(price, 2),
        "unit_purchase_price_eur": round(float(row["unit_purchase_price_eur"] if "unit_purchase_price_eur" in row.keys() else 0), 2),
        "subtotal": round(qty * price, 2),
        "pending_remove": pending,
        "available_for_request": max(0, qty - pending),
        "admin_only": admin_only,
        "can_user_request_delete": can_request_delete,
        "active": bool(row["item_active"]) if row["item_active"] is not None else False,
        "item_archived": row["item_archived_at"] is not None,
        "consumed_date": row["consumed_date"],
        "event_open": bool(row["event_open"]),
    }


def get_pending_requests_for_person(conn: sqlite3.Connection, person_id: int):
    rows = conn.execute(
        """
        SELECT
            cr.id,
            cr.person_id,
            cr.order_line_id,
            cr.item_id,
            cr.quantity_to_remove,
            cr.reason,
            cr.status,
            cr.requested_at,
            COALESCE(i.name, ol.item_name_snapshot) AS display_item_name,
            COALESCE(i.short_label, ol.item_short_label_snapshot) AS display_item_short_label,
            ol.item_name_snapshot,
            ol.item_short_label_snapshot,
            ol.unit_price_eur,
            ol.quantity AS current_quantity
        FROM change_requests cr
        JOIN order_lines ol ON ol.id = cr.order_line_id
        LEFT JOIN items i ON i.id = ol.item_id
        WHERE cr.person_id = ? AND cr.status = 'PENDING'
        ORDER BY cr.id ASC
        """,
        (person_id,),
    ).fetchall()
    result = [
        {
            "id": row["id"],
            "raw_id": row["id"],
            "request_kind": "DELETE",
            "person_id": row["person_id"],
            "line_id": row["order_line_id"],
            "item_id": row["item_id"],
            "drink": row["display_item_name"],
            "item": row["display_item_name"],
            "short_label": row["display_item_short_label"],
            "snapshot_item": row["item_name_snapshot"],
            "snapshot_short_label": row["item_short_label_snapshot"],
            "quantity_to_remove": int(row["quantity_to_remove"]),
            "delta": -int(row["quantity_to_remove"]),
            "reason": row["reason"],
            "requested_at": row["requested_at"],
            "current_quantity": int(row["current_quantity"]),
            "unit_price_eur": round(float(row["unit_price_eur"]), 2),
        }
        for row in rows
    ]

    round_rows = conn.execute(
        """
        SELECT
            rr.id,
            rr.person_id,
            rr.item_id,
            rr.quantity,
            rr.reason,
            rr.requested_at,
            COALESCE(i.name, ?) AS item_name,
            COALESCE(i.short_label, ?) AS short_label,
            COALESCE(i.price_eur, 0) AS price_eur
        FROM round_requests rr
        LEFT JOIN items i ON i.id = rr.item_id
        WHERE rr.person_id = ? AND rr.status = 'PENDING'
        ORDER BY rr.id ASC
        """,
        (ROUND_ITEM_NAME, ROUND_ITEM_SHORT, person_id),
    ).fetchall()
    for row in round_rows:
        result.append(
            {
                "id": f"round:{row['id']}",
                "raw_id": row["id"],
                "request_kind": "ROUND_ADD",
                "person_id": row["person_id"],
                "item_id": row["item_id"],
                "drink": row["item_name"],
                "item": row["item_name"],
                "short_label": row["short_label"],
                "quantity_to_add": int(row["quantity"]),
                "delta": int(row["quantity"]),
                "reason": row["reason"],
                "requested_at": row["requested_at"],
                "unit_price_eur": round(float(row["price_eur"]), 2),
            }
        )
    return result


def get_member_messages_for_person(conn: sqlite3.Connection, person_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            mm.id,
            mm.title,
            mm.message,
            mm.created_at
        FROM member_message_recipients mmr
        JOIN member_messages mm ON mm.id = mmr.message_id
        WHERE mmr.person_id = ?
          AND mm.active = 1
          AND mm.archived_at IS NULL
          AND mmr.acknowledged_at IS NULL
        ORDER BY mm.created_at DESC, mm.id DESC
        """,
        (person_id,),
    ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"] or "Nachricht",
            "message": row["message"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_admin_member_messages(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        """
        SELECT
            mm.id,
            mm.title,
            mm.message,
            mm.active,
            mm.created_at,
            mm.archived_at,
            COUNT(mmr.person_id) AS recipient_count,
            COALESCE(SUM(CASE WHEN mmr.acknowledged_at IS NOT NULL THEN 1 ELSE 0 END), 0) AS acknowledged_count
        FROM member_messages mm
        LEFT JOIN member_message_recipients mmr ON mmr.message_id = mm.id
        WHERE mm.active = 1
          AND mm.archived_at IS NULL
        GROUP BY mm.id
        ORDER BY mm.created_at DESC, mm.id DESC
        LIMIT 50
        """
    ).fetchall()
    messages = []
    for row in rows:
        recipients = conn.execute(
            """
            SELECT
                p.id,
                p.name,
                p.first_name,
                p.last_name,
                mmr.acknowledged_at
            FROM member_message_recipients mmr
            JOIN people p ON p.id = mmr.person_id
            WHERE mmr.message_id = ?
            ORDER BY p.last_name COLLATE NOCASE ASC, p.first_name COLLATE NOCASE ASC, p.name COLLATE NOCASE ASC
            """,
            (row["id"],),
        ).fetchall()
        messages.append(
            {
                "id": row["id"],
                "title": row["title"] or "Nachricht",
                "message": row["message"],
                "active": bool(row["active"]) and row["archived_at"] is None,
                "created_at": row["created_at"],
                "archived_at": row["archived_at"],
                "recipient_count": int(row["recipient_count"] or 0),
                "acknowledged_count": int(row["acknowledged_count"] or 0),
                "recipients": [
                    {
                        "id": recipient["id"],
                        "name": display_name(recipient["first_name"], recipient["last_name"]) or recipient["name"],
                        "acknowledged_at": recipient["acknowledged_at"],
                    }
                    for recipient in recipients
                ],
            }
        )
    return messages


def archive_member_message_if_completed(conn: sqlite3.Connection, message_id: int) -> bool:
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
    row = conn.execute(
        "SELECT id, title, archived_at FROM member_messages WHERE id = ? AND active = 1",
        (message_id,),
    ).fetchone()
    if not row or row["archived_at"] is not None:
        return False
    conn.execute(
        """
        UPDATE member_messages
        SET active = 0, archived_at = ?
        WHERE id = ?
        """,
        (now_text(), message_id),
    )
    log_transaction(conn, None, "MEMBER_MESSAGE_ARCHIVED", 0, f"Nachricht automatisch archiviert: #{message_id} {row['title'] or ''}".strip())
    return True


def person_total_from_lines(lines: list[sqlite3.Row]) -> float:
    return round(sum(int(line["quantity"]) * float(line["unit_price_eur"]) for line in lines), 2)


def open_lines_payment_revision(lines: list[sqlite3.Row], pending_count: int = 0) -> str:
    parts = [
        f"{int(line['id'])}:{int(line['quantity'])}:{line['updated_at']}:{int(line['event_open'])}"
        for line in sorted(lines, key=lambda row: int(row["id"]))
    ]
    raw = f"pending:{int(pending_count)}|" + "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def make_payment_detail_lines(lines: list[sqlite3.Row]) -> list[dict]:
    grouped: dict[tuple, dict] = {}
    for line in lines:
        qty = int(line["quantity"] or 0)
        if qty <= 0:
            continue
        price = round(float(line["unit_price_eur"] or 0), 2)
        purchase = round(float(line["unit_purchase_price_eur"] if "unit_purchase_price_eur" in line.keys() else 0), 2)
        key = (
            line["item_id"],
            line["item_name_snapshot"],
            line["item_short_label_snapshot"],
            price,
            purchase,
        )
        if key not in grouped:
            grouped[key] = {
                "item_id": line["item_id"],
                "item": line["item_name_snapshot"],
                "short_label": line["item_short_label_snapshot"],
                "quantity": 0,
                "unit_price_eur": price,
                "unit_purchase_price_eur": purchase,
                "subtotal_eur": 0.0,
                "line_ids": [],
            }
        grouped[key]["quantity"] += qty
        grouped[key]["subtotal_eur"] = rounded_money(grouped[key]["quantity"] * price)
        grouped[key]["line_ids"].append(int(line["id"]))
    return sorted(
        grouped.values(),
        key=lambda item: (str(item["item"]).lower(), float(item["unit_price_eur"])),
    )


def is_round_order_line(line: sqlite3.Row | dict) -> bool:
    return is_system_item_name(str(row_get(line, "item_name_snapshot", "") or ""))


def current_event_round_units(conn: sqlite3.Connection) -> list[dict]:
    round_rows = conn.execute(
        """
        SELECT
            ol.*,
            p.name,
            p.first_name,
            p.last_name,
            COALESCE((
                SELECT SUM(cr.quantity_to_remove)
                FROM change_requests cr
                WHERE cr.order_line_id = ol.id AND cr.status = 'PENDING'
            ), 0) AS pending_remove
        FROM order_lines ol
        LEFT JOIN people p ON p.id = ol.person_id
        LEFT JOIN items i ON i.id = ol.item_id
        WHERE ol.quantity > 0
          AND ol.event_open = 1
          AND (ol.item_name_snapshot = ? OR i.name = ?)
        ORDER BY ol.consumed_date ASC, ol.created_at ASC, ol.id ASC
        """,
        (ROUND_ITEM_NAME, ROUND_ITEM_NAME),
    ).fetchall()
    units: list[dict] = []
    for row in round_rows:
        qty = max(0, int(row["quantity"]) - int(row["pending_remove"] or 0))
        if qty <= 0:
            continue
        payer_name = display_name(row["first_name"], row["last_name"]) or row["name"] or "Unbekannt"
        price = rounded_money(float(row["unit_price_eur"] or 0))
        for _ in range(qty):
            units.append(
                {
                    "source": "open_line",
                    "round_index": len(units) + 1,
                    "payer_person_id": int(row["person_id"]),
                    "payer_name": payer_name,
                    "round_price_eur": price,
                    "order_line_id": int(row["id"]),
                    "paid_round_unit_id": None,
                    "already_paid": False,
                    "deductions": [],
                }
            )

    paid_rows = conn.execute(
        """
        SELECT pru.*, p.name, p.first_name, p.last_name
        FROM paid_round_units pru
        LEFT JOIN people p ON p.id = pru.payer_person_id
        WHERE pru.event_open = 1
        ORDER BY pru.created_at ASC, pru.id ASC
        """
    ).fetchall()
    for row in paid_rows:
        fallback_name = display_name(row["first_name"], row["last_name"]) or row["name"] or "Unbekannt"
        units.append(
            {
                "source": "paid_unit",
                "round_index": len(units) + 1,
                "payer_person_id": int(row["payer_person_id"]),
                "payer_name": row["payer_name_snapshot"] or fallback_name,
                "round_price_eur": rounded_money(float(row["round_price_eur"] or 0)),
                "order_line_id": row["source_order_line_id"],
                "paid_round_unit_id": int(row["id"]),
                "already_paid": True,
                "deductions": [],
            }
        )
    return units


def current_event_rounds_revision(conn: sqlite3.Connection) -> str:
    parts = []
    for unit in current_event_round_units(conn):
        source_id = unit["paid_round_unit_id"] if unit["source"] == "paid_unit" else unit["order_line_id"]
        parts.append(
            f"{unit['source']}:{source_id}:{unit['payer_person_id']}:{unit['round_price_eur']}"
        )
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def payment_revision(conn: sqlite3.Connection, lines: list[sqlite3.Row], pending_count: int = 0) -> str:
    raw = f"{open_lines_payment_revision(lines, pending_count)}|rounds:{current_event_rounds_revision(conn)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def empty_person_round_deduction_plan(rounds_count: int = 0) -> dict:
    return {
        "rounds_count": int(rounds_count or 0),
        "deducted_items": 0,
        "deducted_vk_eur": 0.0,
        "deducted_purchase_eur": 0.0,
        "deductions": [],
    }


def build_person_round_deduction_plan(conn: sqlite3.Connection, person_id: int) -> dict:
    round_units = current_event_round_units(conn)
    if not round_units:
        return empty_person_round_deduction_plan()

    drink_rows = conn.execute(
        """
        SELECT
            ol.*,
            p.name,
            p.first_name,
            p.last_name,
            COALESCE((
                SELECT SUM(cr.quantity_to_remove)
                FROM change_requests cr
                WHERE cr.order_line_id = ol.id AND cr.status = 'PENDING'
            ), 0) AS pending_remove
        FROM order_lines ol
        JOIN people p ON p.id = ol.person_id
        LEFT JOIN items i ON i.id = ol.item_id
        WHERE ol.person_id = ?
          AND ol.quantity > 0
          AND ol.event_open = 1
          AND COALESCE(ol.admin_only_snapshot, 0) = 0
          AND ol.item_name_snapshot <> ?
          AND COALESCE(i.name, '') <> ?
        ORDER BY ol.unit_price_eur ASC, ol.consumed_date ASC, ol.created_at ASC, ol.id ASC
        """,
        (person_id, ROUND_ITEM_NAME, ROUND_ITEM_NAME),
    ).fetchall()
    remaining = {
        int(row["id"]): max(0, int(row["quantity"]) - int(row["pending_remove"] or 0))
        for row in drink_rows
    }
    deductions = []
    for round_unit in round_units:
        chosen = None
        for row in drink_rows:
            if remaining.get(int(row["id"]), 0) > 0:
                chosen = row
                break
        if not chosen:
            continue
        remaining[int(chosen["id"])] -= 1
        price = rounded_money(float(chosen["unit_price_eur"] or 0))
        purchase = rounded_money(float(chosen["unit_purchase_price_eur"] if "unit_purchase_price_eur" in chosen.keys() else 0))
        deductions.append(
            {
                "round_index": round_unit["round_index"],
                "payer_name": round_unit["payer_name"],
                "person_id": int(chosen["person_id"]),
                "name": display_name(chosen["first_name"], chosen["last_name"]) or chosen["name"] or "Unbekannt",
                "line_id": int(chosen["id"]),
                "item_id": chosen["item_id"],
                "item": chosen["item_name_snapshot"],
                "short_label": chosen["item_short_label_snapshot"],
                "quantity": 1,
                "unit_price_eur": price,
                "unit_purchase_price_eur": purchase,
                "subtotal_eur": price,
                "purchase_total_eur": purchase,
            }
        )

    deducted_vk = rounded_money(sum(float(item["subtotal_eur"]) for item in deductions))
    deducted_purchase = rounded_money(sum(float(item["purchase_total_eur"]) for item in deductions))
    return {
        "rounds_count": len(round_units),
        "deducted_items": len(deductions),
        "deducted_vk_eur": deducted_vk,
        "deducted_purchase_eur": deducted_purchase,
        "deductions": sorted(deductions, key=lambda item: (float(item["unit_price_eur"]), str(item["item"]).lower(), int(item["line_id"]))),
    }


def payment_total_after_round_deductions(lines: list[sqlite3.Row], plan: dict) -> float:
    return max(0.0, rounded_money(person_total_from_lines(lines) - float(plan.get("deducted_vk_eur", 0) or 0)))


def no_payable_total_detail() -> str:
    return "Keine Zahlung noetig; offene Posten werden durch Rundenabzug ausgeglichen."


def has_payable_total_after_round_deductions(lines: list[sqlite3.Row], plan: dict, pending_count: int = 0) -> bool:
    return bool(lines) and int(pending_count or 0) == 0 and payment_total_after_round_deductions(lines, plan) > 0


def make_payment_detail_lines_with_round_deductions(lines: list[sqlite3.Row], plan: dict) -> list[dict]:
    details = make_payment_detail_lines(lines)
    deduction_groups: dict[tuple, dict] = {}
    for item in plan.get("deductions", []):
        price = rounded_money(float(item["unit_price_eur"] or 0))
        purchase = rounded_money(float(item["unit_purchase_price_eur"] or 0))
        key = (item.get("item_id"), item["item"], item["short_label"], price, purchase)
        if key not in deduction_groups:
            deduction_groups[key] = {
                "item_id": item.get("item_id"),
                "item": f"Rundenabzug: {item['item']}",
                "short_label": item["short_label"],
                "quantity": 0,
                "unit_price_eur": price,
                "unit_purchase_price_eur": purchase,
                "subtotal_eur": 0.0,
                "line_ids": [],
                "is_round_deduction": True,
            }
        deduction_groups[key]["quantity"] -= 1
        deduction_groups[key]["subtotal_eur"] = rounded_money(deduction_groups[key]["subtotal_eur"] - price)
        deduction_groups[key]["line_ids"].append(int(item["line_id"]))
    deductions = sorted(
        deduction_groups.values(),
        key=lambda item: (float(item["unit_price_eur"]), str(item["item"]).lower(), min(item["line_ids"] or [0])),
    )
    return details + deductions


def validate_round_deductions_are_current(conn: sqlite3.Connection, deductions: list[dict]):
    if not deductions:
        return
    by_line: dict[int, int] = {}
    expected: dict[int, dict] = {}
    for item in deductions:
        line_id = int(item["line_id"])
        by_line[line_id] = by_line.get(line_id, 0) + 1
        expected[line_id] = item
    placeholders = ",".join("?" for _ in by_line)
    rows = conn.execute(
        f"""
        SELECT
            ol.*,
            COALESCE((
                SELECT SUM(cr.quantity_to_remove)
                FROM change_requests cr
                WHERE cr.order_line_id = ol.id AND cr.status = 'PENDING'
            ), 0) AS pending_remove
        FROM order_lines ol
        WHERE ol.id IN ({placeholders})
        """,
        list(by_line.keys()),
    ).fetchall()
    rows_by_id = {int(row["id"]): row for row in rows}
    for line_id, needed in by_line.items():
        row = rows_by_id.get(line_id)
        item = expected[line_id]
        if not row:
            raise HTTPException(status_code=409, detail="Rundenabzug nicht mehr aktuell: Posten wurde bereits entfernt")
        available = max(0, int(row["quantity"] or 0) - int(row["pending_remove"] or 0))
        if not bool(row["event_open"]):
            raise HTTPException(status_code=409, detail="Rundenabzug nicht mehr aktuell: Posten wurde bereits beim Kassensturz geschlossen")
        if is_round_order_line(row) or bool(row["admin_only_snapshot"]):
            raise HTTPException(status_code=409, detail="Rundenabzug darf nur normale offene Getraenke entfernen")
        if available < needed:
            raise HTTPException(status_code=409, detail="Rundenabzug nicht mehr aktuell: Posten wurde bereits entfernt")
        if row["item_name_snapshot"] != item["item"] or rounded_money(float(row["unit_price_eur"] or 0)) != rounded_money(float(item["unit_price_eur"] or 0)):
            raise HTTPException(status_code=409, detail="Rundenabzug nicht mehr aktuell: Artikelstand hat sich geaendert")


def apply_person_round_deductions(
    conn: sqlite3.Connection,
    person_id: int,
    plan: dict,
    context: str,
    allow_session_id: int | None = None,
) -> int | None:
    deductions = list(plan.get("deductions") or [])
    if not deductions:
        return None
    validate_round_deductions_are_current(conn, deductions)
    deducted_vk = rounded_money(sum(float(item["subtotal_eur"]) for item in deductions))
    deducted_purchase = rounded_money(sum(float(item["purchase_total_eur"]) for item in deductions))
    details_main = " | ".join(f"{item['name']}: -1x {item['item']}" for item in deductions)
    tx_id = log_transaction(
        conn,
        None,
        "ROUND_DEDUCTED",
        deducted_vk,
        f"{context}; vor Zahlung abgezogen: {details_main}",
    )
    for item in deductions:
        _, actual = remove_from_order_line(conn, int(item["line_id"]), 1, allow_session_id=allow_session_id)
        if actual != 1:
            raise HTTPException(status_code=409, detail="Rundenabzug konnte nicht konsistent ausgefuehrt werden")
        log_transaction_item(conn, tx_id, int(item["person_id"]), {
            "item_id": item["item_id"],
            "item_name_snapshot": item["item"],
            "item_short_label_snapshot": item["short_label"],
            "unit_price_eur": item["unit_price_eur"],
            "unit_purchase_price_eur": item["unit_purchase_price_eur"],
        }, -1, "ROUND_DEDUCTED")
    conn.execute(
        """
        INSERT INTO round_events (
            transaction_id, timestamp, round_price_eur, deducted_vk_eur, deducted_purchase_eur,
            profit_vs_purchase_eur, profit_vs_retail_eur, details
        ) VALUES (?, ?, 0, ?, ?, ?, ?, ?)
        """,
        (
            tx_id,
            now_text(),
            deducted_vk,
            deducted_purchase,
            -deducted_purchase,
            -deducted_vk,
            f"Vor Zahlung abgezogen: {details_main}",
        ),
    )
    return tx_id


def preserve_paid_round_units(
    conn: sqlite3.Connection,
    person: sqlite3.Row,
    lines: list[sqlite3.Row],
    payment_transaction_id: int,
):
    payer_name = display_name(person["first_name"], person["last_name"]) or person["name"] or "Unbekannt"
    rows = []
    for line in lines:
        if not bool(line["event_open"]) or not is_round_order_line(line):
            continue
        qty = max(0, int(line["quantity"] or 0))
        price = rounded_money(float(line["unit_price_eur"] or 0))
        rows.extend(
            (
                int(line["id"]),
                int(person["id"]),
                payer_name,
                price,
                int(payment_transaction_id),
                1,
                now_text(),
            )
            for _ in range(qty)
        )
    if rows:
        conn.executemany(
            """
            INSERT INTO paid_round_units (
                source_order_line_id, payer_person_id, payer_name_snapshot, round_price_eur,
                payment_transaction_id, event_open, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def kassa_history_timestamp_labels(timestamp: str | None) -> tuple[str, str, str]:
    raw = str(timestamp or "")
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
        return parsed.strftime("%d.%m"), parsed.strftime("%H:%M"), parsed.strftime("%d.%m, %H:%M")
    except ValueError:
        date_label = raw
        time_label = ""
        if len(raw) >= 16 and raw[4:5] == "-" and raw[7:8] == "-":
            date_label = f"{raw[8:10]}.{raw[5:7]}"
            time_label = raw[11:16]
        return date_label, time_label, f"{date_label}, {time_label}".rstrip(", ")


def make_kassa_person_history(conn: sqlite3.Connection, person_id: int, limit: int = 200) -> list[dict]:
    def history_key(row: sqlite3.Row | dict) -> tuple[object, str, str]:
        return (
            row_get(row, "item_id"),
            str(row_get(row, "item_name_snapshot", "") or ""),
            str(row_get(row, "item_short_label_snapshot", "") or ""),
        )

    def history_entry(row: sqlite3.Row, quantity: int, type_label: str, direction: str) -> dict:
        date_label, time_label, timestamp_label = kassa_history_timestamp_labels(row["timestamp"])
        return {
            "id": int(row["id"]),
            "transaction_id": int(row["transaction_id"]),
            "type": row["kind"],
            "type_label": type_label,
            "direction": direction,
            "timestamp": row["timestamp"],
            "date_label": date_label,
            "time_label": time_label,
            "timestamp_label": timestamp_label,
            "product": row["item_name_snapshot"],
            "short_label": row["item_short_label_snapshot"],
            "quantity": quantity,
            "quantity_label": f"{quantity:+d}x",
        }

    last_payment = conn.execute(
        """
        SELECT id, type, timestamp
        FROM transactions
        WHERE person_id = ?
          AND type IN ('PAID_CASH', 'PAID_SUMUP')
        ORDER BY id DESC
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()
    item_where = ""
    params: list[object] = [person_id]
    if last_payment:
        item_where = "AND transaction_id > ?"
        params.append(int(last_payment["id"]))
    params.append(max(1, min(500, int(limit or 200))))

    rows = conn.execute(
        f"""
        SELECT id, transaction_id, person_id, item_id, kind, timestamp, item_name_snapshot, item_short_label_snapshot, quantity
        FROM transaction_items
        WHERE person_id = ?
          AND kind IN ('CONSUME', 'ROUND_DEDUCTED', 'ROUND_REQUEST_APPROVED')
          {item_where}
        ORDER BY timestamp DESC, id DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    correction_where = ""
    correction_params: list[object] = [person_id]
    if last_payment:
        correction_where = "AND cr.decided_at > ?"
        correction_params.append(last_payment["timestamp"])
    correction_rows = conn.execute(
        f"""
        SELECT
            cr.id,
            cr.decided_at,
            cr.quantity_to_remove,
            ol.item_id,
            ol.item_name_snapshot,
            ol.item_short_label_snapshot
        FROM change_requests cr
        JOIN order_lines ol ON ol.id = cr.order_line_id
        WHERE cr.person_id = ?
          AND cr.status = 'APPROVED'
          AND cr.decided_at IS NOT NULL
          {correction_where}
        ORDER BY cr.decided_at DESC, cr.id DESC
        """,
        correction_params,
    ).fetchall()
    corrections = [
        {
            "key": history_key(row),
            "decided_at": row["decided_at"],
            "remaining": int(row["quantity_to_remove"] or 0),
        }
        for row in correction_rows
        if int(row["quantity_to_remove"] or 0) > 0
    ]

    history = []
    for row in rows:
        kind = row["kind"]
        item_name = row["item_name_snapshot"]
        if kind == "CONSUME" and is_system_item_name(item_name):
            continue
        qty = int(row["quantity"] or 0)
        if qty == 0:
            continue
        if kind == "ROUND_DEDUCTED":
            quantity = -abs(qty)
            type_label = "Abzug Runde"
            direction = "deduction"
        elif kind == "ROUND_REQUEST_APPROVED":
            quantity = abs(qty)
            type_label = "Runde bezahlt"
            direction = "round_payment"
        else:
            quantity = abs(qty)
            row_key = history_key(row)
            for correction in corrections:
                if correction["remaining"] <= 0:
                    continue
                if correction["key"] != row_key:
                    continue
                if correction["decided_at"] and str(row["timestamp"]) > str(correction["decided_at"]):
                    continue
                take = min(quantity, int(correction["remaining"]))
                quantity -= take
                correction["remaining"] -= take
                if quantity <= 0:
                    break
            if quantity <= 0:
                continue
            type_label = "Konsum"
            direction = "consume"
        history.append(history_entry(row, quantity, type_label, direction))
    if last_payment:
        date_label, time_label, timestamp_label = kassa_history_timestamp_labels(last_payment["timestamp"])
        history.append(
            {
                "id": int(last_payment["id"]),
                "transaction_id": int(last_payment["id"]),
                "type": last_payment["type"],
                "type_label": "SumUp-Zahlung" if last_payment["type"] == "PAID_SUMUP" else "Zahlung",
                "direction": "payment",
                "timestamp": last_payment["timestamp"],
                "date_label": date_label,
                "time_label": time_label,
                "timestamp_label": timestamp_label,
                "product": "Rechnung bezahlt",
                "short_label": "Bezahlt",
                "quantity": 0,
                "quantity_label": "OK",
            }
        )
    return history


def kassa_person_payload(conn: sqlite3.Connection, person: sqlite3.Row, lines: list[sqlite3.Row] | None = None) -> dict:
    if lines is None:
        lines = get_open_lines(conn, person["id"])
    pending = get_pending_requests_for_person(conn, int(person["id"]))
    pending_count = len(pending)
    round_plan = build_person_round_deduction_plan(conn, int(person["id"]))
    raw_total = person_total_from_lines(lines)
    total = payment_total_after_round_deductions(lines, round_plan)
    open_items = sum(int(line["quantity"] or 0) for line in lines)
    return {
        "id": int(person["id"]),
        "name": display_name(person["first_name"], person["last_name"]) or person["name"],
        "open_items": open_items,
        "payable_items": max(0, open_items - int(round_plan.get("deducted_items", 0) or 0)),
        "total_before_round_deductions": raw_total,
        "total": total,
        "total_eur": total,
        "round_deduction_items": int(round_plan.get("deducted_items", 0) or 0),
        "round_deduction_total_eur": rounded_money(float(round_plan.get("deducted_vk_eur", 0) or 0)),
        "open_rounds_count": int(round_plan.get("rounds_count", 0) or 0),
        "lines": make_payment_detail_lines_with_round_deductions(lines, round_plan),
        "pending_requests_count": pending_count,
        "pending_requests": pending,
        "can_pay": has_payable_total_after_round_deductions(lines, round_plan, pending_count),
        "revision": payment_revision(conn, lines, pending_count),
    }


def make_counts(lines: list[sqlite3.Row]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in lines:
        label = line["current_item_short_label"] or line["item_short_label_snapshot"] or line["current_item_name"] or line["item_name_snapshot"]
        counts[label] = counts.get(label, 0) + int(line["quantity"])
        if line["item_id"] is not None:
            counts[str(line["item_id"])] = counts.get(str(line["item_id"]), 0) + int(line["quantity"])
    return counts


def make_summary_lines(lines: list[sqlite3.Row]) -> list[dict]:
    """Compact per-person overview.

    Open order lines deliberately keep price/name snapshots for accounting.
    For the overview, however, lines belonging to the same stable item_id must be
    shown as one item even when the short label/name was changed later.
    """
    grouped: dict[object, dict] = {}
    for line in lines:
        key = ("item", int(line["item_id"])) if line["item_id"] is not None else (
            "snapshot",
            line["item_name_snapshot"],
            line["item_short_label_snapshot"],
        )
        label = line["current_item_short_label"] or line["item_short_label_snapshot"] or line["current_item_name"] or line["item_name_snapshot"]
        name = line["current_item_name"] or line["item_name_snapshot"]
        sort_order = int(line["current_sort_order"] if line["current_sort_order"] is not None else 9999)
        if key not in grouped:
            grouped[key] = {
                "item_id": line["item_id"],
                "name": name,
                "short_label": label,
                "quantity": 0,
                "sort_order": sort_order,
            }
        grouped[key]["quantity"] += int(line["quantity"])
        # Keep the latest/current display values if they changed while open lines exist.
        grouped[key]["name"] = name
        grouped[key]["short_label"] = label
        grouped[key]["sort_order"] = min(grouped[key]["sort_order"], sort_order)
    return sorted(grouped.values(), key=lambda item: (item["sort_order"], str(item["short_label"]).lower(), str(item["name"]).lower()))


def make_event_summary_lines(lines: list[sqlite3.Row]) -> list[dict]:
    """Strichliste seit letztem Kassensturz.

    Diese Menge ist nur die laufende Veranstaltung. Sie ist trotzdem bereits Teil
    der offenen Rechnung; beim Kassensturz wird nur die Strichlisten-Markierung
    geschlossen, nicht die offene Rechnung gelöscht.
    """
    return make_summary_lines([line for line in lines if bool(line["event_open"])])


def add_order_line(conn: sqlite3.Connection, person_id: int, item: sqlite3.Row, quantity: int = 1):
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Menge muss positiv sein")
    ensure_no_active_self_payment(conn, int(person_id))
    consumed_date = today_text()
    price = round(float(item["price_eur"]), 2)
    purchase = round(float(item["purchase_price_eur"] if "purchase_price_eur" in item.keys() else 0), 2)
    existing = conn.execute(
        """
        SELECT id, quantity
        FROM order_lines
        WHERE person_id = ?
          AND item_id = ?
          AND unit_price_eur = ?
          AND unit_purchase_price_eur = ?
          AND item_name_snapshot = ?
          AND item_short_label_snapshot = ?
          AND admin_only_snapshot = ?
          AND consumed_date = ?
          AND event_open = 1
          AND quantity > 0
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            person_id,
            item["id"],
            price,
            purchase,
            item["name"],
            item["short_label"],
            int(item["admin_only"]),
            consumed_date,
        ),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE order_lines SET quantity = quantity + ?, updated_at = ? WHERE id = ?",
            (quantity, now_text(), existing["id"]),
        )
        return existing["id"]

    cur = conn.execute(
        """
        INSERT INTO order_lines (
            person_id, item_id, quantity, unit_price_eur, unit_purchase_price_eur, item_name_snapshot,
            item_short_label_snapshot, admin_only_snapshot, consumed_date, event_open, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            person_id,
            item["id"],
            quantity,
            price,
            purchase,
            item["name"],
            item["short_label"],
            int(item["admin_only"]),
            consumed_date,
            1,
            now_text(),
            now_text(),
        ),
    )
    return cur.lastrowid


def remove_from_order_line(conn: sqlite3.Connection, line_id: int, quantity: int, allow_session_id: int | None = None):
    row = conn.execute("SELECT * FROM order_lines WHERE id = ?", (line_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Offener Posten nicht gefunden")
    ensure_no_active_self_payment(conn, int(row["person_id"]), allow_session_id=allow_session_id)
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Menge muss positiv sein")
    current_qty = int(row["quantity"])
    actual = min(current_qty, quantity)
    new_qty = current_qty - actual
    if new_qty <= 0:
        conn.execute("UPDATE order_lines SET quantity = 0, updated_at = ? WHERE id = ?", (now_text(), line_id))
    else:
        conn.execute("UPDATE order_lines SET quantity = ?, updated_at = ? WHERE id = ?", (new_qty, now_text(), line_id))
    return row, actual


def get_action_types(conn: sqlite3.Connection):
    rows = conn.execute("SELECT DISTINCT type FROM transactions ORDER BY type").fetchall()
    return [row["type"] for row in rows]


def sync_status_settings(conn: sqlite3.Connection) -> dict:
    return {
        "show_sync_status": setting_bool(conn, "show_sync_status", "1"),
        "sync_status_size_percent": max(70, min(180, int(get_setting(conn, "sync_status_size_percent", "100") or 100))),
    }


def ui_appearance_settings(conn: sqlite3.Connection) -> dict:
    feedback_style = (get_setting(conn, "drink_feedback_style", "strong") or "strong").strip().lower()
    if feedback_style not in {"subtle", "normal", "strong"}:
        feedback_style = "strong"
    feedback_position = (get_setting(conn, "drink_feedback_position", "above") or "above").strip().lower()
    if feedback_position not in {"above", "below"}:
        feedback_position = "above"
    celebration_mode = (get_setting(conn, "drink_celebration_mode", "condition") or "condition").strip().lower()
    if celebration_mode not in {"always", "condition", "never"}:
        celebration_mode = "condition"
    booking_sound_preset = (get_setting(conn, "drink_booking_sound_preset", "warm") or "warm").strip().lower()
    if booking_sound_preset not in {"warm", "soft", "clear", "bell", "calm"}:
        booking_sound_preset = "warm"
    return {
        "enable_delete_requests": setting_bool(conn, "enable_delete_requests", "1"),
        "show_person_popup_total": setting_bool(conn, "show_person_popup_total", "1"),
        "app_background_color": normalize_hex_color(get_setting(conn, "app_background_color", "#f3f4f6"), "#f3f4f6"),
        "person_card_background_color": normalize_hex_color(get_setting(conn, "person_card_background_color", "#ffffff"), "#ffffff"),
        "person_card_border_color": normalize_hex_color(get_setting(conn, "person_card_border_color", "#bfdbfe"), "#bfdbfe"),
        "person_card_border_width_px": max(0, min(8, int(get_setting(conn, "person_card_border_width_px", "2") or 2))),
        "person_card_gap_px": max(4, min(32, int(get_setting(conn, "person_card_gap_px", "10") or 10))),
        "drink_feedback_enabled": setting_bool(conn, "drink_feedback_enabled", "1"),
        "drink_feedback_style": feedback_style,
        "drink_feedback_duration_ms": max(500, min(3000, int(get_setting(conn, "drink_feedback_duration_ms", "1400") or 1400))),
        "drink_feedback_animation_intensity_percent": max(0, min(200, int(get_setting(conn, "drink_feedback_animation_intensity_percent", "100") or 100))),
        "drink_feedback_position": feedback_position,
        "drink_booking_sound_enabled": setting_bool(conn, "drink_booking_sound_enabled", "1"),
        "drink_booking_sound_preset": booking_sound_preset,
        "drink_celebration_mode": celebration_mode,
        "drink_celebration_condition_round": setting_bool(conn, "drink_celebration_condition_round", "1"),
        "drink_celebration_condition_debt": setting_bool(conn, "drink_celebration_condition_debt", "1"),
        "drink_celebration_debt_threshold_eur": rounded_money(parse_decimal_value(get_setting(conn, "drink_celebration_debt_threshold_eur", "50.00") or "50.00", "Grenzwert")),
        "drink_celebration_confetti_intensity_percent": max(0, min(200, int(get_setting(conn, "drink_celebration_confetti_intensity_percent", "100") or 100))),
        "drink_celebration_sound_enabled": setting_bool(conn, "drink_celebration_sound_enabled", "1"),
    }


def cost_notice_settings(conn: sqlite3.Connection) -> dict:
    warning_threshold = rounded_money(
        parse_decimal_value(get_setting(conn, "cost_warning_threshold_eur", "30.00") or "30.00", "Kostenwarnung")
    )
    reminder_threshold = rounded_money(
        parse_decimal_value(get_setting(conn, "payment_reminder_threshold_eur", "50.00") or "50.00", "Zahlungserinnerung")
    )
    return {
        "cost_warning_enabled": setting_bool(conn, "cost_warning_enabled", "1"),
        "cost_warning_threshold_eur": max(0.0, min(9999.0, warning_threshold)),
        "cost_warning_template": clean_notice_template(
            get_setting(conn, "cost_warning_template", DEFAULT_COST_WARNING_TEMPLATE),
            DEFAULT_COST_WARNING_TEMPLATE,
        ),
        "payment_reminder_enabled": setting_bool(conn, "payment_reminder_enabled", "1"),
        "payment_reminder_threshold_eur": max(0.0, min(9999.0, reminder_threshold)),
        "payment_reminder_template": clean_notice_template(
            get_setting(conn, "payment_reminder_template", DEFAULT_PAYMENT_REMINDER_TEMPLATE),
            DEFAULT_PAYMENT_REMINDER_TEMPLATE,
        ),
        "cost_warning_show_on_overview": setting_bool(conn, "cost_warning_show_on_overview", "1"),
        "cost_warning_show_in_popup": setting_bool(conn, "cost_warning_show_in_popup", "1"),
        "payment_reminder_show_on_overview": setting_bool(conn, "payment_reminder_show_on_overview", "1"),
        "payment_reminder_show_in_popup": setting_bool(conn, "payment_reminder_show_in_popup", "1"),
        "cost_notice_show_on_overview": setting_bool(conn, "cost_notice_show_on_overview", "1"),
        "cost_notice_show_in_popup": setting_bool(conn, "cost_notice_show_in_popup", "1"),
        "member_messages_show_on_overview": setting_bool(conn, "member_messages_show_on_overview", "1"),
        "member_messages_show_in_popup": setting_bool(conn, "member_messages_show_in_popup", "1"),
    }


def parse_timeout_value(value: str | int | None) -> int:
    try:
        timeout = int(str(value or "").strip())
    except ValueError:
        timeout = 120
    return max(30, min(600, timeout))


def test_card_payment_mode(raw_provider: str | None = None) -> bool:
    provider = (raw_provider if raw_provider is not None else os.getenv("PAYMENT_PROVIDER") or "").strip().lower()
    explicit_flag = (os.getenv(TEST_PAYMENT_FLAG_ENV) or "").strip().lower() in {"1", "true", "yes", "on"}
    if APP_ENV in TEST_PAYMENT_APP_ENVS:
        return True
    if explicit_flag and provider in TEST_PAYMENT_PROVIDERS:
        return True
    return APP_ENV in TEST_PAYMENT_PROVIDER_ENVS and provider in TEST_PAYMENT_PROVIDERS


def sumup_payment_settings(conn: sqlite3.Connection | None = None) -> dict:
    raw_provider = (os.getenv("PAYMENT_PROVIDER") or "").strip().lower()
    test_payment_mode = test_card_payment_mode(raw_provider)
    provider = "test" if test_payment_mode else raw_provider
    api_base = (os.getenv("SUMUP_API_BASE") or "https://api.sumup.com").strip().rstrip("/")
    api_key = (os.getenv("SUMUP_API_KEY") or "").strip()
    merchant_code = (os.getenv("SUMUP_MERCHANT_CODE") or "").strip()
    reader_id = (os.getenv("SUMUP_READER_ID") or "").strip()
    affiliate_key = (os.getenv("SUMUP_AFFILIATE_KEY") or "").strip()
    affiliate_app_id = (os.getenv("SUMUP_AFFILIATE_APP_ID") or "").strip()
    currency = (os.getenv("SUMUP_CURRENCY") or "EUR").strip().upper()
    timeout = parse_timeout_value(os.getenv("SUMUP_TIMEOUT_SECONDS") or "120")
    missing = []
    if test_payment_mode:
        configured = True
    else:
        if provider != "sumup":
            missing.append("PAYMENT_PROVIDER=sumup")
        if not api_key:
            missing.append("SUMUP_API_KEY")
        if not merchant_code:
            missing.append("SUMUP_MERCHANT_CODE")
        if not reader_id:
            missing.append("SUMUP_READER_ID")
        if not currency:
            missing.append("SUMUP_CURRENCY")
        configured = provider == "sumup" and not missing
    if provider not in {"sumup", "test"} and not missing:
        missing.append("PAYMENT_PROVIDER=sumup")
    return {
        "payment_provider": provider,
        "self_payment_enabled": provider == "sumup" or test_payment_mode,
        "test_payment_mode": test_payment_mode,
        "sumup_api_base": api_base,
        "sumup_api_key_configured": bool(api_key),
        "sumup_merchant_code": merchant_code,
        "sumup_reader_id": reader_id,
        "sumup_affiliate_key_configured": bool(affiliate_key),
        "sumup_affiliate_app_id": affiliate_app_id,
        "sumup_currency": currency,
        "sumup_timeout_seconds": timeout,
        "sumup_configured": configured,
        "sumup_missing": missing,
    }


def public_self_payment_settings(settings: dict) -> dict:
    configured = bool(settings.get("sumup_configured"))
    enabled = bool(settings.get("self_payment_enabled"))
    return {
        "self_payment_enabled": enabled,
        "payment_provider": settings.get("payment_provider") or "",
        "test_payment_mode": bool(settings.get("test_payment_mode")),
        "sumup_configured": configured,
        "sumup_missing": list(settings.get("sumup_missing") or []),
        "sumup_reader_id": settings.get("sumup_reader_id") or "",
        "sumup_affiliate_key_configured": bool(settings.get("sumup_affiliate_key_configured")),
        "sumup_affiliate_app_id": settings.get("sumup_affiliate_app_id") or "",
        "sumup_currency": settings.get("sumup_currency") or "EUR",
        "self_payment_available": enabled and configured,
        "sumup_timeout_seconds": int(settings.get("sumup_timeout_seconds") or 120),
    }


def sumup_config_from_settings(settings: dict, require_reader: bool = True) -> SumUpConfig:
    missing = []
    if str(settings.get("payment_provider") or "").strip().lower() != "sumup":
        missing.append("PAYMENT_PROVIDER=sumup")
    if not os.getenv("SUMUP_API_KEY"):
        missing.append("SUMUP_API_KEY")
    if not settings.get("sumup_merchant_code"):
        missing.append("SUMUP_MERCHANT_CODE")
    if require_reader and not settings.get("sumup_reader_id"):
        missing.append("SUMUP_READER_ID")
    if not settings.get("sumup_currency"):
        missing.append("SUMUP_CURRENCY")
    if missing:
        missing_text = ", ".join(missing)
        action = "Reader koppeln" if not require_reader else "Self-Checkout starten"
        raise HTTPException(status_code=503, detail=f"SumUp ist für {action} nicht vollständig konfiguriert: {missing_text}")
    if require_reader and not settings.get("sumup_configured"):
        missing = ", ".join(settings.get("sumup_missing") or [])
        raise HTTPException(status_code=503, detail=f"SumUp ist nicht vollständig konfiguriert: {missing}")
    return SumUpConfig(
        api_base=str(settings["sumup_api_base"]),
        api_key=str(os.getenv("SUMUP_API_KEY") or ""),
        merchant_code=str(settings["sumup_merchant_code"]),
        reader_id=str(settings["sumup_reader_id"]),
        currency=str(settings["sumup_currency"] or "EUR"),
        timeout_seconds=int(settings["sumup_timeout_seconds"]),
        affiliate_key=str(os.getenv("SUMUP_AFFILIATE_KEY") or ""),
        affiliate_app_id=str(settings.get("sumup_affiliate_app_id") or ""),
    )


def self_payment_lock_window_seconds(conn: sqlite3.Connection) -> int:
    timeout = int(sumup_payment_settings(conn).get("sumup_timeout_seconds") or 120)
    return max(300, min(900, timeout + 90))


def expire_stale_self_payment_sessions(conn: sqlite3.Connection):
    cutoff = (datetime.now() - timedelta(seconds=self_payment_lock_window_seconds(conn))).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        UPDATE self_payment_sessions
        SET status = 'EXPIRED',
            error = COALESCE(error, 'Zeitlimit ueberschritten'),
            updated_at = ?
        WHERE status IN ('CREATED', 'SENT_TO_READER', 'PENDING') AND updated_at < ?
        """,
        (now_text(), cutoff),
    )


def active_self_payment_session(conn: sqlite3.Connection, person_id: int | None = None):
    expire_stale_self_payment_sessions(conn)
    if person_id is None:
        return conn.execute(
            """
            SELECT *
            FROM self_payment_sessions
            WHERE status IN ('CREATED', 'SENT_TO_READER', 'PENDING')
            ORDER BY updated_at DESC, id DESC
            LIMIT 1
            """
        ).fetchone()
    return conn.execute(
        """
        SELECT *
        FROM self_payment_sessions
        WHERE person_id = ? AND status IN ('CREATED', 'SENT_TO_READER', 'PENDING')
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (person_id,),
    ).fetchone()


def ensure_no_active_self_payment(conn: sqlite3.Connection, person_id: int, allow_session_id: int | None = None):
    row = active_self_payment_session(conn, person_id)
    if row and (allow_session_id is None or int(row["id"]) != int(allow_session_id)):
        raise HTTPException(status_code=409, detail="Für diese Person läuft gerade eine Kartenzahlung")


def ensure_no_active_self_payments(conn: sqlite3.Connection):
    row = active_self_payment_session(conn)
    if row:
        raise HTTPException(status_code=409, detail="Es läuft gerade eine Kartenzahlung. Bitte warten.")


def payment_result_reference(result: dict | None) -> str | None:
    if not result:
        return None
    parts = [
        str(result.get("transaction_code") or "").strip(),
        str(result.get("transaction_id") or "").strip(),
        str(result.get("provider_checkout_id") or "").strip(),
        str(result.get("auth_code") or "").strip(),
    ]
    clean = [part for part in parts if part]
    return " / ".join(clean)[:120] if clean else None


def normalize_card_rounding_mode(mode: str | None) -> str:
    normalized = str(mode or "none").strip().lower()
    if normalized not in CARD_PAYMENT_ROUNDING_STEPS:
        raise HTTPException(status_code=400, detail="Ungültige Aufrundungsoption")
    return normalized


def eur_cents(value: float) -> int:
    return max(0, int(round(float(value or 0) * 100)))


def cents_to_eur(cents: int) -> float:
    return rounded_money(int(cents or 0) / 100)


def card_payment_breakdown(base_total_eur: float, rounding_mode: str | None = "none") -> dict:
    normalized_mode = normalize_card_rounding_mode(rounding_mode)
    base_amount_cents = eur_cents(base_total_eur)
    card_fee_cents = 0 if base_amount_cents <= 0 else max(CARD_PAYMENT_MIN_FEE_CENTS, (base_amount_cents * CARD_PAYMENT_FEE_RATE_PERCENT + 99) // 100)
    subtotal_cents = base_amount_cents + card_fee_cents
    step_cents = CARD_PAYMENT_ROUNDING_STEPS[normalized_mode]
    rounded_total_cents = subtotal_cents if step_cents <= 1 else ((subtotal_cents + step_cents - 1) // step_cents) * step_cents
    rounding_adjustment_cents = rounded_total_cents - subtotal_cents
    return {
        "base_amount_cents": base_amount_cents,
        "base_total_eur": cents_to_eur(base_amount_cents),
        "card_fee_cents": card_fee_cents,
        "card_fee_eur": cents_to_eur(card_fee_cents),
        "rounding_mode": normalized_mode,
        "rounding_adjustment_cents": rounding_adjustment_cents,
        "rounding_adjustment_eur": cents_to_eur(rounding_adjustment_cents),
        "amount_cents": rounded_total_cents,
        "amount_eur": cents_to_eur(rounded_total_cents),
    }


def card_rounding_label(mode: str | None) -> str:
    return {
        "euro": "auf volle Euro",
        "five": "auf den nächsten 5er",
        "ten": "auf den nächsten 10er",
    }.get(str(mode or "none").strip().lower(), "nicht aufrunden")


def mark_self_payment_session(
    conn: sqlite3.Connection,
    session_id: int,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    transaction_id: int | None = None,
    provider_checkout_id: str | None = None,
):
    completed_at = now_text() if status.upper() in {"PAID", "FAILED", "CANCELLED", "TIMEOUT", "UNKNOWN", "EXPIRED"} else None
    conn.execute(
        """
        UPDATE self_payment_sessions
        SET status = ?,
            terminal_result = ?,
            terminal_reference = ?,
            raw_response = ?,
            provider_checkout_id = COALESCE(?, provider_checkout_id),
            error = ?,
            transaction_id = COALESCE(?, transaction_id),
            updated_at = ?,
            completed_at = COALESCE(?, completed_at)
        WHERE id = ?
        """,
        (
            status,
            json.dumps(result or {}, ensure_ascii=True) if result is not None else None,
            payment_result_reference(result),
            json.dumps(result or {}, ensure_ascii=True) if result is not None else None,
            provider_checkout_id or (result or {}).get("provider_checkout_id"),
            (error or "")[:500] if error else None,
            transaction_id,
            now_text(),
            completed_at,
            session_id,
        ),
    )


def self_payment_session_by_client_id(conn: sqlite3.Connection, client_payment_id: str | None):
    if not client_payment_id:
        return None
    expire_stale_self_payment_sessions(conn)
    return conn.execute(
        """
        SELECT *
        FROM self_payment_sessions
        WHERE client_payment_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (client_payment_id,),
    ).fetchone()


def self_payment_status_payload(conn: sqlite3.Connection, session, duplicate: bool = False) -> dict:
    status = str(session["status"] or "").strip().upper()
    provider = str(session["provider"] or "sumup").strip().lower() if "provider" in session.keys() else "sumup"
    is_test_payment = provider == "test"
    payment_label = "Test-Kartenzahlung" if is_test_payment else "SumUp-Zahlung"
    message_by_status = {
        "CREATED": f"{payment_label} wird vorbereitet.",
        "SENT_TO_READER": "Zahlung eingeleitet, bitte Bezahlterminal beachten.",
        "PENDING": "Zahlung läuft. Bitte warten.",
        "PAID": "Zahlung abgeschlossen.",
        "FAILED": session["error"] or "Zahlung fehlgeschlagen.",
        "CANCELLED": session["error"] or "Zahlung abgebrochen.",
        "TIMEOUT": session["error"] or "Bezahlsession ist abgelaufen. Offene Posten bleiben bestehen.",
        "UNKNOWN": session["error"] or "Status ist unklar. Bitte Zahlung prüfen; offene Posten bleiben bestehen.",
        "EXPIRED": session["error"] or "Bezahlsession ist abgelaufen.",
    }
    payment_label = message_text(
        "payment_label_test" if is_test_payment else "payment_label_sumup",
        "Test-Kartenzahlung" if is_test_payment else "SumUp-Zahlung",
    )
    message_by_status = {
        "CREATED": message_text("payment_status_created", "{payment_label} wird vorbereitet.", payment_label=payment_label),
        "SENT_TO_READER": message_text("payment_status_sent_to_reader", "Zahlung eingeleitet, bitte Bezahlterminal beachten."),
        "PENDING": message_text("payment_status_pending", "Zahlung laeuft. Bitte warten."),
        "PAID": message_text("payment_status_paid", "Zahlung abgeschlossen."),
        "FAILED": session["error"] or message_text("payment_status_failed", "Zahlung fehlgeschlagen."),
        "CANCELLED": session["error"] or message_text("payment_status_cancelled", "Zahlung abgebrochen."),
        "TIMEOUT": session["error"] or message_text("payment_status_timeout", "Bezahlsession ist abgelaufen. Offene Posten bleiben bestehen."),
        "UNKNOWN": session["error"] or message_text("payment_status_unknown", "Status ist unklar. Bitte Zahlung pruefen; offene Posten bleiben bestehen."),
        "EXPIRED": session["error"] or message_text("payment_status_expired", "Bezahlsession ist abgelaufen."),
    }
    public_status = {
        "CREATED": "created",
        "SENT_TO_READER": "sent_to_reader",
        "PENDING": "pending",
        "PAID": "paid",
        "FAILED": "failed",
        "CANCELLED": "cancelled",
        "TIMEOUT": "timeout",
        "UNKNOWN": "unknown",
        "EXPIRED": "expired",
    }.get(status, status.lower() or "unknown")
    amount_cents = int(session["amount_cents"] or 0)
    base_amount_cents = int(session["base_amount_cents"] or 0) if "base_amount_cents" in session.keys() else 0
    card_fee_cents = int(session["card_fee_cents"] or 0) if "card_fee_cents" in session.keys() else 0
    rounding_adjustment_cents = int(session["rounding_adjustment_cents"] or 0) if "rounding_adjustment_cents" in session.keys() else 0
    if base_amount_cents <= 0:
        base_amount_cents = max(0, amount_cents - card_fee_cents - rounding_adjustment_cents)
    fallback_payment_message = message_by_status.get(
        status,
        session["error"] or message_text("payment_status_updated", "Zahlungsstatus aktualisiert."),
    )
    payload = {
        "status": public_status,
        "session_status": status,
        "session_id": int(session["id"]),
        "person_id": int(session["person_id"]),
        "client_payment_id": session["client_payment_id"],
        "payment_method": "TEST_CARD" if is_test_payment else "SUMUP",
        "payment_provider": provider,
        "test_payment_mode": is_test_payment,
        "total": rounded_money(float(session["amount_eur"] or 0)),
        "base_total": cents_to_eur(base_amount_cents),
        "base_amount_cents": base_amount_cents,
        "card_fee": cents_to_eur(card_fee_cents),
        "card_fee_cents": card_fee_cents,
        "rounding_mode": session["rounding_mode"] if "rounding_mode" in session.keys() else "none",
        "rounding_adjustment": cents_to_eur(rounding_adjustment_cents),
        "rounding_adjustment_cents": rounding_adjustment_cents,
        "currency": session["currency"] if "currency" in session.keys() else "EUR",
        "transaction_id": session["transaction_id"],
        "provider_checkout_id": session["provider_checkout_id"] if "provider_checkout_id" in session.keys() else None,
        "terminal_reference": session["terminal_reference"],
        "message": fallback_payment_message,
        "duplicate": bool(duplicate),
        **get_sync_state(conn),
    }
    return payload


def terminal_receipt_text(person_name: str, session_id: int) -> str:
    raw = f"Drink POS {person_name} #{session_id}"
    clean = re.sub(r"[^A-Za-z0-9 .,_:/()-]", " ", raw)
    return " ".join(clean.split())[:128]


def create_sumup_checkout(
    cfg: SumUpConfig,
    amount_cents: int,
    receipt_text: str = "",
    foreign_transaction_id: str | None = None,
) -> dict:
    return sumup_create_reader_checkout(cfg, amount_cents, receipt_text, foreign_transaction_id)


def poll_sumup_payment(cfg: SumUpConfig, provider_checkout_id: str) -> dict:
    return sumup_poll_checkout_status(cfg, provider_checkout_id, cfg.timeout_seconds)


def create_test_card_checkout(session_id: int) -> dict:
    provider_checkout_id = f"test-card-checkout-{session_id}"
    return {
        "provider_checkout_id": provider_checkout_id,
        "status": "sent_to_reader",
        "test_payment_mode": True,
    }


def paid_test_card_result(session_id: int, amount_cents: int, currency: str, provider_checkout_id: str) -> dict:
    return {
        "status": "paid",
        "provider_checkout_id": provider_checkout_id,
        "transaction_id": f"test-card-tx-{session_id}",
        "transaction_code": f"TESTCARD{session_id}",
        "auth_code": "TEST",
        "amount_cents": int(amount_cents),
        "currency": str(currency or "EUR").upper(),
        "test_payment_mode": True,
        "raw_response": {"status": "SUCCESSFUL", "test_payment_mode": True},
    }


def connection_event_label(event_type: str) -> str:
    labels = {
        "CONNECTION_LOST": "Verbindung verloren",
        "CONNECTION_RESTORED": "Verbindung aufgenommen",
        "SYNC_COMPLETED": "Synchronisiert",
    }
    return labels.get(event_type, event_type)


def normalize_client_operation_id(value: str | None) -> str | None:
    if not value:
        return None
    clean = re.sub(r"[^A-Za-z0-9_.:-]", "", value.strip())[:80]
    return clean or None


def configured_agent_token() -> str:
    return (os.getenv("DRINK_POS_AGENT_TOKEN") or AGENT_API_TOKEN or "").strip()


def agent_token_from_headers(
    authorization: str | None = None,
    x_drink_pos_agent_token: str | None = None,
) -> str:
    token = x_drink_pos_agent_token.strip() if isinstance(x_drink_pos_agent_token, str) else ""
    if token:
        return token
    if isinstance(authorization, str):
        parts = authorization.strip().split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    return ""


def require_agent_access(
    authorization: str | None = None,
    x_drink_pos_agent_token: str | None = None,
) -> None:
    expected = configured_agent_token()
    if not expected:
        raise HTTPException(status_code=404, detail="Agent API ist deaktiviert. DRINK_POS_AGENT_TOKEN setzen.")
    provided = agent_token_from_headers(authorization, x_drink_pos_agent_token)
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="Ungueltiges Agent-Token")


def require_agent_request(request: Request) -> None:
    require_agent_access(
        authorization=request.headers.get("authorization"),
        x_drink_pos_agent_token=request.headers.get("x-drink-pos-agent-token"),
    )


def admin_rate_key(request: Request) -> str:
    client = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or client


def check_admin_login_rate_limit(request: Request) -> None:
    key = admin_rate_key(request)
    now_ts = datetime.now().timestamp()
    attempts = [
        ts
        for ts in ADMIN_LOGIN_ATTEMPTS.get(key, [])
        if now_ts - ts < ADMIN_LOGIN_RATE_WINDOW_SECONDS
    ]
    if len(attempts) >= ADMIN_LOGIN_RATE_LIMIT:
        ADMIN_LOGIN_ATTEMPTS[key] = attempts
        raise HTTPException(status_code=429, detail="Zu viele Loginversuche. Bitte kurz warten.")
    attempts.append(now_ts)
    ADMIN_LOGIN_ATTEMPTS[key] = attempts


def clear_admin_login_rate_limit(request: Request) -> None:
    ADMIN_LOGIN_ATTEMPTS.pop(admin_rate_key(request), None)


# ---------------------------------------------------------------------------
# Static pages + public APIs
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    with get_conn() as conn:
        return {
            "status": "ok",
            "environment": APP_ENV,
            "database": database_info(),
            "people": conn.execute("SELECT COUNT(*) AS c FROM people WHERE archived_at IS NULL").fetchone()["c"],
            "items": conn.execute("SELECT COUNT(*) AS c FROM items WHERE archived_at IS NULL").fetchone()["c"],
        }

@app.get("/api/sync-status")
def sync_status():
    with get_conn() as conn:
        return {
            "status": "ok",
            "server_time": now_text(),
            **get_sync_state(conn),
        }


def agent_state_payload(conn: sqlite3.Connection) -> dict:
    people_rows = conn.execute(
        """
        SELECT *
        FROM people
        WHERE active = 1 AND archived_at IS NULL
        ORDER BY last_name COLLATE NOCASE ASC, first_name COLLATE NOCASE ASC, name COLLATE NOCASE ASC
        """
    ).fetchall()
    people = []
    total_open_eur = 0.0
    total_open_items = 0
    pending_total = 0
    for row in sorted(people_rows, key=lambda r: normalize_for_sort(display_name(r["first_name"], r["last_name"]) or r["name"])):
        lines = get_open_lines(conn, int(row["id"]))
        pending = get_pending_requests_for_person(conn, int(row["id"]))
        total = person_total_from_lines(lines)
        open_items = sum(int(line["quantity"] or 0) for line in lines)
        total_open_eur += total
        total_open_items += open_items
        pending_total += len(pending)
        people.append(
            {
                "id": int(row["id"]),
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "name": display_name(row["first_name"], row["last_name"]) or row["name"],
                "open_items": open_items,
                "open_total_eur": rounded_money(total),
                "summary_lines": make_summary_lines(lines),
                "event_summary_lines": make_event_summary_lines(lines),
                "lines": [serialize_open_line(line) for line in lines],
                "pending_requests": pending,
            }
        )
    return {
        "status": "ok",
        "server_time": now_text(),
        "totals": {
            "people": len(people),
            "open_items": total_open_items,
            "open_total_eur": rounded_money(total_open_eur),
            "pending_requests": pending_total,
        },
        "items": [item for item in get_items(conn, include_archived=False) if item["can_user_add"]],
        "people": people,
        **get_sync_state(conn),
    }


@app.get("/api/agent/capabilities")
def agent_capabilities(request: Request):
    require_agent_request(request)
    return {
        "status": "ok",
        "interface": "REST",
        "app": "Drink POS",
        "auth": {
            "type": "bearer",
            "headers": ["Authorization: Bearer <token>", "X-Drink-Pos-Agent-Token"],
            "enabled": bool(configured_agent_token()),
        },
        "openapi_url": "/openapi.json",
        "actions": [
            {"method": "GET", "path": "/api/agent/state", "purpose": "Strichlisten-Stand lesen"},
            {"method": "POST", "path": "/api/agent/person", "purpose": "Offene Posten einer Person lesen"},
            {"method": "POST", "path": "/api/agent/book-drink", "purpose": "Normales Getraenk buchen"},
            {"method": "POST", "path": "/api/agent/round-request", "purpose": "Rundenanfrage erstellen"},
        ],
        "limits": {
            "book_drink_max_quantity": 50,
            "round_request_max_quantity": 20,
            "admin_actions": "not_supported",
        },
    }


@app.get("/api/agent/state")
def agent_state(request: Request):
    require_agent_request(request)
    with get_conn() as conn:
        return agent_state_payload(conn)


@app.post("/api/agent/person")
def agent_person(req: AgentPersonRequest, request: Request):
    require_agent_request(request)
    with get_conn() as conn:
        person = get_person(conn, req.person_id, allow_archived=False)
        return {
            **kassa_person_payload(conn, person),
            "pending_requests": get_pending_requests_for_person(conn, req.person_id),
            **get_sync_state(conn),
        }


@app.post("/api/agent/book-drink")
def agent_book_drink(req: AgentBookDrinkRequest, request: Request):
    require_agent_request(request)
    quantity = int(req.quantity or 0)
    if quantity < 1 or quantity > 50:
        raise HTTPException(status_code=400, detail="Menge muss zwischen 1 und 50 liegen")

    with get_conn() as conn:
        person = get_person(conn, req.person_id, allow_archived=False)
        item = get_item_by_id_or_name(conn, req.item_id, req.drink)
        if not bool(item["active"]):
            raise HTTPException(status_code=400, detail="Artikel ist inaktiv")
        if bool(item["admin_only"]) or is_system_item_name(item["name"]):
            raise HTTPException(status_code=403, detail="Agenten duerfen nur normale Benutzerartikel buchen")

        client_operation_id = normalize_client_operation_id(req.client_operation_id)
        if client_operation_id:
            existing_operation = conn.execute(
                "SELECT transaction_id FROM client_operations WHERE client_operation_id = ?",
                (client_operation_id,),
            ).fetchone()
            if existing_operation:
                return {"status": "ok", "duplicate": True, "transaction_id": existing_operation["transaction_id"], **get_sync_state(conn)}
            try:
                conn.execute(
                    """
                    INSERT INTO client_operations (
                        client_operation_id, endpoint, client_time, device_info, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        client_operation_id,
                        "/api/agent/book-drink",
                        (req.client_time or "")[:80] or None,
                        (req.device_info or "")[:160] or None,
                        now_text(),
                    ),
                )
            except sqlite3.IntegrityError:
                existing_operation = conn.execute(
                    "SELECT transaction_id FROM client_operations WHERE client_operation_id = ?",
                    (client_operation_id,),
                ).fetchone()
                return {"status": "ok", "duplicate": True, "transaction_id": existing_operation["transaction_id"] if existing_operation else None, **get_sync_state(conn)}

        line_id = add_order_line(conn, person["id"], item, quantity)
        total = rounded_money(quantity * float(item["price_eur"]))
        detail_parts = [f"+{quantity}x {item['name']} via Agent API"]
        if req.note:
            safe_note = re.sub(r"[^A-Za-z0-9_.,:/() -]", "", req.note).strip()[:160]
            if safe_note:
                detail_parts.append(safe_note)
        if req.client_time:
            detail_parts.append(f"Client-Zeit: {req.client_time[:40]}")
        if req.device_info:
            safe_device = re.sub(r"[^A-Za-z0-9_.,:/() -]", "", req.device_info).strip()[:100]
            if safe_device:
                detail_parts.append(f"Geraet: {safe_device}")

        tx_id = log_transaction(conn, person["id"], "CONSUME", total, " | ".join(detail_parts))
        log_transaction_item(conn, tx_id, person["id"], {
            "item_id": item["id"],
            "item_name_snapshot": item["name"],
            "item_short_label_snapshot": item["short_label"],
            "unit_price_eur": item["price_eur"],
            "unit_purchase_price_eur": item["purchase_price_eur"] if "purchase_price_eur" in item.keys() else 0,
        }, quantity, "CONSUME")
        if client_operation_id:
            conn.execute(
                "UPDATE client_operations SET transaction_id = ? WHERE client_operation_id = ?",
                (tx_id, client_operation_id),
            )
        conn.commit()
        return {
            "status": "ok",
            "transaction_id": tx_id,
            "order_line_id": int(line_id),
            "person_id": int(person["id"]),
            "item_id": int(item["id"]),
            "quantity": quantity,
            "total_eur": total,
            **get_sync_state(conn),
        }


@app.post("/api/agent/round-request")
def agent_round_request(req: AgentRoundRequest, request: Request):
    require_agent_request(request)
    quantity = int(req.quantity or 0)
    if quantity < 1 or quantity > 20:
        raise HTTPException(status_code=400, detail="Menge muss zwischen 1 und 20 liegen")
    return create_round_request(RoundRequestIn(person_id=req.person_id, quantity=quantity, reason=req.reason))


@app.post("/api/client-event")
def client_event(req: ClientEventRequest):
    with get_conn() as conn:
        # Verbindungs-/Sync-Events dienen nur zur Diagnose im Entwicklungsmodus.
        # Im Produktivbetrieb wird der Request bestätigt, aber nicht in den Verlauf geschrieben.
        if APP_ENV != "development":
            return {"status": "ignored", "logging": "development_only", **get_sync_state(conn)}
        if req.event_type == "SYNC_COMPLETED" and req.details and "Automatisch" in req.details:
            return {"status": "ignored", "logging": "automatic_sync_suppressed", **get_sync_state(conn)}
        label = connection_event_label(req.event_type)
        parts = [label]
        if req.page:
            safe_page = re.sub(r"[^A-Za-z0-9_./ -]", "", req.page).strip()[:40]
            if safe_page:
                parts.append(f"Seite: {safe_page}")
        if req.device_info:
            safe_device = re.sub(r"[^A-Za-z0-9_.,:/() -]", "", req.device_info).strip()[:140]
            if safe_device:
                parts.append(f"Geraet: {safe_device}")
        if req.client_time:
            parts.append(f"Client-Zeit: {req.client_time[:40]}")
        if req.last_sync_at:
            parts.append(f"letzter Sync Client: {req.last_sync_at[:40]}")
        if req.details:
            parts.append(req.details.strip()[:160])
        log_transaction(conn, None, req.event_type, 0, " · ".join(parts))
        conn.commit()
        return {"status": "ok", **get_sync_state(conn)}


@app.get("/")
def home():
    return FileResponse(APP_DIR / "index.html", media_type="text/html; charset=utf-8")


@app.get("/liste")
@app.get("/liste/")
def list_page():
    return FileResponse(APP_DIR / "index.html", media_type="text/html; charset=utf-8")


@app.get("/admin")
def admin_page():
    return FileResponse(APP_DIR / "admin.html", media_type="text/html; charset=utf-8")


@app.get("/kassa")
@app.get("/kassa/")
def kassa_page():
    return FileResponse(APP_DIR / "kassa.html", media_type="text/html; charset=utf-8")


@app.get("/self-pay")
@app.get("/self-pay/")
@app.get("/bezahlen")
@app.get("/bezahlen/")
def self_pay_page():
    return FileResponse(APP_DIR / "self-pay.html", media_type="text/html; charset=utf-8")




@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(APP_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/kassa.webmanifest")
def kassa_manifest():
    return FileResponse(APP_DIR / "kassa.webmanifest", media_type="application/manifest+json")


@app.get("/self-pay.webmanifest")
def self_pay_manifest():
    return FileResponse(APP_DIR / "self-pay.webmanifest", media_type="application/manifest+json")


@app.get("/service-worker.js")
def service_worker():
    return FileResponse(APP_DIR / "service-worker.js", media_type="application/javascript")


@app.get("/icon.png")
def icon_png():
    return FileResponse(APP_DIR / "icon.png", media_type="image/png")


@app.get("/icon.svg")
def icon_svg():
    return FileResponse(APP_DIR / "icon.svg", media_type="image/svg+xml")

@app.get("/icon-192.png")
def icon_192_png():
    return FileResponse(APP_DIR / "icon-192.png", media_type="image/png")


@app.get("/icon-512.png")
def icon_512_png():
    return FileResponse(APP_DIR / "icon-512.png", media_type="image/png")


@app.get("/kassa-icon.svg")
def kassa_icon_svg():
    return FileResponse(APP_DIR / "kassa-icon.svg", media_type="image/svg+xml")


@app.get("/kassa-icon.png")
def kassa_icon_png():
    return FileResponse(APP_DIR / "kassa-icon.png", media_type="image/png")


@app.get("/kassa-icon-192.png")
def kassa_icon_192_png():
    return FileResponse(APP_DIR / "kassa-icon-192.png", media_type="image/png")


@app.get("/kassa-icon-512.png")
def kassa_icon_512_png():
    return FileResponse(APP_DIR / "kassa-icon-512.png", media_type="image/png")


@app.get("/api/messages")
def messages():
    return {"messages": load_message_catalog()}


@app.get("/api/config")
def config():
    with get_conn() as conn:
        items = get_items(conn, include_archived=False)
        user_items = [item for item in items if item["can_user_add"]]
        return {
            "currency": "EUR",
            "app_name": get_setting(conn, "app_name", "Drink POS") or "Drink POS",
            "environment": APP_ENV,
            "database": database_info(),
            "build": build_info(),
            "production": is_production(),
            "debug_enabled": not is_production(),
            "show_total_on_overview": setting_bool(conn, "show_total_on_overview", "1"),
            "tally_roughness": max(1, min(10, int(get_setting(conn, "tally_roughness", "4") or 4))),
            "overview_name_size_px": max(12.0, min(28.0, float(get_setting(conn, "overview_name_size_px", "15.5") or 15.5))),
            "overview_summary_size_percent": max(70, min(180, int(get_setting(conn, "overview_summary_size_percent", "100") or 100))),
            "show_summary_label_on_overview": get_setting(conn, "show_summary_label_on_overview", "1") in {"1", "true", "True", True},
            "overview_summary_label_text": get_setting(conn, "overview_summary_label_text", "Gesamt:") or "Gesamt:",
            "tally_size_percent": max(60, min(180, int(get_setting(conn, "tally_size_percent", "100") or 100))),
            **sync_status_settings(conn),
            **ui_appearance_settings(conn),
            **cost_notice_settings(conn),
            **public_self_payment_settings(sumup_payment_settings(conn)),
            "items": items,
            "user_items": user_items,
            # Backward-compatible name for old frontend shape.
            "drinks": user_items,
        }


@app.get("/api/people")
def list_people():
    with get_conn() as conn:
        people = conn.execute(
            """
            SELECT *
            FROM people
            WHERE active = 1 AND archived_at IS NULL
            ORDER BY last_name COLLATE NOCASE ASC, first_name COLLATE NOCASE ASC, name COLLATE NOCASE ASC
            """
        ).fetchall()
        people = sorted(people, key=lambda r: normalize_for_sort(display_name(r["first_name"], r["last_name"]) or r["name"]))
        result = []
        for person in people:
            lines = get_open_lines(conn, person["id"])
            pending = get_pending_requests_for_person(conn, person["id"])
            member_messages = get_member_messages_for_person(conn, person["id"])
            round_plan = build_person_round_deduction_plan(conn, int(person["id"]))
            raw_total = person_total_from_lines(lines)
            payable_total = payment_total_after_round_deductions(lines, round_plan)
            result.append(
                {
                    "id": person["id"],
                    "first_name": person["first_name"],
                    "last_name": person["last_name"],
                    "name": display_name(person["first_name"], person["last_name"]) or person["name"],
                    "counts": make_counts(lines),
                    "summary_lines": make_summary_lines(lines),
                    "event_summary_lines": make_event_summary_lines(lines),
                    "lines": [serialize_open_line(line) for line in lines],
                    "total": raw_total,
                    "total_before_round_deductions": raw_total,
                    "payable_total": payable_total,
                    "payable_total_eur": payable_total,
                    "round_deduction_items": int(round_plan.get("deducted_items", 0) or 0),
                    "round_deduction_total_eur": rounded_money(float(round_plan.get("deducted_vk_eur", 0) or 0)),
                    "can_pay": has_payable_total_after_round_deductions(lines, round_plan, len(pending)),
                    "pending_requests": pending,
                    "member_messages": member_messages,
                    "member_message_count": len(member_messages),
                }
            )
        return result


@app.get("/api/kassa/people")
def kassa_people():
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                p.*,
                COALESCE(SUM(ol.quantity), 0) AS open_items,
                COALESCE(SUM(ol.quantity * ol.unit_price_eur), 0) AS open_total
            FROM people p
            LEFT JOIN order_lines ol ON ol.person_id = p.id AND ol.quantity > 0
            WHERE p.active = 1 AND p.archived_at IS NULL
            GROUP BY p.id
            HAVING open_items > 0
            ORDER BY p.last_name COLLATE NOCASE ASC, p.first_name COLLATE NOCASE ASC, p.name COLLATE NOCASE ASC
            """
        ).fetchall()
        people = []
        for row in sorted(rows, key=lambda r: normalize_for_sort(display_name(r["first_name"], r["last_name"]) or r["name"])):
            lines = get_open_lines(conn, int(row["id"]))
            payload = kassa_person_payload(conn, row, lines)
            people.append(
                {
                    "id": int(row["id"]),
                    "name": payload["name"],
                    "open_items": int(row["open_items"] or 0),
                    "payable_items": payload["payable_items"],
                    "total_before_round_deductions": payload["total_before_round_deductions"],
                    "round_deduction_items": payload["round_deduction_items"],
                    "round_deduction_total_eur": payload["round_deduction_total_eur"],
                    "total": payload["total"],
                    "total_eur": payload["total_eur"],
                }
            )
        return {"people": people, **get_sync_state(conn)}


@app.get("/api/kassa/person/{person_id}")
def kassa_person(person_id: int):
    with get_conn() as conn:
        person = get_person(conn, person_id, allow_archived=False)
        return {**kassa_person_payload(conn, person), **get_sync_state(conn)}


@app.get("/api/kassa/person/{person_id}/history")
def kassa_person_history(person_id: int, limit: int = 200):
    with get_conn() as conn:
        person = get_person(conn, person_id, allow_archived=False)
        name = display_name(person["first_name"], person["last_name"]) or person["name"]
        return {
            "id": int(person["id"]),
            "name": name,
            "history": make_kassa_person_history(conn, int(person["id"]), limit),
            **get_sync_state(conn),
        }


def require_self_payment_available(conn: sqlite3.Connection) -> dict:
    settings = sumup_payment_settings(conn)
    if not settings["self_payment_enabled"]:
        raise HTTPException(status_code=403, detail="Self-Checkout ist deaktiviert. PAYMENT_PROVIDER=sumup setzen; im Testmodus ist PAYMENT_PROVIDER=test möglich.")
    if not settings["sumup_configured"]:
        missing = ", ".join(settings.get("sumup_missing") or [])
        raise HTTPException(status_code=503, detail=f"SumUp ist nicht vollständig konfiguriert: {missing}")
    return settings


@app.get("/api/self-pay/config")
def self_pay_config():
    with get_conn() as conn:
        settings = sumup_payment_settings(conn)
        return {**public_self_payment_settings(settings), **get_sync_state(conn)}


@app.post("/api/admin/sumup/status")
def admin_sumup_status(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        cfg = sumup_config_from_settings(sumup_payment_settings(conn))
    try:
        status = sumup_reader_status(cfg)
    except SumUpError as exc:
        raise HTTPException(status_code=502, detail=exc.message)
    return {"status": "ok", "reader": status}


@app.post("/api/admin/sumup/readers")
def admin_sumup_readers(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        cfg = sumup_config_from_settings(sumup_payment_settings(conn), require_reader=False)
    try:
        readers = sumup_list_readers(cfg)
    except SumUpError as exc:
        raise HTTPException(status_code=502, detail=exc.message)
    return {"status": "ok", "readers": readers}


@app.post("/api/admin/sumup/pair-reader")
def admin_sumup_pair_reader(req: SumUpPairReaderRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        cfg = sumup_config_from_settings(sumup_payment_settings(conn), require_reader=False)
    try:
        reader = sumup_pair_reader(cfg, req.pairing_code, req.name or "Drink POS")
    except SumUpError as exc:
        raise HTTPException(status_code=502, detail=exc.message)
    return {"status": "ok", "reader": reader}


@app.get("/api/self-pay/people")
def self_pay_people():
    with get_conn() as conn:
        require_self_payment_available(conn)
        return kassa_people()


@app.get("/api/self-pay/person/{person_id}")
def self_pay_person(person_id: int):
    with get_conn() as conn:
        require_self_payment_available(conn)
        person = get_person(conn, person_id, allow_archived=False)
        payload = kassa_person_payload(conn, person)
        payload["can_self_pay"] = bool(payload["can_pay"])
        return {**payload, **get_sync_state(conn)}


@app.get("/api/self-pay/payment/{client_payment_id}")
def self_pay_payment_status(client_payment_id: str):
    normalized_id = normalize_client_operation_id(client_payment_id)
    if not normalized_id:
        raise HTTPException(status_code=400, detail="Zahlungs-ID fehlt")
    with get_conn() as conn:
        session = self_payment_session_by_client_id(conn, normalized_id)
        if not session:
            raise HTTPException(status_code=404, detail="Zahlungsvorgang nicht gefunden")
        payload = self_payment_status_payload(conn, session)
        conn.commit()
        return payload


@app.post("/api/self-pay/payment/{client_payment_id}/cancel")
def self_pay_cancel_payment(client_payment_id: str):
    normalized_id = normalize_client_operation_id(client_payment_id)
    if not normalized_id:
        raise HTTPException(status_code=400, detail="Zahlungs-ID fehlt")
    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        session = self_payment_session_by_client_id(conn, normalized_id)
        if not session:
            raise HTTPException(status_code=404, detail="Zahlungsvorgang nicht gefunden")
        status = str(session["status"] or "").upper()
        if status in {"CREATED", "SENT_TO_READER", "PENDING"}:
            mark_self_payment_session(
                conn,
                int(session["id"]),
                "CANCELLED",
                error="Zahlung manuell in der Kassa abgebrochen.",
            )
            log_transaction(
                conn,
                int(session["person_id"]),
                "SUMUP_PAYMENT_CANCELLED",
                0,
                f"SumUp-Zahlung manuell abgebrochen. Session #{int(session['id'])}",
            )
            session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (int(session["id"]),)).fetchone()
        payload = self_payment_status_payload(conn, session)
        conn.commit()
        return payload


@app.post("/api/self-pay/pay")
def self_pay(req: SelfPayRequest):
    client_payment_id = normalize_client_operation_id(req.client_payment_id)
    if not client_payment_id:
        raise HTTPException(status_code=400, detail="Zahlungs-ID fehlt. Bitte Seite aktualisieren.")

    with get_conn() as conn:
        settings = require_self_payment_available(conn)
        provider = str(settings.get("payment_provider") or "").strip().lower()
        cfg = sumup_config_from_settings(settings) if provider == "sumup" else None
        conn.execute("BEGIN IMMEDIATE")
        person = get_person(conn, req.person_id, allow_archived=False)

        existing_session = self_payment_session_by_client_id(conn, client_payment_id)
        if existing_session:
            if int(existing_session["person_id"]) != int(person["id"]):
                raise HTTPException(status_code=409, detail="Diese Zahlungs-ID wurde bereits für eine andere Person verwendet")
            payload = self_payment_status_payload(conn, existing_session, duplicate=True)
            conn.commit()
            return payload

        ensure_no_active_self_payment(conn, int(person["id"]))
        lines = get_open_lines(conn, req.person_id)
        pending = get_pending_requests_for_person(conn, req.person_id)
        current_revision = payment_revision(conn, lines, len(pending))
        current_payload = kassa_person_payload(conn, person, lines)

        if current_revision != (req.expected_revision or "").strip():
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Der offene Stand hat sich gerade geändert. Bitte die aktualisierte Liste prüfen und erneut bezahlen.",
                    "current": current_payload,
                },
            )
        if pending:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Für diese Person gibt es offene Löschanfragen. Bitte zuerst im Adminbereich entscheiden.",
                    "current": current_payload,
                },
            )
        if not lines:
            raise HTTPException(status_code=400, detail="Keine offenen Posten")

        round_plan = build_person_round_deduction_plan(conn, req.person_id)
        total = payment_total_after_round_deductions(lines, round_plan)
        if total <= 0:
            raise HTTPException(status_code=400, detail=no_payable_total_detail())
        breakdown = card_payment_breakdown(total, req.rounding_mode)
        amount_cents = int(breakdown["amount_cents"])
        cur = conn.execute(
            """
            INSERT INTO self_payment_sessions (
                person_id, client_payment_id, status,
                base_amount_cents, card_fee_cents, rounding_mode, rounding_adjustment_cents,
                amount_eur, amount_cents, currency, provider, revision, created_at, updated_at
            ) VALUES (?, ?, 'CREATED', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.person_id,
                client_payment_id,
                breakdown["base_amount_cents"],
                breakdown["card_fee_cents"],
                breakdown["rounding_mode"],
                breakdown["rounding_adjustment_cents"],
                breakdown["amount_eur"],
                amount_cents,
                settings["sumup_currency"],
                provider,
                current_revision,
                now_text(),
                now_text(),
            ),
        )
        session_id = int(cur.lastrowid)
        person_name = display_name(person["first_name"], person["last_name"]) or person["name"]
        receipt_text = terminal_receipt_text(person_name, session_id)
        conn.commit()

    try:
        if provider == "test":
            checkout = create_test_card_checkout(session_id)
        else:
            checkout = create_sumup_checkout(cfg, amount_cents, receipt_text, client_payment_id)
        provider_checkout_id = str(checkout.get("provider_checkout_id") or "").strip()
        with get_conn() as conn:
            session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
            if session and str(session["status"] or "").upper() == "CANCELLED":
                payload = self_payment_status_payload(conn, session)
                conn.commit()
                return payload
            mark_self_payment_session(
                conn,
                session_id,
                "SENT_TO_READER",
                result=checkout,
                provider_checkout_id=provider_checkout_id,
            )
            conn.commit()
        if provider == "test":
            result = paid_test_card_result(session_id, amount_cents, settings["sumup_currency"], provider_checkout_id)
        else:
            result = poll_sumup_payment(cfg, provider_checkout_id)
    except SumUpError as exc:
        session_status = "UNKNOWN" if exc.category == "unknown" else "FAILED"
        with get_conn() as conn:
            session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
            if session and str(session["status"] or "").upper() == "CANCELLED":
                payload = self_payment_status_payload(conn, session)
                conn.commit()
                return payload
            mark_self_payment_session(conn, session_id, session_status, result=exc.raw_response, error=exc.message)
            log_transaction(conn, req.person_id, "SUMUP_PAYMENT_ERROR", 0, f"SumUp-Zahlung Fehler Session #{session_id}: {exc.message[:180]}")
            session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
            payload = self_payment_status_payload(conn, session) if session else {"message": str(exc)}
            conn.commit()
        raise HTTPException(status_code=502, detail=payload)
    except Exception as exc:
        with get_conn() as conn:
            session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
            if session and str(session["status"] or "").upper() == "CANCELLED":
                payload = self_payment_status_payload(conn, session)
                conn.commit()
                return payload
            mark_self_payment_session(conn, session_id, "UNKNOWN", error=str(exc))
            log_transaction(conn, req.person_id, "SUMUP_PAYMENT_ERROR", 0, f"SumUp-Zahlung unklar Session #{session_id}: {str(exc)[:180]}")
            session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
            payload = self_payment_status_payload(conn, session) if session else {"message": str(exc)}
            conn.commit()
        raise HTTPException(status_code=502, detail=payload)

    with get_conn() as conn:
        session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
        if session and str(session["status"] or "").upper() == "CANCELLED":
            payload = self_payment_status_payload(conn, session)
            conn.commit()
            return payload

    provider_status = str(result.get("status") or "unknown").lower()
    if provider_status != "paid":
        with get_conn() as conn:
            session_status = {
                "failed": "FAILED",
                "cancelled": "CANCELLED",
                "timeout": "TIMEOUT",
                "unknown": "UNKNOWN",
            }.get(provider_status, "UNKNOWN")
            message = result.get("message") or self_payment_status_payload(conn, conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone())["message"]
            mark_self_payment_session(
                conn,
                session_id,
                session_status,
                result=result,
                error=str(message),
                provider_checkout_id=result.get("provider_checkout_id"),
            )
            log_transaction(conn, req.person_id, f"SUMUP_PAYMENT_{session_status}", 0, f"SumUp-Zahlung {session_status.lower()} Session #{session_id}")
            session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
            payload = self_payment_status_payload(conn, session) if session else {"status": provider_status}
            conn.commit()
        return payload

    result_amount = result.get("amount_cents")
    result_currency = str(result.get("currency") or settings["sumup_currency"]).upper()
    if (result_amount is not None and int(result_amount) != amount_cents) or result_currency != str(settings["sumup_currency"]).upper():
        with get_conn() as conn:
            mark_self_payment_session(conn, session_id, "UNKNOWN", result=result, error="SumUp-Betrag oder Währung passt nicht zur Rechnung", provider_checkout_id=result.get("provider_checkout_id"))
            log_transaction(conn, req.person_id, "SUMUP_PAYMENT_MISMATCH", total, f"SumUp erfolgreich, aber Betrag/Währung abweichend. Session #{session_id}")
            session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
            payload = self_payment_status_payload(conn, session) if session else {"status": "unknown"}
            conn.commit()
        return payload

    with get_conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
        if session and str(session["status"] or "").upper() == "CANCELLED":
            payload = self_payment_status_payload(conn, session)
            conn.commit()
            return payload
        if not session or session["status"] not in {"CREATED", "SENT_TO_READER", "PENDING"}:
            raise HTTPException(status_code=409, detail="Zahlungssession ist nicht mehr aktiv")
        person = get_person(conn, req.person_id, allow_archived=False)
        lines = get_open_lines(conn, req.person_id)
        pending = get_pending_requests_for_person(conn, req.person_id)
        current_revision = payment_revision(conn, lines, len(pending))
        current_payload = kassa_person_payload(conn, person, lines)
        if current_revision != session["revision"] or pending:
            mark_self_payment_session(conn, session_id, "UNKNOWN", result=result, error="Rechnung hat sich nach SumUp-Freigabe geändert", provider_checkout_id=result.get("provider_checkout_id"))
            log_transaction(conn, req.person_id, "SUMUP_PAYMENT_STALE", float(session["amount_eur"]), f"SumUp erfolgreich, aber Rechnung geändert. Session #{session_id}")
            stale_session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
            payload = self_payment_status_payload(conn, stale_session) if stale_session else {"status": "unknown"}
            payload["current"] = current_payload
            conn.commit()
            raise HTTPException(
                status_code=409,
                detail=payload,
            )

        provider_label = "Test-Kartenzahlung" if provider == "test" else "SumUp-Zahlung"
        round_plan = build_person_round_deduction_plan(conn, req.person_id)
        apply_person_round_deductions(conn, req.person_id, round_plan, f"Bei {provider_label}", allow_session_id=session_id)
        lines = get_open_lines(conn, req.person_id)
        grouped_details = make_payment_detail_lines(lines)
        details = [
            f"{int(line['quantity'])}x {line['item']} zu {eur_text(line['unit_price_eur'])}"
            for line in grouped_details
        ]
        if int(round_plan.get("deducted_items", 0) or 0) > 0:
            details.append(f"Rundenabzug -{int(round_plan['deducted_items'])} Striche ({eur_text(round_plan['deducted_vk_eur'])})")
        card_fee_cents = int(session["card_fee_cents"] or 0) if "card_fee_cents" in session.keys() else 0
        rounding_adjustment_cents = int(session["rounding_adjustment_cents"] or 0) if "rounding_adjustment_cents" in session.keys() else 0
        rounding_mode = session["rounding_mode"] if "rounding_mode" in session.keys() else "none"
        if card_fee_cents > 0:
            details.append(f"Kartenzahlung +3 % {eur_text(cents_to_eur(card_fee_cents))}")
        if rounding_adjustment_cents > 0:
            details.append(f"Aufrundung {card_rounding_label(rounding_mode)} {eur_text(cents_to_eur(rounding_adjustment_cents))}")
        person_name = display_name(person["first_name"], person["last_name"]) or person["name"]
        reference = payment_result_reference(result)
        reference_text = f"; Ref {reference}" if reference else ""
        payment_text = "Test-Kartenzahlung bezahlt" if provider == "test" else "SumUp bezahlt"
        tx_id = log_transaction(conn, req.person_id, "PAID_SUMUP", float(session["amount_eur"]), f"{payment_text} von {person_name}{reference_text}: " + ", ".join(details))
        preserve_paid_round_units(conn, person, lines, tx_id)
        for line in lines:
            log_transaction_item(conn, tx_id, req.person_id, line, int(line["quantity"]), "PAID_SUMUP")
        line_ids = [int(line["id"]) for line in lines]
        if line_ids:
            placeholders = ",".join("?" for _ in line_ids)
            conn.execute(
                f"UPDATE order_lines SET quantity = 0, updated_at = ? WHERE id IN ({placeholders})",
                [now_text(), *line_ids],
            )
        mark_self_payment_session(conn, session_id, "PAID", result=result, transaction_id=tx_id, provider_checkout_id=result.get("provider_checkout_id"))
        paid_session = conn.execute("SELECT * FROM self_payment_sessions WHERE id = ?", (session_id,)).fetchone()
        payload = self_payment_status_payload(conn, paid_session)
        payload["paid_items"] = sum(int(line["quantity"] or 0) for line in lines)
        payload["paid_lines"] = len(lines)
        payload["round_deduction_items"] = int(round_plan.get("deducted_items", 0) or 0)
        payload["round_deduction_total_eur"] = rounded_money(float(round_plan.get("deducted_vk_eur", 0) or 0))
        sync_state = get_sync_state(conn)
        conn.commit()

    return {**payload, **sync_state}


@app.post("/api/member-message/ack")
def acknowledge_member_message(req: MemberMessageAckRequest):
    with get_conn() as conn:
        get_person(conn, req.person_id, allow_archived=False)
        recipient = conn.execute(
            """
            SELECT mmr.message_id, mmr.acknowledged_at
            FROM member_message_recipients mmr
            JOIN member_messages mm ON mm.id = mmr.message_id
            WHERE mmr.person_id = ?
              AND mmr.message_id = ?
              AND mm.active = 1
              AND mm.archived_at IS NULL
            """,
            (req.person_id, req.message_id),
        ).fetchone()
        if not recipient:
            raise HTTPException(status_code=404, detail="Nachricht nicht gefunden")
        if recipient["acknowledged_at"]:
            archived = archive_member_message_if_completed(conn, req.message_id)
            if archived:
                conn.commit()
            return {"status": "ok", "duplicate": True, "archived": archived}
        conn.execute(
            """
            UPDATE member_message_recipients
            SET acknowledged_at = ?
            WHERE person_id = ? AND message_id = ? AND acknowledged_at IS NULL
            """,
            (now_text(), req.person_id, req.message_id),
        )
        log_transaction(conn, req.person_id, "MEMBER_MESSAGE_ACK", 0, f"Nachricht bestätigt: #{req.message_id}")
        archived = archive_member_message_if_completed(conn, req.message_id)
        conn.commit()
    return {"status": "ok", "archived": archived}


@app.post("/api/add-drink")
def add_drink(req: AddDrinkRequest):
    with get_conn() as conn:
        person = get_person(conn, req.person_id, allow_archived=False)
        item = get_item_by_id_or_name(conn, req.item_id, req.drink)
        if not bool(item["active"]):
            raise HTTPException(status_code=400, detail="Artikel ist inaktiv")
        if bool(item["admin_only"]):
            if not req.pin:
                raise HTTPException(status_code=403, detail="Dieser Artikel darf nur vom Admin hinzugefügt werden")
            require_pin(conn, req.pin)
        client_operation_id = normalize_client_operation_id(req.client_operation_id)
        if client_operation_id:
            existing_operation = conn.execute(
                "SELECT transaction_id FROM client_operations WHERE client_operation_id = ?",
                (client_operation_id,),
            ).fetchone()
            if existing_operation:
                return {"status": "ok", "duplicate": True, "transaction_id": existing_operation["transaction_id"], **get_sync_state(conn)}
            try:
                conn.execute(
                    """
                    INSERT INTO client_operations (
                        client_operation_id, endpoint, client_time, device_info, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        client_operation_id,
                        "/api/add-drink",
                        (req.client_time or "")[:80] or None,
                        (req.device_info or "")[:160] or None,
                        now_text(),
                    ),
                )
            except sqlite3.IntegrityError:
                existing_operation = conn.execute(
                    "SELECT transaction_id FROM client_operations WHERE client_operation_id = ?",
                    (client_operation_id,),
                ).fetchone()
                return {"status": "ok", "duplicate": True, "transaction_id": existing_operation["transaction_id"] if existing_operation else None, **get_sync_state(conn)}

        add_order_line(conn, person["id"], item, 1)
        detail_parts = [f"+1x {item['name']} à {eur_text(item['price_eur'])}"]
        if client_operation_id and req.offline_queued:
            detail_parts.append("offline/Client-Queue")
        if req.client_time:
            detail_parts.append(f"Client-Zeit: {req.client_time[:40]}")
        if req.device_info:
            safe_device = re.sub(r"[^A-Za-z0-9_.,:/() -]", "", req.device_info).strip()[:100]
            if safe_device:
                detail_parts.append(f"Geraet: {safe_device}")
        tx_id = log_transaction(
            conn,
            person["id"],
            "CONSUME",
            float(item["price_eur"]),
            " · ".join(detail_parts),
        )
        log_transaction_item(conn, tx_id, person["id"], {
            "item_id": item["id"],
            "item_name_snapshot": item["name"],
            "item_short_label_snapshot": item["short_label"],
            "unit_price_eur": item["price_eur"],
            "unit_purchase_price_eur": item["purchase_price_eur"] if "purchase_price_eur" in item.keys() else 0,
        }, 1, "CONSUME")
        if client_operation_id:
            conn.execute(
                "UPDATE client_operations SET transaction_id = ? WHERE client_operation_id = ?",
                (tx_id, client_operation_id),
            )
        conn.commit()
        return {"status": "ok", "transaction_id": tx_id, **get_sync_state(conn)}


@app.post("/api/edit-request")
def create_edit_request(req: EditRequestIn):
    with get_conn() as conn:
        if not setting_bool(conn, "enable_delete_requests", "1"):
            raise HTTPException(status_code=403, detail="Löschanfragen sind aktuell deaktiviert")
        person = get_person(conn, req.person_id, allow_archived=False)
        ensure_no_active_self_payment(conn, int(person["id"]))
        requested: list[tuple[int, int]] = []

        if req.line_quantities:
            for raw_line_id, raw_qty in req.line_quantities.items():
                line_id = int(raw_line_id)
                qty = int(raw_qty)
                if qty > 0:
                    requested.append((line_id, qty))

        # Backward-compatible old UI support: only negative deltas are accepted now.
        if req.changes:
            for item_name, delta in req.changes.items():
                delta_int = int(delta)
                if delta_int >= 0:
                    continue
                qty_to_remove = abs(delta_int)
                lines = [
                    line
                    for line in get_open_lines(conn, person["id"])
                    if line["item_name_snapshot"] == item_name and not bool(line["admin_only_snapshot"])
                ]
                remaining = qty_to_remove
                for line in lines:
                    available = max(0, int(line["quantity"]) - int(line["pending_remove"] or 0))
                    if available <= 0:
                        continue
                    take = min(available, remaining)
                    requested.append((line["id"], take))
                    remaining -= take
                    if remaining <= 0:
                        break

        if not requested:
            raise HTTPException(status_code=400, detail="Keine gültige Löschanfrage ausgewählt")

        details = []
        for line_id, qty_to_remove in requested:
            line = conn.execute(
                """
                SELECT ol.*, COALESCE((
                    SELECT SUM(cr.quantity_to_remove)
                    FROM change_requests cr
                    WHERE cr.order_line_id = ol.id AND cr.status = 'PENDING'
                ), 0) AS pending_remove
                FROM order_lines ol
                WHERE ol.id = ? AND ol.person_id = ? AND ol.quantity > 0
                """,
                (line_id, person["id"]),
            ).fetchone()
            if not line:
                raise HTTPException(status_code=400, detail="Offener Posten nicht gefunden")
            if bool(line["admin_only_snapshot"]) and not is_system_item_name(line["item_name_snapshot"]):
                raise HTTPException(status_code=400, detail=f"{line['item_name_snapshot']} darf nur vom Admin korrigiert werden")
            available = max(0, int(line["quantity"]) - int(line["pending_remove"] or 0))
            if qty_to_remove < 1 or qty_to_remove > available:
                raise HTTPException(status_code=400, detail=f"Ungültige Menge für {line['item_name_snapshot']}")
            conn.execute(
                """
                INSERT INTO change_requests (
                    person_id, order_line_id, item_id, quantity_to_remove, reason, status, requested_at
                ) VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
                """,
                (person["id"], line_id, line["item_id"], qty_to_remove, req.reason, now_text()),
            )
            details.append(f"-{qty_to_remove}x {line['item_name_snapshot']}")

        log_transaction(conn, person["id"], "CHANGE_REQUEST", 0, "Löschanfrage: " + ", ".join(details))
        conn.commit()
    return {"status": "pending", "requests": len(requested)}


@app.post("/api/round-request")
def create_round_request(req: RoundRequestIn):
    with get_conn() as conn:
        person = get_person(conn, req.person_id, allow_archived=False)
        qty = int(req.quantity or 1)
        if qty < 1 or qty > 20:
            raise HTTPException(status_code=400, detail="Ungültige Menge")
        item = conn.execute("SELECT * FROM items WHERE name = ? AND archived_at IS NULL", (ROUND_ITEM_NAME,)).fetchone()
        if not item:
            ensure_round_item(conn)
            item = conn.execute("SELECT * FROM items WHERE name = ? AND archived_at IS NULL", (ROUND_ITEM_NAME,)).fetchone()
        if not item:
            raise HTTPException(status_code=400, detail="Rundenartikel nicht gefunden")
        add_order_line(conn, person["id"], item, qty)
        total = qty * float(item["price_eur"])
        tx_id = log_transaction(
            conn,
            person["id"],
            "ROUND_REQUEST_APPROVED",
            total,
            f"Runde selbst bestätigt: +{qty}x {ROUND_ITEM_NAME}",
        )
        log_transaction_item(conn, tx_id, person["id"], {
            "item_id": item["id"],
            "item_name_snapshot": item["name"],
            "item_short_label_snapshot": item["short_label"],
            "unit_price_eur": item["price_eur"],
            "unit_purchase_price_eur": 0,
        }, qty, "ROUND_REQUEST_APPROVED")
        conn.execute(
            """
            INSERT INTO round_requests (person_id, item_id, quantity, reason, status, requested_at, decided_at)
            VALUES (?, ?, ?, ?, 'APPROVED', ?, ?)
            """,
            (person["id"], item["id"], qty, req.reason, now_text(), now_text()),
        )
        conn.commit()
    return {"status": "approved", "requests": qty, "total": round(total, 2)}


# ---------------------------------------------------------------------------
# Payment, admin adjustments, rounds
# ---------------------------------------------------------------------------

def resolve_pending_for_payment(conn: sqlite3.Connection, req: PayRequest):
    pending = get_pending_requests_for_person(conn, req.person_id)
    if not pending:
        return []

    pending_ids = {int(item["id"]) for item in pending}
    approve_ids = set(int(x) for x in req.approve_request_ids)
    reject_ids = set(int(x) for x in req.reject_request_ids)

    if req.approve_pending:
        approve_ids = set(pending_ids)
        reject_ids = set()
    elif req.reject_pending:
        reject_ids = set(pending_ids)
        approve_ids = set()

    unknown = (approve_ids | reject_ids) - pending_ids
    if unknown:
        raise HTTPException(status_code=400, detail="Unbekannte Änderungswünsche ausgewählt")
    overlap = approve_ids & reject_ids
    if overlap:
        raise HTTPException(status_code=400, detail="Ein Änderungswunsch kann nicht gleichzeitig bestätigt und abgelehnt werden")
    if (approve_ids | reject_ids) != pending_ids:
        raise HTTPException(status_code=400, detail="Alle Änderungswünsche müssen vor dem Bezahlen bestätigt oder abgelehnt werden")

    handled = []
    for item in pending:
        request_id = int(item["id"])
        if request_id in approve_ids:
            line, actual = remove_from_order_line(conn, int(item["line_id"]), int(item["quantity_to_remove"]))
            conn.execute(
                "UPDATE change_requests SET status = 'APPROVED', decided_at = ? WHERE id = ?",
                (now_text(), request_id),
            )
            log_transaction(
                conn,
                req.person_id,
                "CHANGE_APPROVED",
                0,
                f"Bestätigt: -{actual}x {line['item_name_snapshot']}",
            )
            handled.append({**item, "decision": "APPROVED"})
        else:
            conn.execute(
                "UPDATE change_requests SET status = 'REJECTED', decided_at = ? WHERE id = ?",
                (now_text(), request_id),
            )
            log_transaction(
                conn,
                req.person_id,
                "CHANGE_REJECTED",
                0,
                f"Abgelehnt: -{item['quantity_to_remove']}x {item['item']}",
            )
            handled.append({**item, "decision": "REJECTED"})
    return handled


def decide_single_change_request(conn: sqlite3.Connection, request_id: int, decision: str):
    decision_norm = decision.upper()
    if decision_norm == "APPROVE":
        decision_norm = "APPROVED"
    elif decision_norm == "REJECT":
        decision_norm = "REJECTED"

    if decision_norm not in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="Ungültige Entscheidung")

    row = conn.execute(
        """
        SELECT
            cr.id,
            cr.person_id,
            cr.order_line_id,
            cr.item_id,
            cr.quantity_to_remove,
            cr.status,
            ol.quantity AS current_quantity,
            ol.item_name_snapshot,
            ol.unit_price_eur
        FROM change_requests cr
        JOIN order_lines ol ON ol.id = cr.order_line_id
        WHERE cr.id = ?
        """,
        (request_id,),
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Änderungswunsch nicht gefunden")
    if row["status"] != "PENDING":
        raise HTTPException(status_code=400, detail="Änderungswunsch ist bereits abgeschlossen")

    qty = int(row["quantity_to_remove"])
    item_name = row["item_name_snapshot"]

    if decision_norm == "APPROVED":
        if int(row["current_quantity"]) < qty:
            raise HTTPException(status_code=400, detail="Der offene Posten ist nicht mehr in ausreichender Menge vorhanden")
        line, actual = remove_from_order_line(conn, int(row["order_line_id"]), qty)
        conn.execute(
            "UPDATE change_requests SET status = 'APPROVED', decided_at = ? WHERE id = ?",
            (now_text(), request_id),
        )
        log_transaction(
            conn,
            int(row["person_id"]),
            "CHANGE_APPROVED",
            0,
            f"Bestätigt: -{actual}x {line['item_name_snapshot']}",
        )
    else:
        conn.execute(
            "UPDATE change_requests SET status = 'REJECTED', decided_at = ? WHERE id = ?",
            (now_text(), request_id),
        )
        log_transaction(
            conn,
            int(row["person_id"]),
            "CHANGE_REJECTED",
            0,
            f"Abgelehnt: -{qty}x {item_name}",
        )

    return {
        "status": "ok",
        "request_id": request_id,
        "decision": decision_norm,
        "person_id": int(row["person_id"]),
    }


@app.post("/api/admin/change-request/decide")
def admin_decide_change_request(req: AdminChangeRequestDecision):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        result = decide_single_change_request(conn, req.request_id, req.decision)
        conn.commit()
        return result


@app.post("/api/admin/round-request/decide")
def admin_decide_round_request(req: AdminRoundRequestDecision):
    decision_norm = req.decision.upper()
    if decision_norm == "APPROVE":
        decision_norm = "APPROVED"
    elif decision_norm == "REJECT":
        decision_norm = "REJECTED"
    if decision_norm not in {"APPROVED", "REJECTED"}:
        raise HTTPException(status_code=400, detail="Ungültige Entscheidung")

    with get_conn() as conn:
        require_pin(conn, req.pin)
        row = conn.execute(
            """
            SELECT rr.*, p.name AS person_name, p.first_name, p.last_name, i.name AS item_name, i.short_label, i.price_eur, i.purchase_price_eur
            FROM round_requests rr
            JOIN people p ON p.id = rr.person_id
            LEFT JOIN items i ON i.id = rr.item_id
            WHERE rr.id = ?
            """,
            (req.request_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Rundenanfrage nicht gefunden")
        if row["status"] != "PENDING":
            raise HTTPException(status_code=400, detail="Rundenanfrage ist bereits abgeschlossen")

        item = conn.execute("SELECT * FROM items WHERE id = ?", (row["item_id"],)).fetchone() if row["item_id"] else None
        if not item:
            ensure_round_item(conn)
            item = conn.execute("SELECT * FROM items WHERE name = ?", (ROUND_ITEM_NAME,)).fetchone()
        qty = max(1, int(row["quantity"] or 1))
        person_name = display_name(row["first_name"], row["last_name"]) or row["person_name"]

        if decision_norm == "APPROVED":
            add_order_line(conn, int(row["person_id"]), item, qty)
            total = qty * float(item["price_eur"])
            tx_id = log_transaction(conn, int(row["person_id"]), "ROUND_REQUEST_APPROVED", total, f"Rundenanfrage bestätigt: +{qty}x {ROUND_ITEM_NAME} für {person_name}")
            log_transaction_item(conn, tx_id, int(row["person_id"]), {
                "item_id": item["id"],
                "item_name_snapshot": item["name"],
                "item_short_label_snapshot": item["short_label"],
                "unit_price_eur": item["price_eur"],
                "unit_purchase_price_eur": 0,
            }, qty, "ROUND_REQUEST_APPROVED")
        else:
            log_transaction(conn, int(row["person_id"]), "ROUND_REQUEST_REJECTED", 0, f"Rundenanfrage abgelehnt: +{qty}x {ROUND_ITEM_NAME} für {person_name}")

        conn.execute("UPDATE round_requests SET status = ?, decided_at = ? WHERE id = ?", (decision_norm, now_text(), req.request_id))
        conn.commit()
        return {"status": "ok", "request_id": req.request_id, "decision": decision_norm, "person_id": int(row["person_id"])}


@app.post("/api/pay")
def pay(req: PayRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        person = get_person(conn, req.person_id, allow_archived=True)
        ensure_no_active_self_payment(conn, int(person["id"]))
        handled = resolve_pending_for_payment(conn, req)
        round_pending = conn.execute("SELECT COUNT(*) AS c FROM round_requests WHERE person_id = ? AND status = 'PENDING'", (req.person_id,)).fetchone()["c"]
        if round_pending:
            raise HTTPException(status_code=400, detail="Bitte zuerst alle Rundenanfragen mit ✓ oder ✕ abschließen")

        lines = get_open_lines(conn, req.person_id)
        round_plan = build_person_round_deduction_plan(conn, req.person_id)
        if not lines and int(round_plan.get("deducted_items", 0) or 0) <= 0:
            conn.commit()
            raise HTTPException(status_code=400, detail="Keine offenen Posten")
        total_after_round_deductions = payment_total_after_round_deductions(lines, round_plan)
        if total_after_round_deductions <= 0:
            raise HTTPException(status_code=400, detail=no_payable_total_detail())

        apply_person_round_deductions(conn, req.person_id, round_plan, "Beim Bezahlen")
        lines = get_open_lines(conn, req.person_id)
        total = person_total_from_lines(lines)
        details = []
        for line in lines:
            details.append(
                f"{int(line['quantity'])}x {line['item_name_snapshot']} "
                f"à {eur_text(line['unit_price_eur'])} ({line['consumed_date']})"
            )

        if int(round_plan.get("deducted_items", 0) or 0) > 0:
            details.append(f"Rundenabzug -{int(round_plan['deducted_items'])} Striche ({eur_text(round_plan['deducted_vk_eur'])})")
        if not details:
            details.append("durch Rundenabzug ausgeglichen")

        person_name = display_name(person["first_name"], person["last_name"]) or person["name"]
        tx_id = log_transaction(conn, req.person_id, "PAID_CASH", total, f"Bar bezahlt von {person_name}: " + ", ".join(details))
        preserve_paid_round_units(conn, person, lines, tx_id)
        for line in lines:
            log_transaction_item(conn, tx_id, req.person_id, line, int(line["quantity"]), "PAID_CASH")
        line_ids = [int(line["id"]) for line in lines]
        if line_ids:
            placeholders = ",".join("?" for _ in line_ids)
            conn.execute(
                f"UPDATE order_lines SET quantity = 0, updated_at = ? WHERE id IN ({placeholders})",
                [now_text(), *line_ids],
            )
        conn.commit()

    return {
        "status": "paid",
        "total": round(total, 2),
        "round_deduction_items": int(round_plan.get("deducted_items", 0) or 0),
        "round_deduction_total_eur": rounded_money(float(round_plan.get("deducted_vk_eur", 0) or 0)),
        "pending_handled": len(handled),
    }


@app.post("/api/kassa/pay")
def kassa_pay(req: KassaPayRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        conn.execute("BEGIN IMMEDIATE")
        person = get_person(conn, req.person_id, allow_archived=False)
        ensure_no_active_self_payment(conn, int(person["id"]))
        lines = get_open_lines(conn, req.person_id)
        pending = get_pending_requests_for_person(conn, req.person_id)
        current_revision = payment_revision(conn, lines, len(pending))
        current_payload = kassa_person_payload(conn, person, lines)

        if current_revision != (req.expected_revision or "").strip():
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Der offene Stand hat sich gerade geändert. Bitte die aktualisierte Liste prüfen und erneut bezahlen.",
                    "current": current_payload,
                },
            )
        if pending:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Für diese Person gibt es offene Löschanfragen. Bitte zuerst im Adminbereich entscheiden.",
                    "current": current_payload,
                },
            )
        if not lines:
            raise HTTPException(status_code=400, detail="Keine offenen Posten")

        round_plan = build_person_round_deduction_plan(conn, req.person_id)
        total_after_round_deductions = payment_total_after_round_deductions(lines, round_plan)
        if total_after_round_deductions <= 0:
            raise HTTPException(status_code=400, detail=no_payable_total_detail())
        apply_person_round_deductions(conn, req.person_id, round_plan, "Beim Kassa-Bezahlen")
        lines = get_open_lines(conn, req.person_id)
        total = person_total_from_lines(lines)
        grouped_details = make_payment_detail_lines(lines)
        details = [
            f"{int(line['quantity'])}x {line['item']} à {eur_text(line['unit_price_eur'])}"
            for line in grouped_details
        ]
        if int(round_plan.get("deducted_items", 0) or 0) > 0:
            details.append(f"Rundenabzug -{int(round_plan['deducted_items'])} Striche ({eur_text(round_plan['deducted_vk_eur'])})")
        if not details:
            details.append("durch Rundenabzug ausgeglichen")

        person_name = display_name(person["first_name"], person["last_name"]) or person["name"]
        tx_id = log_transaction(conn, req.person_id, "PAID_CASH", total, f"Kassa bezahlt von {person_name}: " + ", ".join(details))
        preserve_paid_round_units(conn, person, lines, tx_id)
        for line in lines:
            log_transaction_item(conn, tx_id, req.person_id, line, int(line["quantity"]), "PAID_CASH")
        line_ids = [int(line["id"]) for line in lines]
        if line_ids:
            placeholders = ",".join("?" for _ in line_ids)
            conn.execute(
                f"UPDATE order_lines SET quantity = 0, updated_at = ? WHERE id IN ({placeholders})",
                [now_text(), *line_ids],
            )
        sync_state = get_sync_state(conn)
        conn.commit()

    return {
        "status": "paid",
        "total": round(total, 2),
        "paid_items": sum(int(line["quantity"] or 0) for line in lines),
        "paid_lines": len(lines),
        "round_deduction_items": int(round_plan.get("deducted_items", 0) or 0),
        "round_deduction_total_eur": rounded_money(float(round_plan.get("deducted_vk_eur", 0) or 0)),
        **sync_state,
    }


@app.post("/api/admin/adjust-drink")
def admin_adjust_drink(req: AdminAdjustItemRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        person = get_person(conn, req.person_id, allow_archived=True)
        item = get_item_by_id_or_name(conn, req.item_id, req.drink)
        delta = int(req.delta)
        if delta == 0:
            raise HTTPException(status_code=400, detail="Keine Änderung ausgewählt")

        if delta > 0:
            add_order_line(conn, person["id"], item, delta)
            total = delta * float(item["price_eur"])
            details = f"Admin: +{delta}x {item['name']} à {eur_text(item['price_eur'])}"
            tx_id = log_transaction(conn, person["id"], "ADMIN_ADJUSTMENT", total, details)
            log_transaction_item(conn, tx_id, person["id"], {
                "item_id": item["id"],
                "item_name_snapshot": item["name"],
                "item_short_label_snapshot": item["short_label"],
                "unit_price_eur": item["price_eur"],
                "unit_purchase_price_eur": item["purchase_price_eur"] if "purchase_price_eur" in item.keys() else 0,
            }, delta, "CONSUME")
        else:
            to_remove = abs(delta)
            removed_qty = 0
            removed_total = 0.0
            removed_parts = []
            lines = conn.execute(
                """
                SELECT *
                FROM order_lines
                WHERE person_id = ? AND item_id = ? AND quantity > 0
                ORDER BY consumed_date DESC, created_at DESC, id DESC
                """,
                (person["id"], item["id"]),
            ).fetchall()
            for line in lines:
                if to_remove <= 0:
                    break
                line_qty = int(line["quantity"])
                take = min(to_remove, line_qty)
                if take <= 0:
                    continue
                _, actual = remove_from_order_line(conn, int(line["id"]), take)
                to_remove -= actual
                removed_qty += actual
                removed_total += actual * float(line["unit_price_eur"])
                removed_parts.append(f"-{actual}x {line['item_name_snapshot']} à {eur_text(line['unit_price_eur'])}")
            if removed_qty == 0:
                raise HTTPException(status_code=400, detail="Dieser Artikel ist bei dieser Person nicht offen")
            log_transaction(conn, person["id"], "ADMIN_ADJUSTMENT", -removed_total, "Admin: " + ", ".join(removed_parts))

        conn.commit()
        lines = get_open_lines(conn, person["id"])
        return {
            "status": "ok",
            "counts": make_counts(lines),
            "total": person_total_from_lines(lines),
            "lines": [serialize_open_line(line) for line in lines],
        }


@app.post("/api/admin-login")
def admin_login(req: PinRequest, request: Request):
    check_admin_login_rate_limit(request)
    with get_conn() as conn:
        ensure_admin_login_allowed(conn)
        require_pin(conn, req.pin)
        clear_admin_login_rate_limit(request)
        return {
            "status": "ok",
            "environment": APP_ENV,
            "build": build_info(),
            "production": is_production(),
            "debug_enabled": not is_production(),
            "pin_default_warning": (get_setting(conn, "admin_pin", ENV_PIN_CODE) == "1234"),
        }


@app.post("/api/admin/add-round-item")
def admin_add_round_item(req: PinRequest, person_id: int | None = None):
    # Kept for simple clients; the main UI uses /api/admin/adjust-drink with the admin-only item id.
    raise HTTPException(status_code=400, detail="Bitte /api/admin/adjust-drink mit dem Artikel '1 Runde' verwenden")


def cashup_detail_from_row(row: sqlite3.Row, quantity: int | None = None) -> dict:
    qty = int(row["quantity"] if quantity is None else quantity)
    price = round(float(row["unit_price_eur"]), 2)
    return {
        "line_id": row["id"],
        "person_id": row["person_id"],
        "name": display_name(row["first_name"], row["last_name"]) or row["name"] or "Unbekannt",
        "item": row["item_name_snapshot"],
        "short_label": row["item_short_label_snapshot"],
        "quantity": qty,
        "unit_price_eur": price,
        "subtotal_eur": round(qty * price, 2),
    }


def empty_auto_round_plan() -> dict:
    return {
        "rounds_count": 0,
        "charged_total_eur": 0.0,
        "deducted_items": 0,
        "deducted_vk_eur": 0.0,
        "deducted_purchase_eur": 0.0,
        "profit_vs_purchase_eur": 0.0,
        "profit_vs_retail_eur": 0.0,
        "charges": [],
        "rounds": [],
        "deductions": [],
    }


def build_auto_round_plan(conn: sqlite3.Connection) -> dict:
    round_units = current_event_round_units(conn)
    if not round_units:
        return empty_auto_round_plan()

    charge_groups: dict[tuple, dict] = {}
    for round_unit in round_units:
        if bool(round_unit.get("already_paid")):
            continue
        payer_name = round_unit["payer_name"]
        price = rounded_money(float(round_unit["round_price_eur"] or 0))
        key = (round_unit["payer_person_id"], payer_name, price)
        if key not in charge_groups:
            charge_groups[key] = {
                "person_id": round_unit["payer_person_id"],
                "name": payer_name,
                "item": ROUND_ITEM_NAME,
                "short_label": ROUND_ITEM_SHORT,
                "quantity": 0,
                "unit_price_eur": price,
                "subtotal_eur": 0.0,
            }
        charge_groups[key]["quantity"] += 1
        charge_groups[key]["subtotal_eur"] = round(charge_groups[key]["quantity"] * price, 2)

    drink_rows = conn.execute(
        """
        SELECT
            ol.*,
            p.name,
            p.first_name,
            p.last_name,
            COALESCE((
                SELECT SUM(cr.quantity_to_remove)
                FROM change_requests cr
                WHERE cr.order_line_id = ol.id AND cr.status = 'PENDING'
            ), 0) AS pending_remove
        FROM order_lines ol
        JOIN people p ON p.id = ol.person_id
        LEFT JOIN items i ON i.id = ol.item_id
        WHERE ol.quantity > 0
          AND ol.event_open = 1
          AND COALESCE(ol.admin_only_snapshot, 0) = 0
          AND COALESCE(p.active, 0) = 1
          AND p.archived_at IS NULL
          AND ol.item_name_snapshot <> ?
          AND COALESCE(i.name, '') <> ?
        ORDER BY p.last_name ASC, p.first_name ASC, ol.unit_price_eur ASC, ol.consumed_date ASC, ol.created_at ASC, ol.id ASC
        """,
        (ROUND_ITEM_NAME, ROUND_ITEM_NAME),
    ).fetchall()
    people_order: list[int] = []
    lines_by_person: dict[int, list[sqlite3.Row]] = {}
    remaining: dict[int, int] = {}
    for row in drink_rows:
        person_id = int(row["person_id"])
        available = max(0, int(row["quantity"]) - int(row["pending_remove"] or 0))
        if available <= 0:
            continue
        if person_id not in lines_by_person:
            people_order.append(person_id)
            lines_by_person[person_id] = []
        lines_by_person[person_id].append(row)
        remaining[int(row["id"])] = available

    all_deductions = []
    for round_unit in round_units:
        for person_id in people_order:
            chosen = None
            for line in lines_by_person[person_id]:
                if remaining.get(int(line["id"]), 0) > 0:
                    chosen = line
                    break
            if not chosen:
                continue
            remaining[int(chosen["id"])] -= 1
            price = round(float(chosen["unit_price_eur"]), 2)
            purchase = round(float(chosen["unit_purchase_price_eur"] if "unit_purchase_price_eur" in chosen.keys() else 0), 2)
            deduction = {
                "round_index": round_unit["round_index"],
                "payer_name": round_unit["payer_name"],
                "person_id": chosen["person_id"],
                "name": display_name(chosen["first_name"], chosen["last_name"]) or chosen["name"] or "Unbekannt",
                "line_id": chosen["id"],
                "item_id": chosen["item_id"],
                "item": chosen["item_name_snapshot"],
                "short_label": chosen["item_short_label_snapshot"],
                "quantity": 1,
                "unit_price_eur": price,
                "unit_purchase_price_eur": purchase,
                "subtotal_eur": price,
                "purchase_total_eur": purchase,
            }
            round_unit["deductions"].append(deduction)
            all_deductions.append(deduction)

    for round_unit in round_units:
        deducted_vk = round(sum(float(item["subtotal_eur"]) for item in round_unit["deductions"]), 2)
        deducted_purchase = round(sum(float(item["purchase_total_eur"]) for item in round_unit["deductions"]), 2)
        round_unit["deducted_items"] = len(round_unit["deductions"])
        round_unit["deducted_vk_eur"] = deducted_vk
        round_unit["deducted_purchase_eur"] = deducted_purchase
        round_unit["profit_vs_purchase_eur"] = round(float(round_unit["round_price_eur"]) - deducted_purchase, 2)
        round_unit["profit_vs_retail_eur"] = round(float(round_unit["round_price_eur"]) - deducted_vk, 2)

    charged_total = round(sum(float(item["round_price_eur"]) for item in round_units), 2)
    deducted_vk = round(sum(float(item["subtotal_eur"]) for item in all_deductions), 2)
    deducted_purchase = round(sum(float(item["purchase_total_eur"]) for item in all_deductions), 2)
    return {
        "rounds_count": len(round_units),
        "charged_total_eur": charged_total,
        "deducted_items": len(all_deductions),
        "deducted_vk_eur": deducted_vk,
        "deducted_purchase_eur": deducted_purchase,
        "profit_vs_purchase_eur": round(charged_total - deducted_purchase, 2),
        "profit_vs_retail_eur": round(charged_total - deducted_vk, 2),
        "charges": list(charge_groups.values()),
        "rounds": round_units,
        "deductions": all_deductions,
    }


def apply_auto_round_deductions(conn: sqlite3.Connection, plan: dict):
    if int(plan.get("rounds_count", 0) or 0) <= 0:
        return
    validate_round_deductions_are_current(conn, list(plan.get("deductions") or []))
    for round_unit in plan.get("rounds", []):
        deductions = round_unit.get("deductions", [])
        if not deductions:
            continue
        deducted_vk = round(sum(float(item["subtotal_eur"]) for item in deductions), 2)
        deducted_purchase = round(sum(float(item["purchase_total_eur"]) for item in deductions), 2)
        details_main = " | ".join(f"{item['name']}: -1x {item['item']}" for item in deductions)
        metrics = (
            f"Rundenpreis {eur_text(round_unit['round_price_eur'])}; "
            f"EK abgezogen {eur_text(deducted_purchase)}; "
            f"Gewinn EK->Rundenpreis {eur_text(float(round_unit['round_price_eur']) - deducted_purchase)}; "
            f"VK abgezogen {eur_text(deducted_vk)}; "
            f"Gewinn/Verlust VK->Rundenpreis {eur_text(float(round_unit['round_price_eur']) - deducted_vk)}"
        )
        tx_id = log_transaction(
            conn,
            None,
            "ROUND_DEDUCTED",
            deducted_vk,
            f"Automatisch bei Kassensturz; bezahlt von {round_unit['payer_name']}: {details_main} | {metrics}",
        )
        for item in deductions:
            _, actual = remove_from_order_line(conn, int(item["line_id"]), 1)
            if actual != 1:
                raise HTTPException(status_code=409, detail="Rundenabzug konnte nicht konsistent ausgeführt werden")
            log_transaction_item(conn, tx_id, int(item["person_id"]), {
                "item_id": item["item_id"],
                "item_name_snapshot": item["item"],
                "item_short_label_snapshot": item["short_label"],
                "unit_price_eur": item["unit_price_eur"],
                "unit_purchase_price_eur": item["unit_purchase_price_eur"],
            }, -1, "ROUND_DEDUCTED")
        conn.execute(
            """
            INSERT INTO round_events (
                transaction_id, timestamp, round_price_eur, deducted_vk_eur, deducted_purchase_eur,
                profit_vs_purchase_eur, profit_vs_retail_eur, details
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                now_text(),
                round(float(round_unit["round_price_eur"]), 2),
                deducted_vk,
                deducted_purchase,
                round(float(round_unit["round_price_eur"]) - deducted_purchase, 2),
                round(float(round_unit["round_price_eur"]) - deducted_vk, 2),
                f"Automatisch bei Kassensturz; bezahlt von {round_unit['payer_name']}: {details_main}",
            ),
        )
    paid_unit_ids = [
        int(round_unit["paid_round_unit_id"])
        for round_unit in plan.get("rounds", [])
        if round_unit.get("paid_round_unit_id")
    ]
    if paid_unit_ids:
        placeholders = ",".join("?" for _ in paid_unit_ids)
        conn.execute(
            f"UPDATE paid_round_units SET event_open = 0, closed_at = ? WHERE id IN ({placeholders})",
            [now_text(), *paid_unit_ids],
        )


def calculate_cashup_preview(conn: sqlite3.Connection):
    auto_rounds = build_auto_round_plan(conn)
    rows = conn.execute(
        """
        SELECT
            ol.id,
            ol.person_id,
            p.name,
            p.first_name,
            p.last_name,
            ol.item_name_snapshot,
            ol.item_short_label_snapshot,
            ol.quantity,
            ol.unit_price_eur
        FROM order_lines ol
        LEFT JOIN people p ON p.id = ol.person_id
        WHERE ol.quantity > 0 AND ol.event_open = 1
        ORDER BY p.last_name ASC, p.first_name ASC, ol.item_name_snapshot ASC
        """
    ).fetchall()
    gross_lines = len(rows)
    gross_items = sum(int(row["quantity"]) for row in rows)
    gross_total = round(sum(int(row["quantity"]) * float(row["unit_price_eur"]) for row in rows), 2)
    remaining_by_line = {int(row["id"]): int(row["quantity"]) for row in rows}
    for item in auto_rounds.get("deductions", []):
        line_id = int(item["line_id"])
        remaining_by_line[line_id] = max(0, remaining_by_line.get(line_id, 0) - 1)
    details = [cashup_detail_from_row(row, remaining_by_line[int(row["id"])]) for row in rows if remaining_by_line[int(row["id"])] > 0]
    count_lines = len(details)
    count_items = sum(int(row["quantity"]) for row in details)
    total = round(sum(float(row["subtotal_eur"]) for row in details), 2)
    return {
        "closed_lines": count_lines,
        "closed_items": count_items,
        "total": total,
        "details": details,
        "gross_lines": gross_lines,
        "gross_items": gross_items,
        "gross_total": gross_total,
        "auto_rounds": auto_rounds,
    }


@app.post("/api/admin/cashup-preview")
def admin_cashup_preview(req: CashupRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        data = calculate_cashup_preview(conn)
        return {"status": "preview", **data}


@app.post("/api/admin/cashup")
def admin_cashup(req: CashupRequest):
    """Schließt die aktuelle Veranstaltungs-Strichliste.

    Offene Rechnungen bleiben unverändert. Nur die Markierung "seit letztem
    Kassensturz" wird auf den offenen Posten zurückgesetzt, damit danach eine
    neue Veranstaltungs-Strichliste beginnt.
    """
    with get_conn() as conn:
        require_pin(conn, req.pin)
        ensure_no_active_self_payments(conn)
        data = calculate_cashup_preview(conn)
        auto_rounds = data.get("auto_rounds", {})
        if data["gross_lines"] or int(auto_rounds.get("rounds_count", 0) or 0) > 0:
            apply_auto_round_deductions(conn, auto_rounds)
        if data["closed_lines"]:
            log_transaction(
                conn,
                None,
                "CASHUP",
                data["total"],
                f"Kassensturz: {data['closed_items']} Striche auf offene Rechnungen übertragen; Summe {eur_text(data['total'])}",
            )
            conn.execute("UPDATE order_lines SET event_open = 0, updated_at = ? WHERE quantity > 0 AND event_open = 1", (now_text(),))
        conn.commit()
        return {"status": "ok", **data}


def pending_request_count(conn: sqlite3.Connection) -> int:
    delete_count = conn.execute("SELECT COUNT(*) AS c FROM change_requests WHERE status = 'PENDING'").fetchone()["c"]
    round_count = conn.execute("SELECT COUNT(*) AS c FROM round_requests WHERE status = 'PENDING'").fetchone()["c"]
    return int(delete_count) + int(round_count)


def calculate_round_preview(conn: sqlite3.Connection):
    if pending_request_count(conn):
        raise HTTPException(status_code=400, detail="Bitte zuerst alle offenen Änderungswünsche klären")

    removed = []
    total = 0.0
    people = conn.execute(
        """
        SELECT * FROM people
        WHERE active = 1 AND archived_at IS NULL
        """
    ).fetchall()
    people = sorted(people, key=lambda r: normalize_for_sort(display_name(r["first_name"], r["last_name"]) or r["name"]))

    for person in people:
        rows = conn.execute(
            """
            SELECT *
            FROM order_lines
            WHERE person_id = ?
              AND quantity > 0
              AND admin_only_snapshot = 0
              AND event_open = 1
            ORDER BY unit_price_eur ASC, consumed_date ASC, created_at ASC, id ASC
            """,
            (person["id"],),
        ).fetchall()
        if not rows:
            continue
        cheapest = rows[0]
        price = float(cheapest["unit_price_eur"])
        purchase = float(cheapest["unit_purchase_price_eur"] if "unit_purchase_price_eur" in cheapest.keys() else 0)
        removed.append(
            {
                "person_id": person["id"],
                "name": display_name(person["first_name"], person["last_name"]) or person["name"],
                "line_id": cheapest["id"],
                "item": cheapest["item_name_snapshot"],
                "drink": cheapest["item_name_snapshot"],
                "price": round(price, 2),
                "purchase_price": round(purchase, 2),
                "consumed_date": cheapest["consumed_date"],
            }
        )
        total += price
    return removed, total


@app.post("/api/deduct-round-preview")
def deduct_round_preview(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        removed, total = calculate_round_preview(conn)
        round_price = float(get_setting(conn, "round_item_price_eur", DEFAULT_ROUND_PRICE_EUR) or DEFAULT_ROUND_PRICE_EUR)
        deducted_purchase = round(sum(float(item.get("purchase_price", 0)) for item in removed), 2)
        return {
            "status": "preview",
            "removed_count": len(removed),
            "total": round(total, 2),
            "round_price_eur": round(round_price, 2),
            "deducted_purchase_eur": deducted_purchase,
            "profit_vs_purchase_eur": round(round_price - deducted_purchase, 2),
            "profit_vs_retail_eur": round(round_price - float(total), 2),
            "details": [f"{item['name']}: 1x {item['item']}" for item in removed],
            "note": "Es werden nur Getränke aus der aktuellen Strichliste seit dem letzten Kassensturz berücksichtigt.",
        }


@app.post("/api/deduct-round")
def deduct_round(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        ensure_no_active_self_payments(conn)
        removed, total = calculate_round_preview(conn)
        round_price = float(get_setting(conn, "round_item_price_eur", DEFAULT_ROUND_PRICE_EUR) or DEFAULT_ROUND_PRICE_EUR)
        deducted_vk = round(float(total), 2)
        deducted_purchase = round(sum(float(item.get("purchase_price", 0)) for item in removed), 2)
        profit_vs_purchase = round(round_price - deducted_purchase, 2)
        profit_vs_retail = round(round_price - deducted_vk, 2)
        for item in removed:
            remove_from_order_line(conn, int(item["line_id"]), 1)
        if removed:
            details_main = " | ".join(f"{item['name']}: -1x {item['item']}" for item in removed)
            metrics = (
                f"Rundenpreis {eur_text(round_price)}; "
                f"EK abgezogen {eur_text(deducted_purchase)}; Gewinn EK→Rundenpreis {eur_text(profit_vs_purchase)}; "
                f"VK abgezogen {eur_text(deducted_vk)}; Gewinn/Verlust VK→Rundenpreis {eur_text(profit_vs_retail)}"
            )
            tx_id = log_transaction(
                conn,
                None,
                "ROUND_DEDUCTED",
                deducted_vk,
                details_main + " | nur aktuelle Strichliste seit letztem Kassensturz | " + metrics,
            )
            for item in removed:
                line = {
                    "item_id": None,
                    "item_name_snapshot": item["item"],
                    "item_short_label_snapshot": item["item"],
                    "unit_price_eur": item["price"],
                    "unit_purchase_price_eur": item.get("purchase_price", 0),
                }
                log_transaction_item(conn, tx_id, item["person_id"], line, -1, "ROUND_DEDUCTED")
            conn.execute(
                """
                INSERT INTO round_events (
                    transaction_id, timestamp, round_price_eur, deducted_vk_eur, deducted_purchase_eur,
                    profit_vs_purchase_eur, profit_vs_retail_eur, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tx_id, now_text(), round_price, deducted_vk, deducted_purchase, profit_vs_purchase, profit_vs_retail, details_main),
            )
        conn.commit()
        return {
            "status": "ok",
            "removed_count": len(removed),
            "total": round(deducted_vk, 2),
            "round_price_eur": round(round_price, 2),
            "deducted_purchase_eur": round(deducted_purchase, 2),
            "profit_vs_purchase_eur": round(profit_vs_purchase, 2),
            "profit_vs_retail_eur": round(profit_vs_retail, 2),
            "details": [f"{item['name']}: 1x {item['item']}" for item in removed],
        }


# ---------------------------------------------------------------------------
# Debug/test data
# ---------------------------------------------------------------------------

@app.post("/api/debug/add-test-data")
def debug_add_test_data(req: PinRequest):
    if is_production():
        raise HTTPException(status_code=404, detail="Testdaten sind in Produktion deaktiviert")

    with get_conn() as conn:
        require_pin(conn, req.pin)
        items = conn.execute(
            "SELECT * FROM items WHERE active = 1 AND admin_only = 0 AND archived_at IS NULL"
        ).fetchall()
        people = conn.execute("SELECT * FROM people WHERE active = 1 AND archived_at IS NULL").fetchall()
        if not items or not people:
            raise HTTPException(status_code=400, detail="Keine Personen oder Artikel vorhanden")
        selected = random.sample(list(people), k=min(12, len(people)))
        added = []
        for person in selected:
            for item in items:
                qty = random.randint(0, 3)
                if qty <= 0:
                    continue
                add_order_line(conn, person["id"], item, qty)
                added.append(f"{display_name(person['first_name'], person['last_name'])}: +{qty}x {item['name']}")
        log_transaction(conn, None, "DEBUG_TEST_DATA", 0, " | ".join(added))
        conn.commit()
    return {"status": "ok", "items": len(added)}


# ---------------------------------------------------------------------------
# Admin APIs
# ---------------------------------------------------------------------------

@app.post("/api/admin/overview")
def admin_overview(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        people_rows = conn.execute("SELECT * FROM people ORDER BY archived_at IS NOT NULL ASC, active DESC, last_name, first_name").fetchall()
        people = []
        for row in sorted(people_rows, key=lambda r: normalize_for_sort(display_name(r["first_name"], r["last_name"]) or r["name"])):
            lines = get_open_lines(conn, row["id"])
            people.append(
                {
                    "id": row["id"],
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "name": display_name(row["first_name"], row["last_name"]) or row["name"],
                    "active": bool(row["active"]),
                    "archived": row["archived_at"] is not None,
                    "archived_at": row["archived_at"],
                    "open_total": person_total_from_lines(lines),
                    "open_items": sum(int(line["quantity"]) for line in lines),
                }
            )
        return {
            "people": people,
            "items": get_items(conn, include_archived=True),
            "drinks": get_items(conn, include_archived=True),
            "settings": {
                "currency": "EUR",
                "app_name": get_setting(conn, "app_name", "Drink POS") or "Drink POS",
                "database": database_info(),
                "build": build_info(),
                "round_item_price_eur": float(get_setting(conn, "round_item_price_eur", DEFAULT_ROUND_PRICE_EUR) or DEFAULT_ROUND_PRICE_EUR),
                "show_total_on_overview": setting_bool(conn, "show_total_on_overview", "1"),
                "tally_roughness": max(1, min(10, int(get_setting(conn, "tally_roughness", "4") or 4))),
                "overview_name_size_px": max(12.0, min(28.0, float(get_setting(conn, "overview_name_size_px", "15.5") or 15.5))),
                "overview_summary_size_percent": max(70, min(180, int(get_setting(conn, "overview_summary_size_percent", "100") or 100))),
                "show_summary_label_on_overview": setting_bool(conn, "show_summary_label_on_overview", "1"),
                "overview_summary_label_text": get_setting(conn, "overview_summary_label_text", "Gesamt:") or "Gesamt:",
                "tally_size_percent": max(60, min(180, int(get_setting(conn, "tally_size_percent", "100") or 100))),
                **sync_status_settings(conn),
                **ui_appearance_settings(conn),
                **cost_notice_settings(conn),
                **sumup_payment_settings(conn),
                "production": is_production(),
                "environment": APP_ENV,
                "debug_enabled": not is_production(),
                "pin_default_warning": (get_setting(conn, "admin_pin", ENV_PIN_CODE) == "1234"),
            },
            "action_types": get_action_types(conn),
            "member_messages": get_admin_member_messages(conn),
        }


@app.post("/api/admin/member-message/create")
def admin_create_member_message(req: AdminMemberMessageCreate):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        message = req.message.strip()
        title = (req.title or "").strip()
        if not message:
            raise HTTPException(status_code=400, detail="Nachricht darf nicht leer sein")
        if len(title) > 120:
            raise HTTPException(status_code=400, detail="Titel darf maximal 120 Zeichen haben")
        if len(message) > 800:
            raise HTTPException(status_code=400, detail="Nachricht darf maximal 800 Zeichen haben")
        person_ids = sorted({int(person_id) for person_id in req.person_ids if int(person_id) > 0})
        if not person_ids:
            raise HTTPException(status_code=400, detail="Bitte mindestens ein Mitglied auswählen")
        placeholders = ",".join(["?"] * len(person_ids))
        active_people = conn.execute(
            f"""
            SELECT id
            FROM people
            WHERE id IN ({placeholders}) AND active = 1 AND archived_at IS NULL
            """,
            person_ids,
        ).fetchall()
        active_ids = sorted(int(row["id"]) for row in active_people)
        if len(active_ids) != len(person_ids):
            raise HTTPException(status_code=400, detail="Mindestens ein ausgewähltes Mitglied ist nicht aktiv")
        cur = conn.execute(
            """
            INSERT INTO member_messages (title, message, active, created_at, archived_at)
            VALUES (?, ?, 1, ?, NULL)
            """,
            (title or None, message, now_text()),
        )
        message_id = int(cur.lastrowid)
        conn.executemany(
            """
            INSERT INTO member_message_recipients (message_id, person_id, acknowledged_at)
            VALUES (?, ?, NULL)
            """,
            [(message_id, person_id) for person_id in active_ids],
        )
        log_transaction(conn, None, "MEMBER_MESSAGE_CREATED", 0, f"Nachricht #{message_id} an {len(active_ids)} Mitglied(er)")
        conn.commit()
    return {"status": "ok", "id": message_id}


@app.post("/api/admin/member-message/archive")
def admin_archive_member_message(req: AdminMemberMessageArchive):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        row = conn.execute("SELECT id, title FROM member_messages WHERE id = ?", (req.message_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Nachricht nicht gefunden")
        conn.execute(
            """
            UPDATE member_messages
            SET active = 0, archived_at = COALESCE(archived_at, ?)
            WHERE id = ?
            """,
            (now_text(), req.message_id),
        )
        log_transaction(conn, None, "MEMBER_MESSAGE_ARCHIVED", 0, f"Nachricht archiviert: #{req.message_id} {row['title'] or ''}".strip())
        conn.commit()
    return {"status": "ok"}


def names_from_create_update(first_name: str | None, last_name: str | None, name: str | None) -> tuple[str, str, str]:
    if name and (not first_name and not last_name):
        first_name, last_name = split_name(name)
    first = (first_name or "").strip()
    last = (last_name or "").strip()
    full = display_name(first, last)
    if not full:
        raise HTTPException(status_code=400, detail="Vorname oder Nachname fehlt")
    return first, last, full


@app.post("/api/admin/people/create")
def admin_create_person(req: AdminPersonCreate):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        first, last, full = names_from_create_update(req.first_name, req.last_name, req.name)
        try:
            cur = conn.execute(
                """
                INSERT INTO people (name, first_name, last_name, active, archived_at, created_at)
                VALUES (?, ?, ?, 1, NULL, ?)
                """,
                (full, first, last, now_text()),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Name existiert bereits")
        person_id = cur.lastrowid
        log_transaction(conn, person_id, "PERSON_CREATED", 0, f"Person angelegt: {full}")
        conn.commit()
    return {"status": "ok", "id": person_id}


@app.post("/api/admin/people/update")
def admin_update_person(req: AdminPersonUpdate):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        old = get_person(conn, req.person_id, allow_archived=True)
        first, last, full = names_from_create_update(req.first_name, req.last_name, req.name)
        try:
            conn.execute(
                """
                UPDATE people
                SET name = ?, first_name = ?, last_name = ?, active = ?, archived_at = CASE WHEN ? = 1 THEN NULL ELSE archived_at END
                WHERE id = ?
                """,
                (full, first, last, 1 if req.active else 0, 1 if req.active else 0, req.person_id),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Name existiert bereits")
        log_transaction(
            conn,
            req.person_id,
            "PERSON_UPDATED",
            0,
            f"Person geändert: {old['name']} → {full}, aktiv={bool(req.active)}",
        )
        conn.commit()
    return {"status": "ok"}


@app.post("/api/admin/people/delete")
def admin_delete_person(req: AdminPersonDelete):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        person = get_person(conn, req.person_id, allow_archived=True)
        lines = get_open_lines(conn, req.person_id)
        total = person_total_from_lines(lines)
        qty = sum(int(line["quantity"]) for line in lines)
        conn.execute(
            "UPDATE people SET active = 0, archived_at = COALESCE(archived_at, ?) WHERE id = ?",
            (now_text(), req.person_id),
        )
        log_transaction(
            conn,
            req.person_id,
            "PERSON_DELETED",
            0,
            f"Person archiviert/gelöscht: {person['name']}; offene Posten: {qty}; offen: {eur_text(total)}",
        )
        conn.commit()
    return {"status": "ok", "open_total": total, "open_items": qty}


@app.post("/api/admin/drinks/create")
def admin_create_drink(req: AdminItemCreate):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        name = req.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Artikelname fehlt")
        if is_system_item_name(name):
            raise HTTPException(status_code=400, detail="„1 Runde“ wird unter Artikel & Preise verwaltet und ist kein normaler Artikel")
        price = parse_decimal_value(req.price, "Preis")
        purchase_price = parse_decimal_value(req.purchase_price_eur if req.purchase_price_eur is not None else req.purchase_price, "Einkaufspreis")
        if price < 0:
            raise HTTPException(status_code=400, detail="Preis darf nicht negativ sein")
        if purchase_price < 0:
            raise HTTPException(status_code=400, detail="Einkaufspreis darf nicht negativ sein")
        sort_order = req.sort_order
        if sort_order is None:
            sort_order = int(conn.execute("SELECT COALESCE(MAX(sort_order), 0) AS m FROM items").fetchone()["m"]) + 1
        try:
            cur = conn.execute(
                """
                INSERT INTO items (name, short_label, price_eur, purchase_price_eur, active, admin_only, sort_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    (req.short_label or short_label_from_name(name)).strip(),
                    price,
                    purchase_price,
                    1 if req.active else 0,
                    1 if req.admin_only else 0,
                    int(sort_order),
                    now_text(),
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Artikel existiert bereits")
        log_transaction(conn, None, "ITEM_CREATED", 0, f"Artikel angelegt: {name} VK {eur_text(price)}, EK {eur_text(purchase_price)}")
        conn.commit()
    return {"status": "ok", "id": cur.lastrowid}


@app.post("/api/admin/drinks/update")
def admin_update_drink(req: AdminItemUpdate):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        item = get_item_by_id_or_name(conn, req.item_id, req.old_name)
        name = req.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="Artikelname fehlt")
        price = parse_decimal_value(req.price, "Preis")
        purchase_price = parse_decimal_value(req.purchase_price_eur if req.purchase_price_eur is not None else req.purchase_price, "Einkaufspreis")
        if price < 0:
            raise HTTPException(status_code=400, detail="Preis darf nicht negativ sein")
        if purchase_price < 0:
            raise HTTPException(status_code=400, detail="Einkaufspreis darf nicht negativ sein")
        if is_system_item_name(item["name"]) or is_system_item_name(name):
            raise HTTPException(status_code=400, detail="„1 Runde“ wird unter Artikel & Preise verwaltet und kann hier nicht bearbeitet werden")
        try:
            conn.execute(
                """
                UPDATE items
                SET name = ?, short_label = ?, price_eur = ?, purchase_price_eur = ?, active = ?, admin_only = ?, sort_order = ?
                WHERE id = ?
                """,
                (
                    name,
                    (req.short_label or short_label_from_name(name)).strip(),
                    price,
                    purchase_price,
                    1 if req.active else 0,
                    1 if req.admin_only else 0,
                    int(req.sort_order),
                    item["id"],
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Neuer Artikelname existiert bereits")
        # Alte Zeilen aus Versionen ohne EK hatten 0.00 als Platzhalter. Wenn nun
        # ein EK gesetzt/geändert wird, korrigieren wir nur diese fehlenden Snapshots.
        if purchase_price > 0:
            conn.execute(
                """
                UPDATE order_lines
                SET unit_purchase_price_eur = ?
                WHERE item_id = ? AND COALESCE(unit_purchase_price_eur, 0) = 0
                """,
                (purchase_price, item["id"]),
            )
            conn.execute(
                """
                UPDATE transaction_items
                SET unit_purchase_price_eur = ?,
                    purchase_total_eur = quantity * ?,
                    profit_eur = total_eur - (quantity * ?)
                WHERE item_id = ? AND COALESCE(unit_purchase_price_eur, 0) = 0
                """,
                (purchase_price, purchase_price, purchase_price, item["id"]),
            )
        log_transaction(
            conn,
            None,
            "ITEM_UPDATED",
            0,
            f"Artikel geändert: {item['name']} → {name}, VK {eur_text(price)}, EK {eur_text(purchase_price)}, aktiv={bool(req.active)}, admin_only={bool(req.admin_only)}",
        )
        conn.commit()
    return {"status": "ok"}


@app.post("/api/admin/drinks/delete")
def admin_delete_drink(req: AdminItemDelete):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        item = get_item_by_id_or_name(conn, req.item_id, None)
        if is_system_item_name(item["name"]):
            raise HTTPException(status_code=400, detail="„1 Runde“ wird unter Artikel & Preise verwaltet und kann nicht gelöscht werden")
        open_qty = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) AS q FROM order_lines WHERE item_id = ? AND quantity > 0",
            (item["id"],),
        ).fetchone()["q"]
        conn.execute(
            "UPDATE items SET active = 0, archived_at = COALESCE(archived_at, ?) WHERE id = ?",
            (now_text(), item["id"]),
        )
        log_transaction(
            conn,
            None,
            "ITEM_DELETED",
            0,
            f"Artikel archiviert/gelöscht: {item['name']}; aktuell offene Menge bleibt zahlbar: {open_qty}",
        )
        conn.commit()
    return {"status": "ok", "open_quantity": int(open_qty)}


@app.post("/api/admin/settings/update")
def admin_update_settings(req: SettingsUpdateRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        details = []
        if req.new_pin is not None:
            new_pin = req.new_pin.strip()
            if len(new_pin) < 3:
                raise HTTPException(status_code=400, detail="PIN muss mindestens 3 Zeichen haben")
            set_setting(conn, "admin_pin", new_pin)
            details.append("Admin-PIN geändert")
        if req.round_item_price_eur is not None:
            price = parse_decimal_value(req.round_item_price_eur, "Rundenpreis")
            if price < 0:
                raise HTTPException(status_code=400, detail="Rundenpreis darf nicht negativ sein")
            set_setting(conn, "round_item_price_eur", f"{price:.2f}")
            conn.execute(
                """
                UPDATE items
                SET price_eur = ?, purchase_price_eur = 0, active = 1, admin_only = 1,
                    short_label = ?, archived_at = NULL
                WHERE name = ?
                """,
                (price, ROUND_ITEM_SHORT, ROUND_ITEM_NAME),
            )
            details.append(f"Rundenpreis auf {eur_text(price)} gesetzt")
        if req.show_total_on_overview is not None:
            set_setting(conn, "show_total_on_overview", "1" if req.show_total_on_overview else "0")
            details.append("Gesamtpreis in Standardansicht eingeblendet" if req.show_total_on_overview else "Gesamtpreis in Standardansicht ausgeblendet")
        if req.show_person_popup_total is not None:
            set_setting(conn, "show_person_popup_total", "1" if req.show_person_popup_total else "0")
            details.append("Gesamtsumme im Personen-Popup eingeblendet" if req.show_person_popup_total else "Gesamtsumme im Personen-Popup ausgeblendet")
        if req.app_name is not None:
            app_name = req.app_name.strip()
            if not app_name:
                raise HTTPException(status_code=400, detail="App-Name darf nicht leer sein")
            set_setting(conn, "app_name", app_name)
            details.append(f"App-Name geändert: {app_name}")
        if req.tally_roughness is not None:
            roughness = max(1, min(10, int(req.tally_roughness)))
            set_setting(conn, "tally_roughness", str(roughness))
            details.append(f"Strich-Krackeligkeit auf Stufe {roughness} gesetzt")
        if req.overview_name_size_px is not None:
            name_size = max(12.0, min(28.0, float(req.overview_name_size_px)))
            set_setting(conn, "overview_name_size_px", f"{name_size:.1f}")
            details.append(f"Namensgröße auf {decimal_comma(name_size, 1)}px gesetzt")
        if req.overview_summary_size_percent is not None:
            summary_size = max(70, min(180, int(req.overview_summary_size_percent)))
            set_setting(conn, "overview_summary_size_percent", str(summary_size))
            details.append(f"Größe der Gesamtauflistung auf {summary_size}% gesetzt")
        if req.show_summary_label_on_overview is not None:
            set_setting(conn, "show_summary_label_on_overview", "1" if req.show_summary_label_on_overview else "0")
            details.append("Beschriftung der Gesamtauflistung eingeblendet" if req.show_summary_label_on_overview else "Beschriftung der Gesamtauflistung ausgeblendet")
        if req.overview_summary_label_text is not None:
            summary_label = req.overview_summary_label_text.strip()
            if not summary_label:
                raise HTTPException(status_code=400, detail="Text für Gesamtauflistung darf nicht leer sein")
            set_setting(conn, "overview_summary_label_text", summary_label)
            details.append(f"Text der Gesamtauflistung geändert: {summary_label}")
        if req.tally_size_percent is not None:
            tally_size = max(60, min(180, int(req.tally_size_percent)))
            set_setting(conn, "tally_size_percent", str(tally_size))
            details.append(f"Strichlistengröße auf {tally_size}% gesetzt")
        if req.show_sync_status is not None:
            set_setting(conn, "show_sync_status", "1" if req.show_sync_status else "0")
            details.append("Sync-/Verbindungsanzeige eingeblendet" if req.show_sync_status else "Sync-/Verbindungsanzeige ausgeblendet")
        if req.sync_status_size_percent is not None:
            sync_size = max(70, min(180, int(req.sync_status_size_percent)))
            set_setting(conn, "sync_status_size_percent", str(sync_size))
            details.append(f"Sync-/Verbindungsanzeige auf {sync_size}% gesetzt")
        if req.enable_delete_requests is not None:
            set_setting(conn, "enable_delete_requests", "1" if req.enable_delete_requests else "0")
            details.append("Löschanfragen für Benutzer aktiviert" if req.enable_delete_requests else "Löschanfragen für Benutzer deaktiviert")
        if req.app_background_color is not None:
            color = normalize_hex_color(req.app_background_color, "#f3f4f6")
            set_setting(conn, "app_background_color", color)
            details.append(f"App-Hintergrundfarbe auf {color} gesetzt")
        if req.person_card_background_color is not None:
            color = normalize_hex_color(req.person_card_background_color, "#ffffff")
            set_setting(conn, "person_card_background_color", color)
            details.append(f"Personen-Hintergrundfarbe auf {color} gesetzt")
        if req.person_card_border_color is not None:
            color = normalize_hex_color(req.person_card_border_color, "#bfdbfe")
            set_setting(conn, "person_card_border_color", color)
            details.append(f"Personen-Rahmenfarbe auf {color} gesetzt")
        if req.person_card_border_width_px is not None:
            width = max(0, min(8, int(req.person_card_border_width_px)))
            set_setting(conn, "person_card_border_width_px", str(width))
            details.append(f"Personen-Rahmendicke auf {width}px gesetzt")
        if req.person_card_gap_px is not None:
            gap = max(4, min(32, int(req.person_card_gap_px)))
            set_setting(conn, "person_card_gap_px", str(gap))
            details.append(f"Personen-Abstand auf {gap}px gesetzt")
        if req.drink_feedback_enabled is not None:
            set_setting(conn, "drink_feedback_enabled", "1" if req.drink_feedback_enabled else "0")
            details.append("Buchungsfeedback aktiviert" if req.drink_feedback_enabled else "Buchungsfeedback deaktiviert")
        if req.drink_feedback_style is not None:
            style = req.drink_feedback_style.strip().lower()
            if style not in {"subtle", "normal", "strong"}:
                raise HTTPException(status_code=400, detail="Ungültige Feedback-Stärke")
            set_setting(conn, "drink_feedback_style", style)
            style_label = {"subtle": "dezent", "normal": "standard", "strong": "deutlich"}[style]
            details.append(f"Buchungsfeedback auf {style_label} gesetzt")
        if req.drink_feedback_duration_ms is not None:
            duration = max(500, min(3000, int(req.drink_feedback_duration_ms)))
            set_setting(conn, "drink_feedback_duration_ms", str(duration))
            details.append(f"Buchungsfeedback-Dauer auf {duration} ms gesetzt")
        if req.drink_feedback_animation_intensity_percent is not None:
            intensity = max(0, min(200, int(req.drink_feedback_animation_intensity_percent)))
            set_setting(conn, "drink_feedback_animation_intensity_percent", str(intensity))
            details.append(f"Buchungsfeedback-Animationsintensität auf {intensity}% gesetzt")
        if req.drink_feedback_position is not None:
            position = req.drink_feedback_position.strip().lower()
            if position not in {"above", "below"}:
                raise HTTPException(status_code=400, detail="Ungültige Feedback-Position")
            set_setting(conn, "drink_feedback_position", position)
            details.append("Buchungsfeedback-Position gespeichert; Kassenansicht nutzt oben/rechts")
        if req.drink_booking_sound_enabled is not None:
            set_setting(conn, "drink_booking_sound_enabled", "1" if req.drink_booking_sound_enabled else "0")
            details.append("Buchungston aktiviert" if req.drink_booking_sound_enabled else "Buchungston deaktiviert")
        if req.drink_booking_sound_preset is not None:
            preset = req.drink_booking_sound_preset.strip().lower()
            preset_labels = {"warm": "warm", "soft": "sanft", "clear": "klar", "bell": "Glocke", "calm": "ruhig"}
            if preset not in preset_labels:
                raise HTTPException(status_code=400, detail="Ungültiger Buchungston")
            set_setting(conn, "drink_booking_sound_preset", preset)
            details.append(f"Buchungston auf {preset_labels[preset]} gesetzt")
        if req.drink_celebration_mode is not None:
            mode = req.drink_celebration_mode.strip().lower()
            if mode not in {"always", "condition", "never"}:
                raise HTTPException(status_code=400, detail="Ungültiger Feiermodus")
            set_setting(conn, "drink_celebration_mode", mode)
            mode_label = {"always": "immer", "condition": "nur bei Bedingungen", "never": "nie"}[mode]
            details.append(f"Feiereffekt auf {mode_label} gesetzt")
        if req.drink_celebration_condition_round is not None:
            set_setting(conn, "drink_celebration_condition_round", "1" if req.drink_celebration_condition_round else "0")
            details.append("Feiereffekt bei Runden aktiviert" if req.drink_celebration_condition_round else "Feiereffekt bei Runden deaktiviert")
        if req.drink_celebration_condition_debt is not None:
            set_setting(conn, "drink_celebration_condition_debt", "1" if req.drink_celebration_condition_debt else "0")
            details.append("Feiereffekt bei Grenzwert aktiviert" if req.drink_celebration_condition_debt else "Feiereffekt bei Grenzwert deaktiviert")
        if req.drink_celebration_debt_threshold_eur is not None:
            threshold = max(0.0, min(9999.0, parse_decimal_value(req.drink_celebration_debt_threshold_eur, "Feedback-Grenzwert")))
            set_setting(conn, "drink_celebration_debt_threshold_eur", f"{threshold:.2f}")
            details.append(f"Feiereffekt-Grenzwert auf {eur_text(threshold)} gesetzt")
        if req.drink_celebration_confetti_intensity_percent is not None:
            intensity = max(0, min(200, int(req.drink_celebration_confetti_intensity_percent)))
            set_setting(conn, "drink_celebration_confetti_intensity_percent", str(intensity))
            details.append(f"Konfetti-Intensität auf {intensity}% gesetzt")
        if req.drink_celebration_sound_enabled is not None:
            set_setting(conn, "drink_celebration_sound_enabled", "1" if req.drink_celebration_sound_enabled else "0")
            details.append("Feierlicher Ton aktiviert" if req.drink_celebration_sound_enabled else "Feierlicher Ton deaktiviert")
        if req.cost_warning_enabled is not None:
            set_setting(conn, "cost_warning_enabled", "1" if req.cost_warning_enabled else "0")
            details.append("Kostenwarnung aktiviert" if req.cost_warning_enabled else "Kostenwarnung deaktiviert")
        if req.cost_warning_threshold_eur is not None:
            threshold = max(0.0, min(9999.0, parse_decimal_value(req.cost_warning_threshold_eur, "Kostenwarnung")))
            set_setting(conn, "cost_warning_threshold_eur", f"{threshold:.2f}")
            details.append(f"Kostenwarnung ab {eur_text(threshold)}")
        if req.cost_warning_template is not None:
            template = clean_notice_template(req.cost_warning_template, DEFAULT_COST_WARNING_TEMPLATE)
            set_setting(conn, "cost_warning_template", template)
            details.append("Text der Kostenwarnung gespeichert")
        if req.cost_warning_show_on_overview is not None:
            set_setting(conn, "cost_warning_show_on_overview", "1" if req.cost_warning_show_on_overview else "0")
            details.append("Kostenwarnung in Standardansicht angezeigt" if req.cost_warning_show_on_overview else "Kostenwarnung in Standardansicht ausgeblendet")
        if req.cost_warning_show_in_popup is not None:
            set_setting(conn, "cost_warning_show_in_popup", "1" if req.cost_warning_show_in_popup else "0")
            details.append("Kostenwarnung im Personen-Popup angezeigt" if req.cost_warning_show_in_popup else "Kostenwarnung im Personen-Popup ausgeblendet")
        if req.payment_reminder_enabled is not None:
            set_setting(conn, "payment_reminder_enabled", "1" if req.payment_reminder_enabled else "0")
            details.append("Zahlungserinnerung aktiviert" if req.payment_reminder_enabled else "Zahlungserinnerung deaktiviert")
        if req.payment_reminder_threshold_eur is not None:
            threshold = max(0.0, min(9999.0, parse_decimal_value(req.payment_reminder_threshold_eur, "Zahlungserinnerung")))
            set_setting(conn, "payment_reminder_threshold_eur", f"{threshold:.2f}")
            details.append(f"Zahlungserinnerung ab {eur_text(threshold)}")
        if req.payment_reminder_template is not None:
            template = clean_notice_template(req.payment_reminder_template, DEFAULT_PAYMENT_REMINDER_TEMPLATE)
            set_setting(conn, "payment_reminder_template", template)
            details.append("Text der Zahlungserinnerung gespeichert")
        if req.payment_reminder_show_on_overview is not None:
            set_setting(conn, "payment_reminder_show_on_overview", "1" if req.payment_reminder_show_on_overview else "0")
            details.append("Zahlungserinnerung in Standardansicht angezeigt" if req.payment_reminder_show_on_overview else "Zahlungserinnerung in Standardansicht ausgeblendet")
        if req.payment_reminder_show_in_popup is not None:
            set_setting(conn, "payment_reminder_show_in_popup", "1" if req.payment_reminder_show_in_popup else "0")
            details.append("Zahlungserinnerung im Personen-Popup angezeigt" if req.payment_reminder_show_in_popup else "Zahlungserinnerung im Personen-Popup ausgeblendet")
        if req.cost_notice_show_on_overview is not None:
            set_setting(conn, "cost_notice_show_on_overview", "1" if req.cost_notice_show_on_overview else "0")
            details.append("Kostenhinweise in Standardansicht angezeigt" if req.cost_notice_show_on_overview else "Kostenhinweise in Standardansicht ausgeblendet")
        if req.cost_notice_show_in_popup is not None:
            set_setting(conn, "cost_notice_show_in_popup", "1" if req.cost_notice_show_in_popup else "0")
            details.append("Kostenhinweise im Personen-Popup angezeigt" if req.cost_notice_show_in_popup else "Kostenhinweise im Personen-Popup ausgeblendet")
        if req.member_messages_show_on_overview is not None:
            set_setting(conn, "member_messages_show_on_overview", "1" if req.member_messages_show_on_overview else "0")
            details.append("Mitgliedernachrichten in Standardansicht angezeigt" if req.member_messages_show_on_overview else "Mitgliedernachrichten in Standardansicht ausgeblendet")
        if req.member_messages_show_in_popup is not None:
            set_setting(conn, "member_messages_show_in_popup", "1" if req.member_messages_show_in_popup else "0")
            details.append("Mitgliedernachrichten im Personen-Popup angezeigt" if req.member_messages_show_in_popup else "Mitgliedernachrichten im Personen-Popup ausgeblendet")
        if not details:
            raise HTTPException(status_code=400, detail="Keine Einstellung geändert")
        log_transaction(conn, None, "SETTINGS_UPDATED", 0, "; ".join(details))
        conn.commit()
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# History + CSV exports
# ---------------------------------------------------------------------------

@app.post("/api/admin/transactions/filter")
def admin_transactions_filter(req: TransactionFilterRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        limit = max(1, min(int(req.limit or 500), 5000))
        where = []
        params: list[object] = []

        if req.person_id:
            where.append("t.person_id = ?")
            params.append(req.person_id)

        if req.name and req.name.strip():
            where.append("COALESCE(p.name, '') LIKE ?")
            params.append(f"%{req.name.strip()}%")

        if req.action_types is not None:
            selected_types = [str(t).strip() for t in req.action_types if str(t).strip() and str(t).strip() != "ALL"]
            if not selected_types:
                where.append("1 = 0")
            else:
                placeholders = ",".join(["?"] * len(selected_types))
                where.append(f"t.type IN ({placeholders})")
                params.extend(selected_types)
        elif req.action_type and req.action_type != "ALL":
            where.append("t.type = ?")
            params.append(req.action_type)

        if req.excluded_action_types:
            excluded_types = [str(t).strip() for t in req.excluded_action_types if str(t).strip() and str(t).strip() != "ALL"]
            if excluded_types:
                placeholders = ",".join(["?"] * len(excluded_types))
                where.append(f"t.type NOT IN ({placeholders})")
                params.extend(excluded_types)

        if req.date_from and req.date_from.strip():
            where.append("t.timestamp >= ?")
            params.append(req.date_from.strip() + " 00:00:00")

        if req.date_to and req.date_to.strip():
            where.append("t.timestamp <= ?")
            params.append(req.date_to.strip() + " 23:59:59")

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        rows = conn.execute(
            f"""
            SELECT
                t.id,
                COALESCE(p.name, 'System/Admin') AS name,
                t.type,
                t.total,
                t.details,
                t.timestamp
            FROM transactions t
            LEFT JOIN people p ON p.id = t.person_id
            {where_sql}
            ORDER BY t.id DESC
            LIMIT ?
            """,
            params + [limit],
        ).fetchall()
        out_rows = []
        for row in rows:
            item = dict(row)
            item["details"] = normalize_decimal_text(item.get("details", ""))
            out_rows.append(item)
        return {"rows": out_rows, "action_types": get_action_types(conn)}


@app.post("/api/admin/transactions")
def admin_transactions(req: PinRequest):
    return admin_transactions_filter(TransactionFilterRequest(pin=req.pin, limit=200))["rows"]


@app.get("/api/transactions")
def transactions(pin: str | None = None):
    with get_conn() as conn:
        require_pin(conn, pin or "")
        rows = conn.execute(
            """
            SELECT t.id, COALESCE(p.name, 'System/Admin') AS name, t.type, t.total, t.details, t.timestamp
            FROM transactions t
            LEFT JOIN people p ON p.id = t.person_id
            ORDER BY t.id DESC
            LIMIT 100
            """
        ).fetchall()
        out_rows = []
        for row in rows:
            item = dict(row)
            item["details"] = normalize_decimal_text(item.get("details", ""))
            out_rows.append(item)
        return out_rows


def csv_response(filename: str, headers: list[str], rows: list[list[object]]):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def report_group_columns(group_by: str) -> list[str]:
    g = (group_by or "item").strip().lower()
    mapping = {
        "none": [],
        "date": ["date"],
        "person": ["person"],
        "item": ["item"],
        "type": ["item"],
        "item_person": ["item", "person"],
        "person_item": ["person", "item"],
        "item_date": ["item", "date"],
        "date_item": ["date", "item"],
        "person_date": ["person", "date"],
        "date_person": ["date", "person"],
        "item_person_date": ["item", "person", "date"],
        "date_person_item": ["date", "person", "item"],
    }
    return mapping.get(g, ["item"])


def date_in_range(date_value: str, date_from: str | None, date_to: str | None) -> bool:
    if date_from and date_value < date_from:
        return False
    if date_to and date_value > date_to:
        return False
    return True


def add_metric_row(base: dict, row: dict):
    base["quantity"] += int(row.get("quantity", 0) or 0)
    base["revenue_eur"] += float(row.get("revenue_eur", 0) or 0)
    base["cost_eur"] += float(row.get("cost_eur", 0) or 0)
    base["profit_eur"] += float(row.get("profit_eur", 0) or 0)
    base["vk_value_eur"] += float(row.get("vk_value_eur", 0) or 0)


def build_report_rows(conn: sqlite3.Connection, req: ReportRequest) -> tuple[list[str], list[list[object]]]:
    report_type = (req.report_type or "consumption").strip().lower()
    group_cols = report_group_columns(req.group_by)
    raw: list[dict] = []

    if report_type == "event_consumption":
        rows = conn.execute(
            """
            SELECT ol.*, COALESCE(p.name, 'Gelöschte Person') AS person_name
            FROM order_lines ol
            LEFT JOIN people p ON p.id = ol.person_id
            WHERE ol.quantity > 0 AND ol.event_open = 1
              AND COALESCE(ol.admin_only_snapshot, 0) = 0
            """
        ).fetchall()
        for r in rows:
            date_value = r["consumed_date"]
            if not date_in_range(date_value, req.date_from, req.date_to):
                continue
            qty = int(r["quantity"])
            cost = qty * float(r["unit_purchase_price_eur"] if "unit_purchase_price_eur" in r.keys() else 0)
            vk = qty * float(r["unit_price_eur"])
            raw.append({
                "date": date_value,
                "person": r["person_name"],
                "item": r["item_name_snapshot"],
                "short_label": r["item_short_label_snapshot"],
                "quantity": qty,
                "revenue_eur": 0,
                "cost_eur": cost,
                "profit_eur": -cost,
                "vk_value_eur": vk,
            })
    elif report_type == "rounds":
        rows = conn.execute(
            """
            SELECT id, timestamp, round_price_eur, deducted_vk_eur, deducted_purchase_eur,
                   profit_vs_purchase_eur, profit_vs_retail_eur, COALESCE(details, '') AS details
            FROM round_events
            ORDER BY timestamp ASC, id ASC
            """
        ).fetchall()
        headers = ["id", "date", "timestamp", "round_price_eur", "deducted_ek_eur", "deducted_vk_eur", "gewinn_ek_zu_rundenpreis_eur", "gewinn_verlust_vk_zu_rundenpreis_eur", "details"]
        out = []
        for r in rows:
            date_value = str(r["timestamp"])[:10]
            if not date_in_range(date_value, req.date_from, req.date_to):
                continue
            out.append([
                r["id"], date_value, r["timestamp"], decimal_comma(r['round_price_eur']),
                decimal_comma(r['deducted_purchase_eur']), decimal_comma(r['deducted_vk_eur']),
                decimal_comma(r['profit_vs_purchase_eur']), decimal_comma(r['profit_vs_retail_eur']), normalize_decimal_text(r["details"]),
            ])
        return headers, out
    else:
        if report_type == "consumption":
            kinds = ("CONSUME",)
        elif report_type == "revenue":
            kinds = PAID_TRANSACTION_KINDS
        elif report_type == "profit":
            kinds = (*PAID_TRANSACTION_KINDS, "ROUND_DEDUCTED")
        else:
            raise HTTPException(status_code=400, detail="Unbekannter Berichtstyp")

        placeholders = ",".join("?" for _ in kinds)
        rows = conn.execute(
            f"""
            SELECT ti.*, COALESCE(p.name, 'System/Admin') AS person_name,
                   COALESCE(i.admin_only, 0) AS current_admin_only
            FROM transaction_items ti
            LEFT JOIN people p ON p.id = ti.person_id
            LEFT JOIN items i ON i.id = ti.item_id
            WHERE ti.kind IN ({placeholders})
            ORDER BY ti.timestamp ASC, ti.id ASC
            """,
            kinds,
        ).fetchall()
        for r in rows:
            date_value = str(r["timestamp"])[:10]
            if not date_in_range(date_value, req.date_from, req.date_to):
                continue
            kind = r["kind"]
            if report_type == "consumption" and (bool(r["current_admin_only"]) or is_system_item_name(r["item_name_snapshot"])):
                continue
            qty = int(r["quantity"])
            total = float(r["total_eur"])
            purchase_total = float(r["purchase_total_eur"] if "purchase_total_eur" in r.keys() else 0)
            if report_type == "consumption":
                raw.append({
                    "date": date_value,
                    "person": r["person_name"],
                    "item": r["item_name_snapshot"],
                    "short_label": r["item_short_label_snapshot"],
                    "quantity": qty,
                    "revenue_eur": 0,
                    "cost_eur": purchase_total,
                    "profit_eur": -purchase_total,
                    "vk_value_eur": total,
                })
            elif report_type == "revenue":
                raw.append({
                    "date": date_value,
                    "person": r["person_name"],
                    "item": r["item_name_snapshot"],
                    "short_label": r["item_short_label_snapshot"],
                    "quantity": qty,
                    "revenue_eur": total,
                    "cost_eur": purchase_total,
                    "profit_eur": total - purchase_total,
                    "vk_value_eur": total,
                })
            else:  # profit
                if kind == "ROUND_DEDUCTED":
                    cost = abs(purchase_total)
                    raw.append({
                        "date": date_value,
                        "person": r["person_name"],
                        "item": r["item_name_snapshot"],
                        "short_label": r["item_short_label_snapshot"],
                        "quantity": qty,
                        "revenue_eur": 0,
                        "cost_eur": cost,
                        "profit_eur": -cost,
                        "vk_value_eur": abs(total),
                    })
                else:
                    raw.append({
                        "date": date_value,
                        "person": r["person_name"],
                        "item": r["item_name_snapshot"],
                        "short_label": r["item_short_label_snapshot"],
                        "quantity": qty,
                        "revenue_eur": total,
                        "cost_eur": purchase_total,
                        "profit_eur": total - purchase_total,
                        "vk_value_eur": total,
                    })

    grouped: dict[tuple, dict] = {}
    for row in raw:
        key = tuple(row.get(col, "") for col in group_cols)
        if key not in grouped:
            grouped[key] = {col: row.get(col, "") for col in group_cols}
            grouped[key].update({"quantity": 0, "revenue_eur": 0.0, "cost_eur": 0.0, "profit_eur": 0.0, "vk_value_eur": 0.0})
        add_metric_row(grouped[key], row)

    headers = group_cols + ["quantity", "vk_value_eur", "revenue_eur", "cost_eur", "profit_eur"]
    out_rows = []
    for key, row in sorted(grouped.items(), key=lambda item: tuple(str(v).lower() for v in item[0])):
        out_rows.append(
            [row.get(col, "") for col in group_cols]
            + [
                int(row["quantity"]),
                decimal_comma(row['vk_value_eur']),
                decimal_comma(row['revenue_eur']),
                decimal_comma(row['cost_eur']),
                decimal_comma(row['profit_eur']),
            ]
        )
    if not group_cols:
        headers = ["quantity", "vk_value_eur", "revenue_eur", "cost_eur", "profit_eur"]
        if out_rows:
            out_rows = [out_rows[0][-5:]]
    return headers, out_rows


def clean_report_date(value: str | None) -> str | None:
    raw = (value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return raw
    return None


def statistics_scope(conn: sqlite3.Connection, req: StatisticsRequest) -> dict:
    scope = (req.scope or "today").strip().lower()
    today = today_text()
    if scope == "event":
        last_cashup = conn.execute(
            "SELECT timestamp FROM transactions WHERE type = 'CASHUP' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return {
            "scope": "event",
            "label": "Aktuelle Strichliste",
            "date_from": None,
            "date_to": None,
            "since_timestamp": last_cashup["timestamp"] if last_cashup else None,
        }
    if scope == "month":
        return {
            "scope": "month",
            "label": "Dieser Monat",
            "date_from": f"{today[:8]}01",
            "date_to": today,
            "since_timestamp": None,
        }
    if scope == "all":
        return {"scope": "all", "label": "Gesamt", "date_from": None, "date_to": None, "since_timestamp": None}
    if scope == "custom":
        date_from = clean_report_date(req.date_from)
        date_to = clean_report_date(req.date_to)
        if date_from and date_to and date_from > date_to:
            date_from, date_to = date_to, date_from
        label = "Benutzerdefiniert"
        if date_from and date_to:
            label = f"{date_from} bis {date_to}"
        elif date_from:
            label = f"ab {date_from}"
        elif date_to:
            label = f"bis {date_to}"
        return {"scope": "custom", "label": label, "date_from": date_from, "date_to": date_to, "since_timestamp": None}
    return {"scope": "today", "label": "Heute", "date_from": today, "date_to": today, "since_timestamp": None}


def rounded_money(value: float) -> float:
    return round(float(value or 0), 2)


def timestamp_in_statistics_scope(timestamp: str, period: dict) -> bool:
    ts = str(timestamp or "")
    since = period.get("since_timestamp")
    if since:
        return ts > str(since)
    date_value = ts[:10]
    return date_in_range(date_value, period.get("date_from"), period.get("date_to"))


def statistics_timestamp_where(alias: str, period: dict) -> tuple[str, list[str]]:
    parts: list[str] = []
    params: list[str] = []
    since = period.get("since_timestamp")
    if since:
        parts.append(f"{alias}.timestamp > ?")
        params.append(str(since))
    else:
        date_from = period.get("date_from")
        date_to = period.get("date_to")
        if date_from:
            parts.append(f"{alias}.timestamp >= ?")
            params.append(f"{date_from} 00:00:00")
        if date_to:
            parts.append(f"{alias}.timestamp <= ?")
            params.append(f"{date_to} 23:59:59")
    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), params


def statistics_item_visible(row: sqlite3.Row, include_admin_items: bool) -> bool:
    if include_admin_items:
        return True
    if bool(row_get(row, "current_admin_only", row_get(row, "admin_only_snapshot", 0))):
        return False
    return not is_system_item_name(str(row_get(row, "item_name_snapshot", "")))


def empty_stat_bucket() -> dict:
    return {"quantity": 0, "vk_value_eur": 0.0, "revenue_eur": 0.0, "cost_eur": 0.0, "profit_eur": 0.0}


@app.post("/api/admin/statistics")
def admin_statistics(req: StatisticsRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        period = statistics_scope(conn, req)
        include_admin_items = bool(req.include_admin_items)

        kpis = empty_stat_bucket()
        top_items: dict[str, dict] = {}
        finance_by_date: dict[str, dict] = {}
        ti_where, ti_params = statistics_timestamp_where("ti", period)

        consumption_rows = conn.execute(
            f"""
            SELECT ti.*, COALESCE(i.admin_only, 0) AS current_admin_only,
                   COALESCE(p.name, 'System/Admin') AS person_name,
                   p.first_name, p.last_name
            FROM transaction_items ti
            LEFT JOIN items i ON i.id = ti.item_id
            LEFT JOIN people p ON p.id = ti.person_id
            WHERE ti.kind = 'CONSUME'
            {ti_where}
            ORDER BY ti.timestamp ASC, ti.id ASC
            """,
            ti_params,
        ).fetchall()
        for row in consumption_rows:
            if not timestamp_in_statistics_scope(row["timestamp"], period):
                continue
            if not statistics_item_visible(row, include_admin_items):
                continue
            qty = int(row["quantity"] or 0)
            if qty <= 0:
                continue
            total = float(row["total_eur"] or 0)
            cost = float(row["purchase_total_eur"] or 0)
            key = f"{row['item_name_snapshot']}|{row['item_short_label_snapshot']}"
            item = top_items.setdefault(
                key,
                {
                    "item": row["item_name_snapshot"],
                    "short_label": row["item_short_label_snapshot"],
                    **empty_stat_bucket(),
                },
            )
            item["quantity"] += qty
            item["vk_value_eur"] += total
            item["cost_eur"] += cost
            item["profit_eur"] += total - cost
            kpis["quantity"] += qty
            kpis["vk_value_eur"] += total

        finance_rows = conn.execute(
            f"""
            SELECT ti.*, COALESCE(i.admin_only, 0) AS current_admin_only
            FROM transaction_items ti
            LEFT JOIN items i ON i.id = ti.item_id
            WHERE ti.kind IN ('PAID_CASH', 'PAID_SUMUP', 'ROUND_DEDUCTED')
            {ti_where}
            ORDER BY ti.timestamp ASC, ti.id ASC
            """,
            ti_params,
        ).fetchall()
        for row in finance_rows:
            if not timestamp_in_statistics_scope(row["timestamp"], period):
                continue
            if not statistics_item_visible(row, include_admin_items):
                continue
            kind = row["kind"]
            if kind == "ROUND_DEDUCTED":
                revenue = 0.0
                cost = abs(float(row["purchase_total_eur"] or 0))
                profit = -cost
                vk_value = abs(float(row["total_eur"] or 0))
            else:
                revenue = float(row["total_eur"] or 0)
                cost = float(row["purchase_total_eur"] or 0)
                profit = float(row["profit_eur"] or (revenue - cost))
                vk_value = revenue
            date_value = str(row["timestamp"])[:10]
            day = finance_by_date.setdefault(date_value, {"date": date_value, "revenue_eur": 0.0, "cost_eur": 0.0, "profit_eur": 0.0, "vk_value_eur": 0.0})
            day["revenue_eur"] += revenue
            day["cost_eur"] += cost
            day["profit_eur"] += profit
            day["vk_value_eur"] += vk_value
            kpis["revenue_eur"] += revenue
            kpis["cost_eur"] += cost
            kpis["profit_eur"] += profit

        open_people: dict[int, dict] = {}
        open_summary = {"items": 0, "total_eur": 0.0, "cost_eur": 0.0, "profit_eur": 0.0}
        event_summary = {"items": 0, "total_eur": 0.0, "cost_eur": 0.0, "profit_eur": 0.0}
        open_rows = conn.execute(
            """
            SELECT ol.*, p.name AS person_name, p.first_name, p.last_name, p.archived_at
            FROM order_lines ol
            LEFT JOIN people p ON p.id = ol.person_id
            WHERE ol.quantity > 0
            ORDER BY p.last_name ASC, p.first_name ASC, ol.item_name_snapshot ASC
            """
        ).fetchall()
        for row in open_rows:
            qty = int(row["quantity"] or 0)
            total = qty * float(row["unit_price_eur"] or 0)
            cost = qty * float(row["unit_purchase_price_eur"] or 0)
            open_summary["items"] += qty
            open_summary["total_eur"] += total
            open_summary["cost_eur"] += cost
            open_summary["profit_eur"] += total - cost
            person_id = int(row["person_id"])
            person = open_people.setdefault(
                person_id,
                {
                    "person_id": person_id,
                    "person": display_name(row["first_name"], row["last_name"]) or row["person_name"] or "Unbekannt",
                    "archived": row["archived_at"] is not None,
                    "open_items": 0,
                    "open_total_eur": 0.0,
                    "open_cost_eur": 0.0,
                    "open_profit_eur": 0.0,
                },
            )
            person["open_items"] += qty
            person["open_total_eur"] += total
            person["open_cost_eur"] += cost
            person["open_profit_eur"] += total - cost
            if int(row["event_open"] or 0) == 1:
                event_summary["items"] += qty
                event_summary["total_eur"] += total
                event_summary["cost_eur"] += cost
                event_summary["profit_eur"] += total - cost

        rounds = {
            "count": 0,
            "round_price_eur": 0.0,
            "deducted_vk_eur": 0.0,
            "deducted_purchase_eur": 0.0,
            "profit_vs_purchase_eur": 0.0,
            "profit_vs_retail_eur": 0.0,
        }
        round_rows = conn.execute(
            f"""
            SELECT timestamp, round_price_eur, deducted_vk_eur, deducted_purchase_eur,
                   profit_vs_purchase_eur, profit_vs_retail_eur
            FROM round_events
            WHERE 1 = 1
            {statistics_timestamp_where("round_events", period)[0]}
            ORDER BY timestamp ASC, id ASC
            """,
            statistics_timestamp_where("round_events", period)[1],
        ).fetchall()
        for row in round_rows:
            if float(row["round_price_eur"] or 0) > 0:
                rounds["count"] += 1
            rounds["round_price_eur"] += float(row["round_price_eur"] or 0)
            rounds["deducted_vk_eur"] += float(row["deducted_vk_eur"] or 0)
            rounds["deducted_purchase_eur"] += float(row["deducted_purchase_eur"] or 0)
            rounds["profit_vs_purchase_eur"] += float(row["profit_vs_purchase_eur"] or 0)
            rounds["profit_vs_retail_eur"] += float(row["profit_vs_retail_eur"] or 0)

        change_requests = conn.execute("SELECT status, COUNT(*) AS c FROM change_requests GROUP BY status").fetchall()
        round_requests = conn.execute("SELECT status, COUNT(*) AS c FROM round_requests GROUP BY status").fetchall()
        requests = {"delete": {}, "round": {}, "pending_total": 0}
        for row in change_requests:
            requests["delete"][row["status"]] = int(row["c"])
        for row in round_requests:
            requests["round"][row["status"]] = int(row["c"])
        requests["pending_total"] = int(requests["delete"].get("PENDING", 0)) + int(requests["round"].get("PENDING", 0))
        item_details = [
            {**item, "vk_value_eur": rounded_money(item["vk_value_eur"]), "cost_eur": rounded_money(item["cost_eur"]), "profit_eur": rounded_money(item["profit_eur"])}
            for item in sorted(top_items.values(), key=lambda r: (-int(r["quantity"]), -float(r["vk_value_eur"]), str(r["item"]).lower()))
        ]

        return {
            "period": {**period, "include_admin_items": include_admin_items},
            "kpis": {key: rounded_money(value) if key.endswith("_eur") else int(value) for key, value in kpis.items()},
            "open": {key: rounded_money(value) if key.endswith("_eur") else int(value) for key, value in open_summary.items()},
            "event": {key: rounded_money(value) if key.endswith("_eur") else int(value) for key, value in event_summary.items()},
            "top_items": item_details[:8],
            "item_details": item_details,
            "open_people": [
                {
                    **person,
                    "open_total_eur": rounded_money(person["open_total_eur"]),
                    "open_cost_eur": rounded_money(person["open_cost_eur"]),
                    "open_profit_eur": rounded_money(person["open_profit_eur"]),
                }
                for person in sorted(open_people.values(), key=lambda r: (-float(r["open_total_eur"]), str(r["person"]).lower()))[:12]
            ],
            "finance_by_date": [
                {
                    "date": row["date"],
                    "revenue_eur": rounded_money(row["revenue_eur"]),
                    "cost_eur": rounded_money(row["cost_eur"]),
                    "profit_eur": rounded_money(row["profit_eur"]),
                    "vk_value_eur": rounded_money(row["vk_value_eur"]),
                }
                for row in sorted(finance_by_date.values(), key=lambda r: r["date"])
            ],
            "rounds": {key: rounded_money(value) if key.endswith("_eur") else int(value) for key, value in rounds.items()},
            "requests": requests,
        }


@app.post("/api/admin/report/preview")
def report_preview(req: ReportRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        headers, rows = build_report_rows(conn, req)
        return {"headers": headers, "rows": rows}


@app.post("/api/admin/export/report")
def export_report(req: ReportRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        headers, rows = build_report_rows(conn, req)
        safe_type = re.sub(r"[^a-z0-9_-]+", "_", (req.report_type or "report").lower())
        safe_group = re.sub(r"[^a-z0-9_-]+", "_", (req.group_by or "group").lower())
        return csv_response(f"report_{safe_type}_{safe_group}.csv", headers, rows)


@app.post("/api/admin/export/transactions")
def export_transactions(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        rows = conn.execute(
            """
            SELECT t.id, t.timestamp, t.type, COALESCE(p.name, 'System/Admin') AS name, t.total, COALESCE(t.details, '') AS details
            FROM transactions t
            LEFT JOIN people p ON p.id = t.person_id
            ORDER BY t.id ASC
            """
        ).fetchall()
        return csv_response(
            "transactions.csv",
            ["id", "timestamp", "type", "person", "total_eur", "details"],
            [[r["id"], r["timestamp"], r["type"], r["name"], decimal_comma(r['total']), normalize_decimal_text(r["details"])] for r in rows],
        )


@app.post("/api/admin/export/open-balances")
def export_open_balances(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        people = conn.execute("SELECT * FROM people ORDER BY name ASC").fetchall()
        out = []
        for person in people:
            lines = get_open_lines(conn, person["id"])
            if not lines:
                continue
            out.append([
                person["id"],
                display_name(person["first_name"], person["last_name"]) or person["name"],
                "yes" if person["archived_at"] else "no",
                sum(int(line["quantity"]) for line in lines),
                decimal_comma(person_total_from_lines(lines)),
            ])
        return csv_response("open_balances.csv", ["person_id", "person", "archived", "open_items", "open_total_eur"], out)


@app.post("/api/admin/export/open-lines")
def export_open_lines(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        rows = conn.execute(
            """
            SELECT ol.*, COALESCE(p.name, 'Gelöschte Person') AS person_name
            FROM order_lines ol
            LEFT JOIN people p ON p.id = ol.person_id
            WHERE ol.quantity > 0
            ORDER BY p.name, ol.consumed_date, ol.id
            """
        ).fetchall()
        return csv_response(
            "open_lines.csv",
            ["line_id", "person", "item", "short_label", "quantity", "unit_price_eur", "unit_purchase_price_eur", "subtotal_eur", "purchase_total_eur", "potential_profit_eur", "consumed_date", "admin_only"],
            [
                [
                    r["id"],
                    r["person_name"],
                    r["item_name_snapshot"],
                    r["item_short_label_snapshot"],
                    r["quantity"],
                    decimal_comma(r['unit_price_eur']),
                    decimal_comma(r['unit_purchase_price_eur'] if 'unit_purchase_price_eur' in r.keys() else 0),
                    decimal_comma(int(r['quantity']) * float(r['unit_price_eur'])),
                    decimal_comma(int(r['quantity']) * float(r['unit_purchase_price_eur'] if 'unit_purchase_price_eur' in r.keys() else 0)),
                    decimal_comma(int(r['quantity']) * (float(r['unit_price_eur']) - float(r['unit_purchase_price_eur'] if 'unit_purchase_price_eur' in r.keys() else 0))),
                    r["consumed_date"],
                    "yes" if r["admin_only_snapshot"] else "no",
                ]
                for r in rows
            ],
        )


@app.post("/api/admin/export/item-summary")
def export_item_summary(req: PinRequest):
    with get_conn() as conn:
        require_pin(conn, req.pin)
        paid_rows = conn.execute(
            """
            SELECT
                kind,
                item_name_snapshot,
                item_short_label_snapshot,
                unit_price_eur,
                unit_purchase_price_eur,
                SUM(quantity) AS qty,
                SUM(total_eur) AS total,
                SUM(purchase_total_eur) AS purchase_total,
                SUM(profit_eur) AS profit_total
            FROM transaction_items
            GROUP BY kind, item_name_snapshot, item_short_label_snapshot, unit_price_eur, unit_purchase_price_eur
            """
        ).fetchall()
        open_rows = conn.execute(
            """
            SELECT
                'OPEN' AS kind,
                item_name_snapshot,
                item_short_label_snapshot,
                unit_price_eur,
                unit_purchase_price_eur,
                SUM(quantity) AS qty,
                SUM(quantity * unit_price_eur) AS total,
                SUM(quantity * unit_purchase_price_eur) AS purchase_total,
                SUM(quantity * (unit_price_eur - unit_purchase_price_eur)) AS profit_total
            FROM order_lines
            WHERE quantity > 0
            GROUP BY item_name_snapshot, item_short_label_snapshot, unit_price_eur, unit_purchase_price_eur
            """
        ).fetchall()
        rows = list(paid_rows) + list(open_rows)
        rows = sorted(rows, key=lambda r: (r["kind"], r["item_name_snapshot"], float(r["unit_price_eur"])))
        return csv_response(
            "item_summary.csv",
            ["status", "item", "short_label", "unit_price_eur", "unit_purchase_price_eur", "quantity", "total_eur", "purchase_total_eur", "profit_eur"],
            [
                [
                    r["kind"],
                    r["item_name_snapshot"],
                    r["item_short_label_snapshot"],
                    decimal_comma(r['unit_price_eur']),
                    decimal_comma(r['unit_purchase_price_eur']),
                    r["qty"],
                    decimal_comma(r['total']),
                    decimal_comma(r['purchase_total']),
                    decimal_comma(r['profit_total']),
                ]
                for r in rows
            ],
        )
