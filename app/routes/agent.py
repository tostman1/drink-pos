"""Agent API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

try:
    from app.utils.validation import require_agent_access
except ImportError:
    from utils.validation import require_agent_access


router = APIRouter()


@router.get("/api/agent/capabilities")
def agent_capabilities(request: Request) -> dict:
    """Return available agent capabilities."""

    require_agent_access(
        authorization=request.headers.get("authorization"),
        x_drink_pos_agent_token=request.headers.get("x-drink-pos-agent-token"),
    )
    return {"can_book_drink": True, "can_read_state": True, "can_create_round_request": True}
