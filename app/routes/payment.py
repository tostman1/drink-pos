"""Payment API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

try:
    from app.db.connection import get_conn
    from app.models.requests import PayRequest
    from app.services import payments as payments_service
    from app.utils.validation import require_pin
except ImportError:
    from db.connection import get_conn
    from models.requests import PayRequest
    from services import payments as payments_service
    from utils.validation import require_pin


router = APIRouter()


@router.post("/api/pay")
def pay(req: PayRequest) -> dict:
    """Process a cash payment."""

    try:
        with get_conn() as conn:
            require_pin(conn, req.pin)
            result = payments_service.process_cash_payment(conn, req.person_id)
            conn.commit()
            return result.to_dict()
    except payments_service.PaymentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
