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
    PeriodGenerationPolicy,
    ValueState,
)
from app.models import Obligation, ObligationTemplate


def get_or_create_obligation(
    *,
    session: Session,
    template: ObligationTemplate,
    period: BillingPeriod,
) -> tuple[Obligation, bool]:
    obligation = session.scalar(
        select(Obligation).where(
            Obligation.ledger_id == template.ledger_id,
            Obligation.template_id == template.id,
            Obligation.period_year == period.year,
            Obligation.period_month == period.month,
        )
    )
    if obligation is not None:
        return obligation, False

    obligation = Obligation(
        ledger_id=template.ledger_id,
        template_id=template.id,
        category_id=template.category_id,
        name=template.name,
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
        currency=template.currency,
    )
    try:
        with session.begin_nested():
            session.add(obligation)
            session.flush()
    except IntegrityError:
        obligation = session.scalar(
            select(Obligation).where(
                Obligation.ledger_id == template.ledger_id,
                Obligation.template_id == template.id,
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
    templates = session.scalars(
        select(ObligationTemplate).where(
            ObligationTemplate.ledger_id == ledger_id,
            ObligationTemplate.is_active.is_(True),
            ObligationTemplate.period_generation_policy
            == PeriodGenerationPolicy.PRECREATE,
        )
    ).all()

    created: list[Obligation] = []
    for template in templates:
        for period in (current_period, current_period.next()):
            obligation, was_created = get_or_create_obligation(
                session=session,
                template=template,
                period=period,
            )
            if was_created:
                created.append(obligation)

    return created
