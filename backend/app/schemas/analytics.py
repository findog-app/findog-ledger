import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

from app.schemas.obligations import ObligationPeriodPublic


class CurrencyPaymentSummaryPublic(BaseModel):
    """Amounts are grouped by currency and are never converted or combined."""

    currency: str | None
    total_known_amount: Decimal
    paid_known_amount: Decimal
    paid_percentage: Decimal | None


class PeriodPaymentSummaryPublic(BaseModel):
    period: ObligationPeriodPublic
    total_obligation_count: int
    paid_obligation_count: int
    paid_percentage: Decimal | None
    unknown_amount_count: int
    is_complete: bool
    amount_summaries: list[CurrencyPaymentSummaryPublic]


class CategoryAmountHistoryPointPublic(BaseModel):
    """A period's amount, keeping missing and unknown values distinct."""

    period: ObligationPeriodPublic
    state: Literal["missing", "unknown", "known"]
    current_amount: Decimal | None
    currency: str | None


class CategoryAmountHistoryPublic(BaseModel):
    category_id: uuid.UUID
    points: list[CategoryAmountHistoryPointPublic]
