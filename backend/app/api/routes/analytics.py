import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import SessionDep, require_ledger_view_access
from app.domain import BillingPeriod
from app.models import Ledger
from app.schemas import (
    CategoryAmountHistoryPointPublic,
    CategoryAmountHistoryPublic,
    CurrencyPaymentSummaryPublic,
    ObligationPeriodPublic,
    PeriodPaymentSummaryPublic,
)
from app.use_cases import analytics as analytics_use_cases
from app.use_cases.exceptions import CategoryNotFoundError

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


@router.get(
    "/ledgers/{ledger_id}/analytics/categories/{category_id}/history",
    response_model=CategoryAmountHistoryPublic,
)
def read_category_amount_history(
    *,
    session: SessionDep,
    category_id: uuid.UUID,
    from_: str = Query(alias="from", pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    to: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    ledger: Ledger = Depends(require_ledger_view_access),
) -> Any:
    from_period = _parse_period(from_)
    to_period = _parse_period(to)
    try:
        history = analytics_use_cases.get_category_amount_history(
            session=session,
            ledger_id=ledger.id,
            category_id=category_id,
            from_period=from_period,
            to_period=to_period,
        )
    except CategoryNotFoundError:
        raise HTTPException(status_code=404, detail="Category not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return CategoryAmountHistoryPublic(
        category_id=history.category_id,
        points=[
            CategoryAmountHistoryPointPublic(
                period=ObligationPeriodPublic(
                    year=point.period.year, month=point.period.month
                ),
                state=point.state,
                current_amount=point.current_amount,
                currency=point.currency,
            )
            for point in history.points
        ],
    )


def _parse_period(value: str) -> BillingPeriod:
    year, month = value.split("-")
    return BillingPeriod(year=int(year), month=int(month))
