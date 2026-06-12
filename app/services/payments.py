"""Payment service helpers."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

try:
    from app.config import CARD_PAYMENT_FEE_RATE_PERCENT, CARD_PAYMENT_MIN_FEE_CENTS, CARD_PAYMENT_ROUNDING_STEPS
    from app.models.responses import CardPaymentBreakdown
    from app.services import orders
    from app.utils.helpers import now_text
except ImportError:
    from config import CARD_PAYMENT_FEE_RATE_PERCENT, CARD_PAYMENT_MIN_FEE_CENTS, CARD_PAYMENT_ROUNDING_STEPS
    from models.responses import CardPaymentBreakdown
    from services import orders
    from utils.helpers import now_text


class PaymentError(RuntimeError):
    """Raised when a payment cannot be completed."""


@dataclass(slots=True)
class PaymentResult:
    status: str
    person_id: int
    total_eur: float
    paid_items: int
    transaction_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "person_id": self.person_id,
            "total_eur": self.total_eur,
            "paid_items": self.paid_items,
            "transaction_id": self.transaction_id,
        }


def eur_cents(value: float) -> int:
    """Convert EUR to non-negative cents."""

    return max(0, int(round(float(value or 0) * 100)))


def cents_to_eur(cents: int) -> float:
    """Convert cents to EUR rounded to two decimals."""

    return round(int(cents or 0) / 100, 2)


def card_payment_fee_cents(base_cents: int) -> int:
    """Return the configured card fee in cents."""

    base = max(0, int(base_cents or 0))
    if base <= 0:
        return 0
    return max(CARD_PAYMENT_MIN_FEE_CENTS, (base * CARD_PAYMENT_FEE_RATE_PERCENT + 99) // 100)


def normalize_card_rounding_mode(mode: str | None) -> str:
    """Validate and normalize a card rounding mode."""

    normalized = str(mode or "none").strip().lower()
    if normalized not in CARD_PAYMENT_ROUNDING_STEPS:
        raise PaymentError("Invalid card rounding mode")
    return normalized


def card_payment_breakdown(base_total: float, rounding_mode: str | None = "none") -> CardPaymentBreakdown:
    """Calculate card payment amount, fee, and optional round-up."""

    normalized_mode = normalize_card_rounding_mode(rounding_mode)
    base_amount_cents = eur_cents(base_total)
    card_fee_cents = card_payment_fee_cents(base_amount_cents)
    subtotal_cents = base_amount_cents + card_fee_cents
    step_cents = CARD_PAYMENT_ROUNDING_STEPS[normalized_mode]
    rounded_total_cents = subtotal_cents if step_cents <= 1 else ((subtotal_cents + step_cents - 1) // step_cents) * step_cents
    rounding_adjustment_cents = rounded_total_cents - subtotal_cents
    return CardPaymentBreakdown(
        base_amount_cents=base_amount_cents,
        base_total_eur=cents_to_eur(base_amount_cents),
        card_fee_cents=card_fee_cents,
        card_fee_eur=cents_to_eur(card_fee_cents),
        rounding_mode=normalized_mode,
        rounding_adjustment_cents=rounding_adjustment_cents,
        rounding_adjustment_eur=cents_to_eur(rounding_adjustment_cents),
        amount_cents=rounded_total_cents,
        amount_eur=cents_to_eur(rounded_total_cents),
    )


def rounding_options_for_breakdown(breakdown: CardPaymentBreakdown) -> list[dict[str, Any]]:
    """Return selectable rounding options for a card payment preview."""

    payable_cents = breakdown.base_amount_cents + breakdown.card_fee_cents
    options = [{"mode": "none", "target_cents": payable_cents, "add_cents": 0, "label": "No rounding"}]
    seen = {payable_cents}
    for mode in ("euro", "five", "ten"):
        step = CARD_PAYMENT_ROUNDING_STEPS[mode]
        target = ((payable_cents + step - 1) // step) * step
        if target in seen:
            continue
        seen.add(target)
        options.append({"mode": mode, "target_cents": target, "add_cents": target - payable_cents, "label": mode})
    return options


def process_cash_payment(conn: sqlite3.Connection, person_id: int) -> PaymentResult:
    """Close a person's open lines as a cash payment."""

    lines = orders.get_open_lines(conn, person_id)
    total = round(sum(int(line["quantity"] or 0) * float(line["unit_price_eur"] or 0) for line in lines), 2)
    if total <= 0:
        raise PaymentError("No payable open lines")
    now = now_text()
    cur = conn.execute(
        "INSERT INTO transactions (person_id, type, total, details, timestamp) VALUES (?, ?, ?, ?, ?)",
        (person_id, "PAID_CASH", total, "Cash payment", now),
    )
    conn.execute(
        "UPDATE order_lines SET quantity = 0, updated_at = ? WHERE person_id = ? AND quantity > 0 AND event_open = 1",
        (now, person_id),
    )
    return PaymentResult("paid", person_id, total, sum(int(line["quantity"] or 0) for line in lines), int(cur.lastrowid))


def mark_self_payment_session(
    conn: sqlite3.Connection,
    client_payment_id: str,
    status: str,
    error: str | None = None,
) -> None:
    """Update a self-payment session by client payment id."""

    conn.execute(
        "UPDATE self_payment_sessions SET status = ?, error = ?, updated_at = ? WHERE client_payment_id = ?",
        (status, error, now_text(), client_payment_id),
    )


def self_payment_session_by_client_id(conn: sqlite3.Connection, client_id: str | None) -> sqlite3.Row | None:
    """Return the latest self-payment session for a client id."""

    if not client_id:
        return None
    return conn.execute(
        "SELECT * FROM self_payment_sessions WHERE client_payment_id = ? ORDER BY id DESC LIMIT 1",
        (client_id,),
    ).fetchone()


def expire_stale_self_payment_sessions(conn: sqlite3.Connection) -> int:
    """Expire stale sessions.

    The legacy timeout rules are still richer; this conservative implementation
    marks only sessions older than one hour that are still pending.
    """

    cur = conn.execute(
        """
        UPDATE self_payment_sessions
        SET status = 'EXPIRED', updated_at = ?
        WHERE status IN ('CREATED', 'SENT_TO_READER', 'PENDING')
          AND datetime(created_at) < datetime('now', '-1 hour')
        """,
        (now_text(),),
    )
    return int(cur.rowcount or 0)
