from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import BillingPeriod, ObligationLifecycle, PeriodGenerationPolicy
from app.models import Obligation
from app.use_cases import obligations as obligation_use_cases
from tests.utils.ledger_domain import create_template


def test_ensure_obligations_for_period_creates_current_and_next_drafts(
    db: Session,
) -> None:
    ledger, _, _, template = create_template(db)

    created = obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        period=BillingPeriod(year=2026, month=3),
    )

    assert len(created) == 2
    assert sorted((item.period_year, item.period_month) for item in created) == [
        (2026, 3),
        (2026, 4),
    ]
    assert all(item.lifecycle == ObligationLifecycle.DRAFT for item in created)
    assert all(item.template_id == template.id for item in created)


def test_ensure_obligations_for_period_is_idempotent(db: Session) -> None:
    ledger, _, _, _ = create_template(db)
    period = BillingPeriod(year=2026, month=3)

    first = obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        period=period,
    )
    second = obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        period=period,
    )

    obligations = db.query(Obligation).filter(Obligation.ledger_id == ledger.id).all()

    assert len(first) == 2
    assert second == []
    assert len(obligations) == 2


def test_list_obligations_for_period_returns_only_matching_ledger_and_period(
    db: Session,
) -> None:
    ledger_one, _, _, template_one = create_template(
        db,
        period_generation_policy=PeriodGenerationPolicy.PRECREATE,
    )
    ledger_two, _, _, _ = create_template(
        db,
        period_generation_policy=PeriodGenerationPolicy.PRECREATE,
    )
    target_period = BillingPeriod(year=2026, month=5)

    obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger_one.id,
        period=target_period,
    )
    obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger_two.id,
        period=target_period,
    )
    obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger_one.id,
        period=BillingPeriod(year=2026, month=6),
    )

    obligations = obligation_use_cases.list_obligations_for_period(
        session=db,
        ledger_id=ledger_one.id,
        period=target_period,
    )

    assert len(obligations) == 1
    assert obligations[0].ledger_id == ledger_one.id
    assert obligations[0].template_id == template_one.id
    assert (obligations[0].period_year, obligations[0].period_month) == (2026, 5)


def test_ensure_obligations_for_period_ignores_non_precreate_templates(
    db: Session,
) -> None:
    ledger, _, _, _ = create_template(
        db,
        period_generation_policy=PeriodGenerationPolicy.ON_DEMAND,
    )

    created = obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        period=BillingPeriod(year=2026, month=3),
    )

    assert created == []


def test_list_obligations_for_period_filters_by_lifecycle(db: Session) -> None:
    ledger, _, _, _ = create_template(db)
    period = BillingPeriod(year=2026, month=8)
    created = obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        period=period,
    )
    created[0].lifecycle = ObligationLifecycle.READY
    db.commit()

    obligations = obligation_use_cases.list_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        period=period,
        lifecycle=ObligationLifecycle.READY,
    )

    assert len(obligations) == 1
    assert obligations[0].lifecycle == ObligationLifecycle.READY


def test_list_obligations_for_period_filters_by_template_id(db: Session) -> None:
    ledger_one, _, _, template_one = create_template(db)
    _, _, _, template_two = create_template(db)
    period = BillingPeriod(year=2026, month=9)
    obligation_use_cases.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger_one.id,
        period=period,
    )

    obligations = obligation_use_cases.list_obligations_for_period(
        session=db,
        ledger_id=ledger_one.id,
        period=period,
        template_id=template_one.id,
    )

    assert len(obligations) == 1
    assert obligations[0].template_id == template_one.id
