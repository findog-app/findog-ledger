from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import BillingPeriod, ObligationLifecycle
from app.models import Obligation


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
