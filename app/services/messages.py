"""Editable UI message catalog service."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any


APP_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MESSAGES_PATH = APP_DIR / "messages.json"
DEFAULT_DB_PATH = "/app/data/drink_pos.db"


def runtime_messages_path(db_path: str | os.PathLike[str] | None = None) -> Path:
    """Return the editable message catalog path for the active runtime."""

    override = os.getenv("DRINK_POS_MESSAGES")
    if override:
        return Path(override)
    resolved_db_path = Path(db_path or os.getenv("DRINK_POS_DB") or DEFAULT_DB_PATH)
    return resolved_db_path.parent / "messages.json"


def read_message_file(path: Path) -> dict[str, Any]:
    """Read one message JSON file and ignore invalid optional overrides."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def ensure_messages_file(db_path: str | os.PathLike[str] | None = None) -> None:
    """Create a persistent editable message catalog when missing."""

    target = runtime_messages_path(db_path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() and DEFAULT_MESSAGES_PATH.exists():
            target.write_text(DEFAULT_MESSAGES_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    except OSError:
        # Message overrides are optional; bundled defaults remain available.
        return


def load_message_catalog(db_path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Load bundled messages with persistent runtime overrides."""

    defaults = read_message_file(DEFAULT_MESSAGES_PATH)
    target = runtime_messages_path(db_path)
    if target == DEFAULT_MESSAGES_PATH:
        return defaults
    overrides = read_message_file(target)
    return {**defaults, **overrides}


class MessageValues(dict):
    """Placeholder mapping that keeps unknown placeholders visible."""

    def __missing__(self, key):
        return "{" + key + "}"


def message_text(
    key: str,
    default: str = "",
    *,
    db_path: str | os.PathLike[str] | None = None,
    values: Mapping[str, Any] | None = None,
) -> str:
    """Return an editable message value with optional placeholder replacement."""

    raw = load_message_catalog(db_path).get(key, default)
    text = str(raw if raw is not None else default)
    try:
        return text.format_map(MessageValues(values or {}))
    except (KeyError, ValueError):
        return text
