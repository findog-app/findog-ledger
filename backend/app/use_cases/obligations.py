from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import BillingPeriod, ObligationKey, ObligationLifecycle
from app.models import Category, Ledger, Obligation
from app.services import obligations as obligation_service
from app.use_cases.exceptions import (
    CategoryNotFoundError,
    DuplicateObligationError,
    LedgerNotFoundError,
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
) -> Obligation:
    _require_ledger(session=session, ledger_id=ledger_id)
    category = session.scalar(
        select(Category).where(
            Category.ledger_id == ledger_id,
            Category.code == category_code,
        )
    )
    if category is None:
        raise CategoryNotFoundError

    obligation, created = obligation_service.get_or_create_obligation(
        session=session,
        category=category,
        period=period,
    )
    if not created:
        raise DuplicateObligationError

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
