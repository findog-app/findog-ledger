from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import (
    BillingPeriod,
    CurrentValueSource,
    DataSourcePolicy,
    EffectiveValueSourceMode,
    ObligationKey,
    ObligationLifecycle,
    ValueState,
    due_date_range,
)
from app.models import Category, Ledger, Obligation
from app.services import obligations as obligation_service
from app.use_cases.exceptions import (
    CategoryNotFoundError,
    DuplicateObligationError,
    LedgerNotFoundError,
    ManualObligationNotAllowedError,
    ObligationNotFoundError,
)


def _require_ledger(*, session: Session, ledger_id: uuid.UUID) -> Ledger:
    ledger = session.get(Ledger, ledger_id)
    if ledger is None:
        raise LedgerNotFoundError
    return ledger


def ensure_obligations_for_period(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    period: BillingPeriod,
) -> list[Obligation]:
    _require_ledger(session=session, ledger_id=ledger_id)

    created = obligation_service.ensure_obligations_for_period(
        session=session,
        ledger_id=ledger_id,
        current_period=period,
    )
    session.commit()
    for obligation in created:
        session.refresh(obligation)
    return created


def list_obligations_for_period(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    period: BillingPeriod,
    lifecycle: ObligationLifecycle | None = None,
    category_id: uuid.UUID | None = None,
) -> list[Obligation]:
    _require_ledger(session=session, ledger_id=ledger_id)

    statement = select(Obligation).where(
        Obligation.ledger_id == ledger_id,
        Obligation.period_year == period.year,
        Obligation.period_month == period.month,
    )
    if lifecycle is not None:
        statement = statement.where(Obligation.lifecycle == lifecycle)
    if category_id is not None:
        statement = statement.where(Obligation.category_id == category_id)

    return list(
        session.scalars(
            statement.order_by(
                Obligation.name.asc(),
                Obligation.category_id.asc(),
                Obligation.id.asc(),
            )
        ).all()
    )


def list_obligations_for_ledger(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    year: int | None = None,
    month: int | None = None,
    category_code: str | None = None,
    lifecycle: ObligationLifecycle | None = None,
) -> list[Obligation]:
    _require_ledger(session=session, ledger_id=ledger_id)

    statement = (
        select(Obligation)
        .join(Obligation.category)
        .where(Obligation.ledger_id == ledger_id)
    )
    if year is not None:
        statement = statement.where(Obligation.period_year == year)
    if month is not None:
        statement = statement.where(Obligation.period_month == month)
    if category_code is not None:
        statement = statement.where(Category.code == category_code)
    if lifecycle is not None:
        statement = statement.where(Obligation.lifecycle == lifecycle)

    return list(
        session.scalars(
            statement.order_by(
                Obligation.period_year.desc(),
                Obligation.period_month.desc(),
                Obligation.name.asc(),
                Obligation.id.asc(),
            )
        ).all()
    )


def create_manual_obligation(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_code: str,
    period: BillingPeriod,
    data_ready: bool = False,
    current_amount: Decimal | None = None,
    issue_date: date | None = None,
    due_date: date | None = None,
) -> Obligation:
    if current_amount is not None and current_amount < 0:
        raise ValueError("current_amount must be greater than or equal to zero")
    if data_ready and (current_amount is None or due_date is None):
        raise ValueError(
            "current_amount and due_date are required when data_ready is true"
        )
    if due_date is not None:
        minimum, maximum = due_date_range(period)
        if not minimum <= due_date <= maximum:
            raise ValueError(
                "due_date must be within the billing period or the first "
                "seven business days after it"
            )
    if issue_date is not None and due_date is not None and issue_date > due_date:
        raise ValueError("issue_date cannot be later than due_date")

    _require_ledger(session=session, ledger_id=ledger_id)
    category = session.scalar(
        select(Category).where(
            Category.ledger_id == ledger_id,
            Category.code == category_code,
        )
    )
    if category is None:
        raise CategoryNotFoundError
    if category.data_source_policy is DataSourcePolicy.AUTOMATIC:
        raise ManualObligationNotAllowedError

    obligation, created = obligation_service.get_or_create_obligation(
        session=session,
        category=category,
        period=period,
    )
    if not created:
        raise DuplicateObligationError

    obligation.lifecycle = (
        ObligationLifecycle.READY if data_ready else ObligationLifecycle.COLLECTING_DATA
    )
    obligation.current_amount = current_amount
    obligation.issue_date = issue_date
    obligation.due_date = due_date
    obligation.effective_value_source = (
        EffectiveValueSourceMode.MANUAL
        if any(value is not None for value in (current_amount, issue_date, due_date))
        else EffectiveValueSourceMode.UNKNOWN
    )
    value_state = ValueState.CONFIRMED if data_ready else ValueState.ESTIMATED
    if current_amount is not None:
        obligation.amount_state = value_state
        obligation.amount_source = CurrentValueSource.MANUAL
    if issue_date is not None:
        obligation.issue_date_state = value_state
        obligation.issue_date_source = CurrentValueSource.MANUAL
    if due_date is not None:
        obligation.due_date_state = value_state
        obligation.due_date_source = CurrentValueSource.MANUAL

    session.commit()
    session.refresh(obligation)
    return obligation


def get_obligation_by_key(
    *, session: Session, ledger_id: uuid.UUID, key: ObligationKey
) -> Obligation:
    _require_ledger(session=session, ledger_id=ledger_id)
    obligation = session.scalar(
        select(Obligation)
        .join(Obligation.category)
        .where(
            Obligation.ledger_id == ledger_id,
            Category.code == key.category_code,
            Obligation.period_year == key.period.year,
            Obligation.period_month == key.period.month,
        )
    )
    if obligation is None:
        raise ObligationNotFoundError
    return obligation
