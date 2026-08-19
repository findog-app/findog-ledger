import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.domain import BillingPeriod, ObligationKey, ObligationLifecycle
from app.use_cases import obligations as obligation_use_cases
from app.use_cases.exceptions import ObligationReadOnlyError
from tests.utils.ledger_domain import create_category_with_recurrence


def test_ensure_obligations_for_period_creates_current_and_next_periods(
    db: Session,
) -> None:
    ledger, _, category = create_category_with_recurrence(db)
    created = obligation_use_cases.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, period=BillingPeriod(2026, 3)
    )
    assert len(created) == 2
    assert all(item.category_id == category.id for item in created)
    assert {
        (item.period_year, item.period_month): item.lifecycle for item in created
    } == {
        (2026, 3): ObligationLifecycle.COLLECTING_DATA,
        (2026, 4): ObligationLifecycle.DRAFT,
    }


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
    draft = next(
        item for item in created if item.lifecycle is ObligationLifecycle.DRAFT
    )

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


@pytest.mark.parametrize(
    "lifecycle",
    [
        ObligationLifecycle.READY,
        ObligationLifecycle.PAID,
        ObligationLifecycle.CANCELED,
    ],
)
def test_manual_update_rejects_read_only_lifecycles(
    db: Session, lifecycle: ObligationLifecycle
) -> None:
    ledger, _, category = create_category_with_recurrence(db)
    period = BillingPeriod(2026, 8)
    created = obligation_use_cases.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, period=period
    )
    obligation = next(
        item
        for item in created
        if item.lifecycle is ObligationLifecycle.COLLECTING_DATA
    )
    obligation.lifecycle = lifecycle
    db.commit()

    with pytest.raises(ObligationReadOnlyError):
        obligation_use_cases.update_manual_obligation(
            session=db,
            ledger_id=ledger.id,
            key=ObligationKey(category_code=category.code, period=period),
            notes="Cannot be changed",
        )


def test_cancel_obligation_moves_collecting_data_to_canceled(db: Session) -> None:
    ledger, _, category = create_category_with_recurrence(db)
    period = BillingPeriod(2026, 8)
    obligation_use_cases.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, period=period
    )

    canceled = obligation_use_cases.cancel_obligation(
        session=db,
        ledger_id=ledger.id,
        key=ObligationKey(category_code=category.code, period=period),
    )

    assert canceled.lifecycle is ObligationLifecycle.CANCELED


@pytest.mark.parametrize(
    "lifecycle",
    [
        ObligationLifecycle.READY,
        ObligationLifecycle.PAID,
        ObligationLifecycle.CANCELED,
        ObligationLifecycle.ERROR,
    ],
)
def test_reopen_obligation_moves_reopenable_lifecycles_to_collecting_data(
    db: Session, lifecycle: ObligationLifecycle
) -> None:
    ledger, _, category = create_category_with_recurrence(db)
    period = BillingPeriod(2026, 8)
    created = obligation_use_cases.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, period=period
    )
    obligation = next(
        item
        for item in created
        if item.lifecycle is ObligationLifecycle.COLLECTING_DATA
    )
    obligation.lifecycle = lifecycle
    db.commit()

    reopened = obligation_use_cases.reopen_obligation(
        session=db,
        ledger_id=ledger.id,
        key=ObligationKey(category_code=category.code, period=period),
    )

    assert reopened.lifecycle is ObligationLifecycle.COLLECTING_DATA
