from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain import (
    BillingPeriod,
    CurrentValueSource,
    EffectiveValueSourceMode,
    ObligationLifecycle,
    ValueState,
)
from app.models import Category, Obligation


def get_or_create_obligation(
    *,
    session: Session,
    category: Category,
    period: BillingPeriod,
) -> tuple[Obligation, bool]:
    obligation = session.scalar(
        select(Obligation).where(
            Obligation.ledger_id == category.ledger_id,
            Obligation.category_id == category.id,
            Obligation.period_year == period.year,
            Obligation.period_month == period.month,
        )
    )
    if obligation is not None:
        return obligation, False

    obligation = Obligation(
        ledger_id=category.ledger_id,
        category_id=category.id,
        name=category.name,
        lifecycle=ObligationLifecycle.DRAFT,
        period_year=period.year,
        period_month=period.month,
        effective_value_source=EffectiveValueSourceMode.UNKNOWN,
        current_amount=None,
        amount_state=ValueState.UNKNOWN,
        amount_source=CurrentValueSource.UNKNOWN,
        issue_date=None,
        issue_date_state=ValueState.UNKNOWN,
        issue_date_source=CurrentValueSource.UNKNOWN,
        due_date=None,
        due_date_state=ValueState.UNKNOWN,
        due_date_source=CurrentValueSource.UNKNOWN,
        currency=category.currency,
    )
    try:
        with session.begin_nested():
            session.add(obligation)
            session.flush()
    except IntegrityError:
        obligation = session.scalar(
            select(Obligation).where(
                Obligation.ledger_id == category.ledger_id,
                Obligation.category_id == category.id,
                Obligation.period_year == period.year,
                Obligation.period_month == period.month,
            )
        )
        if obligation is None:
            raise
        return obligation, False

    return obligation, True


def ensure_obligations_for_period(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    current_period: BillingPeriod,
) -> list[Obligation]:
    categories = session.scalars(
        select(Category).where(
            Category.ledger_id == ledger_id,
            Category.is_active.is_(True),
        )
    ).all()

    created: list[Obligation] = []
    for category in categories:
        for period in (current_period, current_period.next()):
            if not category.occurs_in(period):
                continue
            obligation, was_created = get_or_create_obligation(
                session=session,
                category=category,
                period=period,
            )
            if was_created:
                created.append(obligation)

    return created
