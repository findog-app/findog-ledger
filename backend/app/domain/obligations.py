from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class ObligationLifecycle(str, Enum):
    DRAFT = "draft"
    COLLECTING_DATA = "collecting_data"
    READY = "ready"
    PAID = "paid"
    CANCELED = "canceled"
    ERROR = "error"


class DataSourcePolicy(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    HYBRID = "hybrid"


class RecurrenceUnit(str, Enum):
    MONTH = "month"
    YEAR = "year"


class ValueState(str, Enum):
    UNKNOWN = "unknown"
    ESTIMATED = "estimated"
    CONFIRMED = "confirmed"
    OVERRIDDEN = "overridden"


class CurrentValueSource(str, Enum):
    UNKNOWN = "unknown"
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class EffectiveValueSourceMode(str, Enum):
    UNKNOWN = "unknown"
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class BillingPeriod:
    year: int
    month: int

    def __post_init__(self) -> None:
        if self.month < 1 or self.month > 12:
            raise ValueError("month must be between 1 and 12")

    def next(self) -> BillingPeriod:
        if self.month == 12:
            return BillingPeriod(year=self.year + 1, month=1)
        return BillingPeriod(year=self.year, month=self.month + 1)

    @classmethod
    def from_date(cls, value: date) -> BillingPeriod:
        return cls(year=value.year, month=value.month)


@dataclass(slots=True)
class Obligation:
    id: uuid.UUID
    ledger_id: uuid.UUID
    category_id: uuid.UUID
    period: BillingPeriod
    name: str
    lifecycle: ObligationLifecycle
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
