import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain import (
    CurrentValueSource,
    EffectiveValueSourceMode,
    ObligationLifecycle,
    ValueState,
)


class BillingPeriodInput(BaseModel):
    year: int = Field(ge=1, le=9999)
    month: int = Field(ge=1, le=12)


class ObligationCreate(BaseModel):
    category_code: str = Field(pattern=r"^[A-Z]{4}$")
    period: BillingPeriodInput


class ObligationPeriodPublic(BillingPeriodInput):
    pass


class ObligationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ledger_id: uuid.UUID
    category_id: uuid.UUID
    category_code: str
    key: str
    name: str
    notes: str | None
    lifecycle: ObligationLifecycle
    period: ObligationPeriodPublic
    effective_value_source: EffectiveValueSourceMode
    current_amount: Decimal | None
    amount_state: ValueState
    amount_source: CurrentValueSource
    issue_date: date | None
    issue_date_state: ValueState
    issue_date_source: CurrentValueSource
    due_date: date | None
    due_date_state: ValueState
    due_date_source: CurrentValueSource
    currency: str | None
    created_at: datetime
    updated_at: datetime


class ObligationsPublic(BaseModel):
    data: list[ObligationPublic]
    count: int
