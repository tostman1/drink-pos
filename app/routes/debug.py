"""Debug-only API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

try:
    from app.config import is_production
except ImportError:
    from config import is_production


router = APIRouter()


@router.post("/api/debug/add-test-data")
def add_test_data_disabled() -> dict:
    """Placeholder debug route for the modular router."""

    if is_production():
        raise HTTPException(status_code=404, detail="Debug API is disabled")
    return {"status": "not_implemented_in_modular_router"}
