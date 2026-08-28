from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from sqlalchemy import select, tuple_
from sqlalchemy.orm import Session

from app.domain import BillingPeriod, ObligationLifecycle
from app.models import Category, Obligation
from app.use_cases.exceptions import CategoryNotFoundError


@dataclass(frozen=True, slots=True)
class CurrencyPaymentSummary:
    """Amount progress for obligations expressed in one currency."""

    currency: str | None
    total_known_amount: Decimal
    paid_known_amount: Decimal
    paid_percentage: Decimal | None


@dataclass(frozen=True, slots=True)
class PeriodPaymentSummary:
    total_obligation_count: int
    paid_obligation_count: int
    paid_percentage: Decimal | None
    unknown_amount_count: int
    is_complete: bool
    amount_summaries: list[CurrencyPaymentSummary]


def is_obligation_paid(obligation: Obligation) -> bool:
    """Return whether an obligation is paid according to the domain lifecycle."""

    return obligation.lifecycle is ObligationLifecycle.PAID


def summarize_period_payment_progress(
    *, session: Session, ledger_id: uuid.UUID, period: BillingPeriod
) -> PeriodPaymentSummary:
    """Read payment progress for one ledger period without combining currencies."""

    obligations = list(
        session.scalars(
            select(Obligation).where(
                Obligation.ledger_id == ledger_id,
                Obligation.period_year == period.year,
                Obligation.period_month == period.month,
                Obligation.lifecycle != ObligationLifecycle.CANCELED,
            )
        )
    )
    total_obligation_count = len(obligations)
    paid_obligation_count = sum(is_obligation_paid(item) for item in obligations)
    unknown_amount_count = sum(item.current_amount is None for item in obligations)
    amounts_by_currency: defaultdict[str | None, list[Decimal]] = defaultdict(
        lambda: [Decimal("0.00"), Decimal("0.00")]
    )

    for obligation in obligations:
        if obligation.current_amount is None:
            continue
        amounts = amounts_by_currency[obligation.currency]
        amounts[0] += obligation.current_amount
        if is_obligation_paid(obligation):
            amounts[1] += obligation.current_amount

    return PeriodPaymentSummary(
        total_obligation_count=total_obligation_count,
        paid_obligation_count=paid_obligation_count,
        paid_percentage=_percentage(paid_obligation_count, total_obligation_count),
        unknown_amount_count=unknown_amount_count,
        is_complete=unknown_amount_count == 0,
        amount_summaries=[
            CurrencyPaymentSummary(
                currency=currency,
                total_known_amount=amounts[0],
                paid_known_amount=amounts[1],
                paid_percentage=_percentage(amounts[1], amounts[0]),
            )
            for currency, amounts in sorted(
                amounts_by_currency.items(), key=lambda item: item[0] or ""
            )
        ],
    )


def _percentage(numerator: Decimal | int, denominator: Decimal | int) -> Decimal | None:
    if denominator == 0:
        return None
    if numerator == 0:
        return Decimal("0")
    return Decimal(numerator) * Decimal("100") / Decimal(denominator)


HistoryPointState = Literal["missing", "unknown", "known"]


@dataclass(frozen=True, slots=True)
class CategoryAmountHistoryPoint:
    period: BillingPeriod
    state: HistoryPointState
    current_amount: Decimal | None
    currency: str | None


@dataclass(frozen=True, slots=True)
class CategoryAmountHistory:
    category_id: uuid.UUID
    points: list[CategoryAmountHistoryPoint]


def get_category_amount_history(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_id: uuid.UUID,
    from_period: BillingPeriod,
    to_period: BillingPeriod,
) -> CategoryAmountHistory:
    """Return a continuous, currency-preserving amount history for a category."""

    if (from_period.year, from_period.month) > (to_period.year, to_period.month):
        raise ValueError("from period must not be after to period")

    category = session.scalar(
        select(Category).where(
            Category.id == category_id, Category.ledger_id == ledger_id
        )
    )
    if category is None:
        raise CategoryNotFoundError

    obligations = session.scalars(
        select(Obligation).where(
            Obligation.ledger_id == ledger_id,
            Obligation.category_id == category_id,
            tuple_(Obligation.period_year, Obligation.period_month).between(
                (from_period.year, from_period.month),
                (to_period.year, to_period.month),
            ),
        )
    )
    obligations_by_period = {
        (obligation.period_year, obligation.period_month): obligation
        for obligation in obligations
    }

    points: list[CategoryAmountHistoryPoint] = []
    period = from_period
    while period != to_period.next():
        obligation = obligations_by_period.get((period.year, period.month))
        if obligation is None:
            points.append(
                CategoryAmountHistoryPoint(
                    period=period,
                    state="missing",
                    current_amount=None,
                    currency=category.currency,
                )
            )
        elif obligation.current_amount is None:
            points.append(
                CategoryAmountHistoryPoint(
                    period=period,
                    state="unknown",
                    current_amount=None,
                    currency=obligation.currency,
                )
            )
        else:
            points.append(
                CategoryAmountHistoryPoint(
                    period=period,
                    state="known",
                    current_amount=obligation.current_amount,
                    currency=obligation.currency,
                )
            )
        period = period.next()

    return CategoryAmountHistory(category_id=category.id, points=points)
