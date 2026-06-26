"""Security helpers for admin and agent access."""

from __future__ import annotations

import os
import sqlite3

from fastapi import HTTPException

try:
    from app.utils.helpers import get_setting
except ImportError:
    from utils.helpers import get_setting


DEFAULT_ADMIN_PIN = "1234"
DEFAULT_PIN_PRODUCTION_ERROR = (
    "Standard-PIN 1234 ist in Produktion gesperrt. Bitte DRINK_POS_PIN setzen "
    "oder die PIN in einer lokalen Entwicklungsumgebung ändern."
)


def configured_env_pin() -> str:
    """Return the configured admin PIN fallback from the current environment."""

    raw = os.getenv("DRINK_POS_PIN")
    return (raw or DEFAULT_ADMIN_PIN).strip() or DEFAULT_ADMIN_PIN


def is_production_env() -> bool:
    """Return whether the current process environment is production-like."""

    return os.getenv("DRINK_POS_ENV", "development").strip().lower() in {"prod", "production"}


def configured_admin_pin(conn: sqlite3.Connection, env_pin: str | None = None) -> str:
    """Return the stored admin PIN with environment fallback."""

    fallback = (env_pin or configured_env_pin()).strip() or DEFAULT_ADMIN_PIN
    return get_setting(conn, "admin_pin", fallback) or fallback


def ensure_admin_login_allowed(
    conn: sqlite3.Connection,
    *,
    production: bool | None = None,
    env_pin: str | None = None,
) -> None:
    """Block the default PIN in production."""

    active_production = is_production_env() if production is None else production
    if active_production and configured_admin_pin(conn, env_pin) == DEFAULT_ADMIN_PIN:
        raise HTTPException(status_code=403, detail=DEFAULT_PIN_PRODUCTION_ERROR)


def require_pin(
    conn: sqlite3.Connection,
    pin: str,
    *,
    production: bool | None = None,
    env_pin: str | None = None,
) -> None:
    """Validate an admin PIN and raise the API-compatible HTTP error."""

    active_production = is_production_env() if production is None else production
    configured = configured_admin_pin(conn, env_pin)
    if active_production and configured == DEFAULT_ADMIN_PIN:
        raise HTTPException(status_code=403, detail=DEFAULT_PIN_PRODUCTION_ERROR)
    if pin != configured:
        raise HTTPException(status_code=403, detail="Falsche PIN")
