from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from app.domain.currencies import Currency
from app.domain.obligations import BillingPeriod, DataSourcePolicy, RecurrenceUnit


@dataclass(slots=True)
class CategoryGroup:
    id: uuid.UUID
    ledger_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def can_archive(self, *, has_active_children: bool) -> bool:
        return not has_active_children


@dataclass(slots=True)
class Category:
    id: uuid.UUID
    ledger_id: uuid.UUID
    category_group_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    code: str
    data_source_policy: DataSourcePolicy
    recurrence_interval: int | None
    recurrence_unit: RecurrenceUnit | None
    first_due_date: date | None
    currency: Currency
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def archive(self, *, archived_at: datetime) -> None:
        self.is_active = False
        self.archived_at = archived_at

    def occurs_in(self, period: BillingPeriod) -> bool:
        if (
            self.data_source_policy is DataSourcePolicy.MANUAL
            or self.recurrence_interval is None
            or self.recurrence_unit is None
            or self.first_due_date is None
        ):
            return False

        anchor_period = BillingPeriod.from_date(self.first_due_date)
        month_difference = (period.year - anchor_period.year) * 12 + (
            period.month - anchor_period.month
        )
        if month_difference < 0:
            return False
        if self.recurrence_unit is RecurrenceUnit.MONTH:
            return month_difference % self.recurrence_interval == 0
        return (
            period.month == anchor_period.month
            and (period.year - anchor_period.year) % self.recurrence_interval == 0
        )
