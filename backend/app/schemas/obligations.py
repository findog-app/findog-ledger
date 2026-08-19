import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain import (
    BillingPeriod,
    CurrentValueSource,
    EffectiveValueSourceMode,
    ObligationLifecycle,
    ValueState,
    due_date_range,
)


class BillingPeriodInput(BaseModel):
    year: int = Field(ge=1, le=9999)
    month: int = Field(ge=1, le=12)


class ObligationCreate(BaseModel):
    category_code: str = Field(pattern=r"^[A-Z]{4}$")
    period: BillingPeriodInput
    data_ready: bool = False
    current_amount: Decimal | None = Field(default=None, ge=0)
    issue_date: date | None = None
    due_date: date | None = None

    @model_validator(mode="after")
    def require_confirmed_values_when_data_is_ready(self) -> "ObligationCreate":
        if self.data_ready and (self.current_amount is None or self.due_date is None):
            raise ValueError(
                "current_amount and due_date are required when data_ready is true"
            )
        if self.due_date is not None:
            minimum, maximum = due_date_range(
                BillingPeriod(year=self.period.year, month=self.period.month)
            )
            if not minimum <= self.due_date <= maximum:
                raise ValueError(
                    "due_date must be within the billing period or the first "
                    "seven business days after it"
                )
        if self.issue_date is not None and self.due_date is not None:
            if self.issue_date > self.due_date:
                raise ValueError("issue_date cannot be later than due_date")
        return self


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
