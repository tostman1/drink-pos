"""Build metadata exposed safely to the app and admin UI."""

from __future__ import annotations

import os


BUILD_COMMIT_ENV = "APP_BUILD_COMMIT"
BUILD_REF_ENV = "APP_BUILD_REF"
BUILD_CHANNEL_ENV = "APP_BUILD_CHANNEL"
BUILD_TAGS_ENV = "APP_BUILD_TAGS"
RUNTIME_IMAGE_REF_ENV = "DRINK_POS_IMAGE_REF"
LOCAL_BUILD_COMMIT = "local-dev"


def build_commit() -> str:
    """Return the container build commit or a safe local-development fallback."""

    value = os.getenv(BUILD_COMMIT_ENV, "").strip()
    return value or LOCAL_BUILD_COMMIT


def short_commit(commit: str | None = None) -> str:
    """Return the compact commit id used in image tags."""

    value = (commit or build_commit()).strip()
    if not value or value == LOCAL_BUILD_COMMIT:
        return value or LOCAL_BUILD_COMMIT
    return value[:7]


def build_tags() -> list[str]:
    """Return build-time image tags stored in the container environment."""

    raw = os.getenv(BUILD_TAGS_ENV, "").strip()
    if not raw:
        return []
    return [part.strip() for part in raw.replace("\n", ",").split(",") if part.strip()]


def image_ref_label(image_ref: str | None) -> str:
    """Extract the tag or digest label from a configured image reference."""

    value = (image_ref or "").strip()
    if not value:
        return ""
    if "@" in value:
        return value.split("@", 1)[1]
    image_name = value.rsplit("/", 1)[-1]
    if ":" in image_name:
        return image_name.rsplit(":", 1)[1]
    return ""


def build_info() -> dict:
    """Return public, non-secret build metadata."""

    commit = build_commit()
    runtime_image_ref = os.getenv(RUNTIME_IMAGE_REF_ENV, "").strip()
    return {
        "commit": commit,
        "short_commit": short_commit(commit),
        "ref": os.getenv(BUILD_REF_ENV, "").strip(),
        "channel": os.getenv(BUILD_CHANNEL_ENV, "").strip(),
        "tags": build_tags(),
        "runtime_image_ref": runtime_image_ref,
        "runtime_image_label": image_ref_label(runtime_image_ref),
    }
