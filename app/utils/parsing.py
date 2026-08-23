"""Parsing helpers for names, decimal values, dates, and settings."""

from __future__ import annotations

from datetime import datetime


def split_name(full_name: str) -> tuple[str, str]:
    """Split a legacy 'last first' name into (first_name, last_name)."""

    clean = " ".join((full_name or "").strip().split())
    if not clean:
        return "", ""
    parts = clean.split(" ", 1)
    if len(parts) == 1:
        return "", parts[0]
    return parts[1], parts[0]


def display_name(first_name: str, last_name: str) -> str:
    """Return the display form used by the current UI."""

    first = (first_name or "").strip()
    last = (last_name or "").strip()
    return " ".join(part for part in [last, first] if part)


def parse_decimal_value(value, field_name: str = "value") -> float:
    """Parse German comma or technical dot decimal notation."""

    if value is None:
        raise ValueError(f"{field_name} is required")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("EUR", "").replace(" ", "").replace("\u00a0", "")
    if not text:
        raise ValueError(f"{field_name} is required")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid number") from exc


def parse_timeout_value(value: str | int | None, default: int = 30) -> int:
    """Parse a timeout setting and clamp it to a practical range."""

    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(1, min(parsed, 300))


def parse_db_timestamp(value: str | None) -> datetime | None:
    """Parse a database timestamp written as '%Y-%m-%d %H:%M:%S'."""

    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def parse_bool_setting(value: object, default: bool = False) -> bool:
    """Parse database and environment boolean values."""

    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
