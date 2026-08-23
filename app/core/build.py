"""Build metadata exposed safely to the app and admin UI."""

from __future__ import annotations

import os


BUILD_COMMIT_ENV = "APP_BUILD_COMMIT"
LOCAL_BUILD_COMMIT = "local-dev"


def build_commit() -> str:
    """Return the container build commit or a safe local-development fallback."""

    value = os.getenv(BUILD_COMMIT_ENV, "").strip()
    return value or LOCAL_BUILD_COMMIT


def build_info() -> dict[str, str]:
    """Return public, non-secret build metadata."""

    return {"commit": build_commit()}
