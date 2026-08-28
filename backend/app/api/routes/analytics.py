from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_ledger_view_access
from app.domain import BillingPeriod
from app.models import Ledger
from app.schemas import (
    CurrencyPaymentSummaryPublic,
    ObligationPeriodPublic,
    PeriodPaymentSummaryPublic,
)
from app.use_cases import analytics as analytics_use_cases

router = APIRouter(tags=["analytics"])


@router.get(
    "/ledgers/{ledger_id}/analytics/period-summary",
    response_model=PeriodPaymentSummaryPublic,
)
def read_period_payment_summary(
    *,
    session: SessionDep,
    year: int = Query(ge=1, le=9999),
    month: int = Query(ge=1, le=12),
    ledger: Ledger = Depends(require_ledger_view_access),
) -> Any:
    summary = analytics_use_cases.summarize_period_payment_progress(
        session=session,
        ledger_id=ledger.id,
        period=BillingPeriod(year=year, month=month),
    )
    return PeriodPaymentSummaryPublic(
        period=ObligationPeriodPublic(year=year, month=month),
        total_obligation_count=summary.total_obligation_count,
        paid_obligation_count=summary.paid_obligation_count,
        paid_percentage=summary.paid_percentage,
        unknown_amount_count=summary.unknown_amount_count,
        is_complete=summary.is_complete,
        amount_summaries=[
            CurrencyPaymentSummaryPublic(
                currency=item.currency,
                total_known_amount=item.total_known_amount,
                paid_known_amount=item.paid_known_amount,
                paid_percentage=item.paid_percentage,
            )
            for item in summary.amount_summaries
        ],
    )
