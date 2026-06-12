"""Typed response shapes shared by services and routes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class PaymentResult:
    """Result returned after a successful payment operation."""

    status: str
    person_id: int
    total_eur: float
    paid_items: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class CardPaymentBreakdown:
    """Breakdown of a card payment including fee and rounding."""

    base_amount_cents: int
    base_total_eur: float
    card_fee_cents: int
    card_fee_eur: float
    rounding_mode: str
    rounding_adjustment_cents: int
    rounding_adjustment_eur: float
    amount_cents: int
    amount_eur: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
