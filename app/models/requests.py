"""Request models for the Drink POS API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _positive_or_none(value, field_name: str):
    if value is None:
        return None
    if int(value) <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


class PositiveIdModel(BaseModel):
    """Base model that validates common identifier fields when present."""

    @field_validator("person_id", "item_id", "request_id", "message_id", mode="before", check_fields=False)
    @classmethod
    def _validate_positive_ids(cls, value, info):
        return _positive_or_none(value, info.field_name)


class PinRequest(BaseModel):
    """Request carrying an admin PIN."""

    pin: str

    @field_validator("pin")
    @classmethod
    def validate_pin(cls, value: str) -> str:
        clean = str(value or "").strip()
        if not clean:
            raise ValueError("PIN is required")
        if len(clean) > 64:
            raise ValueError("PIN is too long")
        return clean


class CashupRequest(PinRequest):
    """Request to preview or execute a cashup."""


class AddDrinkRequest(PositiveIdModel):
    person_id: int
    item_id: int | None = None
    drink: str | None = None
    pin: str | None = None
    client_operation_id: str | None = None
    client_time: str | None = None
    device_info: str | None = None
    offline_queued: bool = False


class EditRequestIn(PositiveIdModel):
    person_id: int
    line_quantities: dict[str, int] | None = None
    changes: dict[str, int] | None = None
    reason: str | None = None


class RoundRequestIn(PositiveIdModel):
    person_id: int
    quantity: int = 1
    reason: str | None = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: int) -> int:
        if int(value) <= 0:
            raise ValueError("quantity must be positive")
        return int(value)


class PayRequest(PinRequest, PositiveIdModel):
    person_id: int
    approve_request_ids: list[int] = Field(default_factory=list)
    reject_request_ids: list[int] = Field(default_factory=list)
    approve_pending: bool = False
    reject_pending: bool = False


class KassaPayRequest(PayRequest):
    expected_revision: str


class SelfPayRequest(PositiveIdModel):
    person_id: int
    expected_revision: str
    client_payment_id: str | None = None
    rounding_mode: str = "none"


class SumUpPairReaderRequest(PinRequest):
    pairing_code: str
    name: str | None = "Drink POS"


class MemberMessageAckRequest(PositiveIdModel):
    person_id: int
    message_id: int


class AdminAdjustItemRequest(PinRequest, PositiveIdModel):
    person_id: int
    delta: int
    item_id: int | None = None
    drink: str | None = None


class AdminChangeRequestDecision(PinRequest, PositiveIdModel):
    request_id: int
    decision: Literal["approve", "reject", "APPROVED", "REJECTED"]


class AdminRoundRequestDecision(AdminChangeRequestDecision):
    pass


class AdminPersonCreate(PinRequest):
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None


class AdminPersonUpdate(PinRequest, PositiveIdModel):
    person_id: int
    first_name: str | None = None
    last_name: str | None = None
    name: str | None = None
    active: bool = True


class AdminPersonDelete(PinRequest, PositiveIdModel):
    person_id: int


class AdminMemberMessageCreate(PinRequest):
    title: str | None = None
    message: str
    person_ids: list[int]


class AdminMemberMessageArchive(PinRequest, PositiveIdModel):
    message_id: int


class AdminItemCreate(PinRequest):
    name: str
    short_label: str | None = None
    price: float | str
    purchase_price: float | str = 0
    purchase_price_eur: float | str | None = None
    active: bool = True
    admin_only: bool = False
    sort_order: int | None = None


class AdminItemUpdate(AdminItemCreate, PositiveIdModel):
    item_id: int | None = None
    old_name: str | None = None
    sort_order: int = 100


class AdminItemDelete(PinRequest, PositiveIdModel):
    item_id: int


class SettingsUpdateRequest(PinRequest):
    new_pin: str | None = None
    round_item_price_eur: float | str | None = None
    show_total_on_overview: bool | None = None
    show_person_popup_total: bool | None = None
    app_name: str | None = None
    tally_roughness: int | None = None
    overview_name_size_px: float | None = None
    overview_summary_size_percent: int | None = None
    show_summary_label_on_overview: bool | None = None
    overview_summary_label_text: str | None = None
    tally_size_percent: int | None = None
    show_sync_status: bool | None = None
    sync_status_size_percent: int | None = None
    enable_delete_requests: bool | None = None
    app_background_color: str | None = None
    person_card_background_color: str | None = None
    person_card_border_color: str | None = None
    person_card_border_width_px: int | None = None
    person_card_gap_px: int | None = None
    drink_feedback_enabled: bool | None = None
    drink_feedback_style: str | None = None
    drink_feedback_duration_ms: int | None = None
    drink_feedback_animation_intensity_percent: int | None = None
    drink_feedback_position: str | None = None
    drink_booking_sound_enabled: bool | None = None
    drink_booking_sound_preset: str | None = None
    drink_celebration_mode: str | None = None
    drink_celebration_condition_round: bool | None = None
    drink_celebration_condition_debt: bool | None = None
    drink_celebration_debt_threshold_eur: float | str | None = None
    drink_celebration_confetti_intensity_percent: int | None = None
    drink_celebration_sound_enabled: bool | None = None
    cost_warning_enabled: bool | None = None
    cost_warning_threshold_eur: float | str | None = None
    cost_warning_template: str | None = None
    cost_warning_show_on_overview: bool | None = None
    cost_warning_show_in_popup: bool | None = None
    payment_reminder_enabled: bool | None = None
    payment_reminder_threshold_eur: float | str | None = None
    payment_reminder_template: str | None = None
    payment_reminder_show_on_overview: bool | None = None
    payment_reminder_show_in_popup: bool | None = None
    cost_notice_show_on_overview: bool | None = None
    cost_notice_show_in_popup: bool | None = None
    member_messages_show_on_overview: bool | None = None
    member_messages_show_in_popup: bool | None = None


class ClientEventRequest(BaseModel):
    event_type: Literal["CONNECTION_LOST", "CONNECTION_RESTORED", "SYNC_COMPLETED"]
    page: str | None = None
    client_time: str | None = None
    last_sync_at: str | None = None
    device_info: str | None = None
    details: str | None = None


class TransactionFilterRequest(PinRequest, PositiveIdModel):
    name: str | None = None
    person_id: int | None = None
    action_type: str | None = None
    action_types: list[str] | None = None
    excluded_action_types: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    limit: int = 500


class ReportRequest(PinRequest):
    report_type: str = "consumption"
    group_by: str = "item"
    date_from: str | None = None
    date_to: str | None = None


class StatisticsRequest(PinRequest):
    scope: str = "today"
    date_from: str | None = None
    date_to: str | None = None
    include_admin_items: bool = False


class AgentBookDrinkRequest(PositiveIdModel):
    person_id: int
    item_id: int | None = None
    drink: str | None = None
    quantity: int = 1
    client_operation_id: str | None = None
    client_time: str | None = None
    device_info: str | None = None
    note: str | None = None


class AgentPersonRequest(PositiveIdModel):
    person_id: int


class AgentRoundRequest(RoundRequestIn):
    pass
