"""Public API routes."""

from __future__ import annotations

from fastapi import APIRouter

try:
    from app.db.connection import get_conn
    from app.services import sync as sync_service
except ImportError:
    from db.connection import get_conn
    from services import sync as sync_service


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Return a basic health response."""

    return {"status": "ok"}


@router.get("/api/sync-status")
def sync_status() -> dict:
    """Return the current synchronization revision."""

    with get_conn() as conn:
        return sync_service.get_sync_state(conn)


@router.get("/api/config")
def get_config() -> dict:
    """Return public configuration payload."""

    with get_conn() as conn:
        return sync_service.get_config_payload(conn)
