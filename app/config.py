"""Runtime configuration for Drink POS.

This module centralizes environment-derived values and defaults that were
historically declared in the application entrypoint.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final


APP_ENV: Final[str] = os.getenv("DRINK_POS_ENV", "development").strip().lower()
RAW_ENV_PIN_CODE: Final[str | None] = os.getenv("DRINK_POS_PIN")
ENV_PIN_CODE: Final[str] = (RAW_ENV_PIN_CODE or "1234").strip() or "1234"
ENV_PIN_FROM_ENV: Final[bool] = RAW_ENV_PIN_CODE is not None and RAW_ENV_PIN_CODE.strip() != ""
AGENT_API_TOKEN: Final[str] = os.getenv("DRINK_POS_AGENT_TOKEN", "").strip()
APP_DIR: Final[Path] = Path(__file__).resolve().parent

TEST_PAYMENT_APP_ENVS: Final[set[str]] = {"test", "testing"}
TEST_PAYMENT_PROVIDER_ENVS: Final[set[str]] = {"development", "dev", "local", *TEST_PAYMENT_APP_ENVS}
TEST_PAYMENT_PROVIDERS: Final[set[str]] = {"test", "mock", "demo"}
TEST_PAYMENT_FLAG_ENV: Final[str] = "DRINK_POS_ALLOW_TEST_CARD_PAYMENTS"


def default_db_path_for_env(env: str) -> str:
    """Return the default SQLite path for an application environment."""

    normalized = (env or "development").strip().lower()
    if normalized in {"prod", "production"}:
        return "/app/data/drink_pos.db"
    return "/app/data/drink_pos_dev.db"


DB_PATH: Final[str] = os.getenv("DRINK_POS_DB") or default_db_path_for_env(APP_ENV)
DB_PATH_SOURCE: Final[str] = "DRINK_POS_DB" if os.getenv("DRINK_POS_DB") else "environment-default"
DB_TIMEOUT_SECONDS: Final[int] = 15
DB_BUSY_TIMEOUT_MS: Final[int] = 15_000

ADMIN_LOGIN_RATE_WINDOW_SECONDS: Final[int] = 300
ADMIN_LOGIN_RATE_LIMIT: Final[int] = 8

DEFAULT_ITEMS: Final[list[dict[str, object]]] = [
    {"name": "Bier gross", "short_label": "Gross", "price_eur": 2.50, "purchase_price_eur": 1.40, "admin_only": False},
    {"name": "Bier klein", "short_label": "Klein", "price_eur": 1.80, "purchase_price_eur": 1.00, "admin_only": False},
    {"name": "Limo", "short_label": "Limo", "price_eur": 1.00, "purchase_price_eur": 0.45, "admin_only": False},
]

ROUND_ITEM_NAME: Final[str] = "1 Runde"
ROUND_ITEM_SHORT: Final[str] = "Runde"
DEFAULT_ROUND_PRICE_EUR: Final[str] = "10.00"
DEFAULT_COST_WARNING_TEMPLATE: Final[str] = "Offen: {betrag}. Unteres Limit {unteres_limit} erreicht."
DEFAULT_PAYMENT_REMINDER_TEMPLATE: Final[str] = (
    "Offen: {betrag}. Oberes Limit {oberes_limit} erreicht. Bitte bei Gelegenheit bezahlen."
)
SYSTEM_ITEM_NAMES: Final[set[str]] = {ROUND_ITEM_NAME}

PAID_TRANSACTION_TYPES: Final[tuple[str, ...]] = ("PAID_CASH", "PAID_SUMUP")
PAID_TRANSACTION_KINDS: Final[tuple[str, ...]] = PAID_TRANSACTION_TYPES

CARD_PAYMENT_FEE_RATE_PERCENT: Final[int] = 3
CARD_PAYMENT_MIN_FEE_CENTS: Final[int] = 20
CARD_PAYMENT_ROUNDING_STEPS: Final[dict[str, int]] = {
    "none": 1,
    "euro": 100,
    "five": 500,
    "ten": 1000,
}

DEFAULT_NAMES: Final[list[str]] = [
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


def is_system_item_name(name: str | None) -> bool:
    """Return whether an item name is reserved for system behavior."""

    normalized = (name or "").strip().lower()
    return normalized in {item.lower() for item in SYSTEM_ITEM_NAMES}


def is_production(env: str | None = None) -> bool:
    """Return whether the given or configured environment is production."""

    return (env or APP_ENV).strip().lower() in {"prod", "production"}


def database_info() -> dict[str, str]:
    """Return safe database metadata for diagnostic API responses."""

    profile = "production" if is_production() else "development"
    return {
        "source": DB_PATH_SOURCE,
        "profile": profile,
        "path": "hidden" if profile == "production" else DB_PATH,
    }
