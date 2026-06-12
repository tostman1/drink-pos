"""Admin API routes."""

from __future__ import annotations

from fastapi import APIRouter

try:
    from app.db.connection import get_conn
    from app.models.requests import PinRequest
    from app.services import statistics
    from app.utils.validation import require_pin
except ImportError:
    from db.connection import get_conn
    from models.requests import PinRequest
    from services import statistics
    from utils.validation import require_pin


router = APIRouter()


@router.post("/api/admin/cashup-preview")
def admin_cashup_preview(req: PinRequest) -> dict:
    """Return a cashup preview."""

    with get_conn() as conn:
        require_pin(conn, req.pin)
        return statistics.calculate_cashup_preview(conn)
