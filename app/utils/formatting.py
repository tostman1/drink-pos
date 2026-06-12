"""Formatting helpers for display labels, money, and colors."""

from __future__ import annotations

import re

try:
    from app.config import CARD_PAYMENT_ROUNDING_STEPS, SYSTEM_ITEM_NAMES
except ImportError:
    from config import CARD_PAYMENT_ROUNDING_STEPS, SYSTEM_ITEM_NAMES


def normalize_for_sort(text: str) -> str:
    """Normalize German-ish text for deterministic alphabetical sorting."""

    return (
        str(text or "")
        .lower()
        .replace("\u00e4", "ae")
        .replace("\u00f6", "oe")
        .replace("\u00fc", "ue")
        .replace("\u00df", "ss")
    )


def decimal_comma(value, places: int = 2) -> str:
    """Format a number with a comma decimal separator."""

    return f"{float(value):.{places}f}".replace(".", ",")


def eur_text(value) -> str:
    """Format a numeric value as an EUR display string."""

    return f"EUR {decimal_comma(value)}"


def normalize_decimal_text(value) -> str:
    """Convert decimal points in money-like text fragments to commas."""

    return re.sub(r"(EUR\s*-?\d+)\.(\d{1,2})(?=\D|$)", r"\1,\2", str(value or ""))


def short_label_from_name(name: str) -> str:
    """Create a short fallback label from an item name."""

    words = re.findall(r"\w+", name or "", flags=re.UNICODE)
    if not words:
        return "?"
    if len(words) >= 2 and words[0].lower() == "bier":
        return words[1].capitalize()
    return "".join(word[0].upper() for word in words)[:5]


def normalize_hex_color(value: str | None, default: str) -> str:
    """Return a normalized #RRGGBB color or the provided default."""

    raw = (value or default or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", raw):
        return raw.lower()
    if re.fullmatch(r"[0-9A-Fa-f]{6}", raw):
        return f"#{raw.lower()}"
    return default


def card_rounding_label(mode: str | None) -> str:
    """Return a human label for a card rounding mode."""

    normalized = str(mode or "none").strip().lower()
    if normalized not in CARD_PAYMENT_ROUNDING_STEPS:
        normalized = "none"
    return {
        "euro": "full euro",
        "five": "next 5",
        "ten": "next 10",
    }.get(normalized, "no rounding")


def is_system_item_name(name: str | None) -> bool:
    """Return whether a display name belongs to a reserved system item."""

    return (name or "").strip().lower() in {item.lower() for item in SYSTEM_ITEM_NAMES}
