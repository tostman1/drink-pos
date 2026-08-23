"""Validation helpers shared by routes and services."""

from __future__ import annotations

import os
import re
import secrets
import sqlite3

from fastapi import HTTPException

try:
    from app.config import AGENT_API_TOKEN, ENV_PIN_CODE
    from app.utils.helpers import get_setting
except ImportError:
    from config import AGENT_API_TOKEN, ENV_PIN_CODE
    from utils.helpers import get_setting


class ValidationError(ValueError):
    """Raised when service-level validation fails."""


def configured_admin_pin(conn: sqlite3.Connection) -> str:
    """Return the configured admin PIN with environment fallback."""

    return get_setting(conn, "admin_pin", ENV_PIN_CODE) or ENV_PIN_CODE


def require_pin(conn: sqlite3.Connection, pin: str) -> None:
    """Validate the admin PIN or raise a 403 HTTP error."""

    if pin != configured_admin_pin(conn):
        raise HTTPException(status_code=403, detail="Falsche PIN")


def normalize_client_operation_id(value: str | None) -> str | None:
    """Normalize a client idempotency key."""

    if not value:
        return None
    clean = re.sub(r"[^A-Za-z0-9_.:-]", "", value.strip())[:80]
    return clean or None


def configured_agent_token() -> str:
    """Return the configured agent API token."""

    return (os.getenv("DRINK_POS_AGENT_TOKEN") or AGENT_API_TOKEN or "").strip()


def require_agent_access(authorization: str | None = None, x_drink_pos_agent_token: str | None = None) -> None:
    """Validate an agent API token from headers."""

    expected = configured_agent_token()
    if not expected:
        raise HTTPException(status_code=404, detail="Agent API ist deaktiviert. DRINK_POS_AGENT_TOKEN setzen.")
    provided = ""
    if x_drink_pos_agent_token:
        provided = x_drink_pos_agent_token.strip()
    elif authorization:
        parts = authorization.strip().split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            provided = parts[1].strip()
    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="Ungueltiges Agent-Token")


def validate_person_exists(conn: sqlite3.Connection, person_id: int):
    """Return a person row or raise ValidationError."""

    row = conn.execute("SELECT * FROM people WHERE id = ?", (person_id,)).fetchone()
    if not row:
        raise ValidationError("Person not found")
    return row


def validate_item_exists(conn: sqlite3.Connection, item_id: int):
    """Return an item row or raise ValidationError."""

    row = conn.execute("SELECT * FROM items WHERE id = ? AND archived_at IS NULL", (item_id,)).fetchone()
    if not row:
        raise ValidationError("Item not found")
    return row


def validate_amount_positive(amount: float) -> None:
    """Raise ValidationError when an amount is negative or zero."""

    if float(amount) <= 0:
        raise ValidationError("Amount must be positive")


def validate_payment_request(person_id: int, total_eur: float) -> None:
    """Validate the common requirements for payment execution."""

    if int(person_id) <= 0:
        raise ValidationError("person_id must be positive")
    validate_amount_positive(total_eur)
