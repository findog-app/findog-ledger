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


class _Unset:
    pass


UNSET = _Unset()


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

    statement = (
        select(Obligation)
        .join(Obligation.category)
        .where(
            Obligation.ledger_id == ledger_id,
            Obligation.period_year == period.year,
            Obligation.period_month == period.month,
        )
    )
    if lifecycle is not None:
        statement = statement.where(Obligation.lifecycle == lifecycle)
    if category_id is not None:
        statement = statement.where(Obligation.category_id == category_id)

    return list(
        session.scalars(
            statement.order_by(
                Category.name.asc(),
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
                Category.name.asc(),
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
    notes: str | None = None,
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
    obligation.notes = notes
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


def _set_manual_value(
    *,
    obligation: Obligation,
    value_attribute: str,
    state_attribute: str,
    source_attribute: str,
    value: Decimal | date | None,
) -> None:
    setattr(obligation, value_attribute, value)
    if value is None:
        setattr(obligation, state_attribute, ValueState.UNKNOWN)
        setattr(obligation, source_attribute, CurrentValueSource.UNKNOWN)
        return

    previous_state = getattr(obligation, state_attribute)
    setattr(obligation, source_attribute, CurrentValueSource.MANUAL)
    if previous_state is ValueState.CONFIRMED:
        setattr(obligation, state_attribute, ValueState.OVERRIDDEN)
    elif previous_state is ValueState.UNKNOWN:
        setattr(obligation, state_attribute, ValueState.ESTIMATED)


def _update_effective_value_source(obligation: Obligation) -> None:
    sources = {
        source
        for value, source in (
            (obligation.current_amount, obligation.amount_source),
            (obligation.issue_date, obligation.issue_date_source),
            (obligation.due_date, obligation.due_date_source),
        )
        if value is not None and source is not CurrentValueSource.UNKNOWN
    }
    if not sources:
        obligation.effective_value_source = EffectiveValueSourceMode.UNKNOWN
    elif sources == {CurrentValueSource.MANUAL}:
        obligation.effective_value_source = EffectiveValueSourceMode.MANUAL
    elif sources == {CurrentValueSource.AUTOMATIC}:
        obligation.effective_value_source = EffectiveValueSourceMode.AUTOMATIC
    else:
        obligation.effective_value_source = EffectiveValueSourceMode.MIXED


def update_manual_obligation(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    key: ObligationKey,
    current_amount: Decimal | None | _Unset = UNSET,
    issue_date: date | None | _Unset = UNSET,
    due_date: date | None | _Unset = UNSET,
    notes: str | None | _Unset = UNSET,
) -> Obligation:
    obligation = get_obligation_by_key(session=session, ledger_id=ledger_id, key=key)

    next_current_amount = (
        obligation.current_amount
        if isinstance(current_amount, _Unset)
        else current_amount
    )
    next_issue_date = (
        obligation.issue_date if isinstance(issue_date, _Unset) else issue_date
    )
    next_due_date = obligation.due_date if isinstance(due_date, _Unset) else due_date
    if next_current_amount is not None and next_current_amount < 0:
        raise ValueError("current_amount must be greater than or equal to zero")
    if next_due_date is not None:
        minimum, maximum = due_date_range(
            BillingPeriod(obligation.period_year, obligation.period_month)
        )
        if not minimum <= next_due_date <= maximum:
            raise ValueError(
                "due_date must be within the billing period or the first "
                "seven business days after it"
            )
    if next_issue_date is not None and next_due_date is not None:
        if next_issue_date > next_due_date:
            raise ValueError("issue_date cannot be later than due_date")

    if not isinstance(current_amount, _Unset):
        _set_manual_value(
            obligation=obligation,
            value_attribute="current_amount",
            state_attribute="amount_state",
            source_attribute="amount_source",
            value=current_amount,
        )
    if not isinstance(issue_date, _Unset):
        _set_manual_value(
            obligation=obligation,
            value_attribute="issue_date",
            state_attribute="issue_date_state",
            source_attribute="issue_date_source",
            value=issue_date,
        )
    if not isinstance(due_date, _Unset):
        _set_manual_value(
            obligation=obligation,
            value_attribute="due_date",
            state_attribute="due_date_state",
            source_attribute="due_date_source",
            value=due_date,
        )
    if not isinstance(notes, _Unset):
        obligation.notes = notes

    _update_effective_value_source(obligation)
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
