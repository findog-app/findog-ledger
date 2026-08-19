import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.domain import BillingPeriod, ObligationKey, ObligationLifecycle
from app.use_cases import obligations as obligation_use_cases
from tests.utils.ledger_domain import create_category_with_recurrence


def test_ensure_obligations_for_period_creates_current_and_next_drafts(
    db: Session,
) -> None:
    ledger, _, category = create_category_with_recurrence(db)
    created = obligation_use_cases.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, period=BillingPeriod(2026, 3)
    )
    assert len(created) == 2
    assert all(item.category_id == category.id for item in created)


def test_list_obligations_for_period_filters_by_category_id(db: Session) -> None:
    ledger_one, _, category_one = create_category_with_recurrence(db)
    _, _, category_two = create_category_with_recurrence(db)
    period = BillingPeriod(2026, 9)
    obligation_use_cases.ensure_obligations_for_period(
        session=db, ledger_id=ledger_one.id, period=period
    )

    obligations = obligation_use_cases.list_obligations_for_period(
        session=db, ledger_id=ledger_one.id, period=period, category_id=category_one.id
    )
    assert len(obligations) == 1
    assert obligations[0].category_id == category_one.id
    assert obligations[0].category_id != category_two.id


def test_list_obligations_for_period_filters_by_lifecycle(db: Session) -> None:
    ledger, _, _ = create_category_with_recurrence(db)
    period = BillingPeriod(2026, 8)
    created = obligation_use_cases.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, period=period
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


def test_create_manual_obligation_rejects_negative_current_amount(db: Session) -> None:
    with pytest.raises(ValueError, match="current_amount"):
        obligation_use_cases.create_manual_obligation(
            session=db,
            ledger_id=uuid.uuid4(),
            category_code="ELEC",
            period=BillingPeriod(2026, 8),
            current_amount=Decimal("-1.00"),
        )


def test_manual_update_moves_draft_obligation_to_collecting_data(db: Session) -> None:
    ledger, _, category = create_category_with_recurrence(db)
    period = BillingPeriod(2026, 8)
    created = obligation_use_cases.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, period=period
    )
    draft = next(item for item in created if item.period_year == period.year)

    updated = obligation_use_cases.update_manual_obligation(
        session=db,
        ledger_id=ledger.id,
        key=ObligationKey(
            category_code=category.code,
            period=BillingPeriod(draft.period_year, draft.period_month),
        ),
        notes="Manual follow-up",
    )

    assert updated.lifecycle is ObligationLifecycle.COLLECTING_DATA
