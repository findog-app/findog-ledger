from decimal import Decimal

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
