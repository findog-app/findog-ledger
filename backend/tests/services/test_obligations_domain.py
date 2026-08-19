from datetime import date

from sqlalchemy.orm import Session

from app.domain import BillingPeriod, RecurrenceUnit
from app.models import Obligation
from app.services import obligations as obligation_service
from tests.utils.ledger_domain import create_category_with_recurrence


def test_ensure_obligations_creates_current_and_next_periods_with_lifecycles(
    db: Session,
) -> None:
    ledger, _, category = create_category_with_recurrence(db)

    created = obligation_service.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, current_period=BillingPeriod(2026, 3)
    )

    assert len(created) == 2
    assert {(item.period_year, item.period_month) for item in created} == {
        (2026, 3),
        (2026, 4),
    }
    assert all(item.category_id == category.id for item in created)
    assert {item.business_key for item in created} == {
        f"{category.code}-2026-03",
        f"{category.code}-2026-04",
    }
    assert {
        (item.period_year, item.period_month): item.lifecycle for item in created
    } == {
        (2026, 3): "collecting_data",
        (2026, 4): "draft",
    }


def test_ensure_obligations_is_idempotent(db: Session) -> None:
    ledger, _, _ = create_category_with_recurrence(db)
    period = BillingPeriod(2026, 3)

    first = obligation_service.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, current_period=period
    )
    second = obligation_service.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, current_period=period
    )

    assert len(first) == 2
    assert second == []
    assert (
        len(db.query(Obligation).filter(Obligation.ledger_id == ledger.id).all()) == 2
    )


def test_ensure_obligations_ignores_categories_without_recurrence(db: Session) -> None:
    ledger, _, _ = create_category_with_recurrence(
        db, recurrence_interval=None, recurrence_unit=None, recurrence_anchor=None
    )

    assert (
        obligation_service.ensure_obligations_for_period(
            session=db, ledger_id=ledger.id, current_period=BillingPeriod(2026, 3)
        )
        == []
    )


def test_ensure_obligations_only_creates_periods_that_occur(db: Session) -> None:
    ledger, _, _ = create_category_with_recurrence(
        db,
        recurrence_interval=2,
        recurrence_unit=RecurrenceUnit.MONTH,
        recurrence_anchor=date(2026, 1, 1),
    )

    created = obligation_service.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, current_period=BillingPeriod(2026, 2)
    )

    assert {(item.period_year, item.period_month) for item in created} == {(2026, 3)}


def test_ensure_obligations_derives_due_date_from_category_due_day(
    db: Session,
) -> None:
    ledger, _, category = create_category_with_recurrence(db)
    category.due_day = 31
    db.commit()

    created = obligation_service.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, current_period=BillingPeriod(2026, 2)
    )

    due_dates = {
        (item.period_year, item.period_month): item.due_date for item in created
    }
    assert due_dates == {
        (2026, 2): date(2026, 2, 27),
        (2026, 3): date(2026, 3, 31),
    }
    assert all(item.due_date_state.value == "estimated" for item in created)
    assert all(item.due_date_source.value == "automatic" for item in created)


def test_category_occurs_in_respects_month_and_year_recurrence(db: Session) -> None:
    _, _, category = create_category_with_recurrence(
        db,
        recurrence_interval=2,
        recurrence_unit=RecurrenceUnit.MONTH,
        recurrence_anchor=date(2026, 1, 15),
    )

    assert category.occurs_in(BillingPeriod(2026, 1))
    assert not category.occurs_in(BillingPeriod(2026, 2))
    assert category.occurs_in(BillingPeriod(2026, 3))

    category.recurrence_interval = 1
    category.recurrence_unit = RecurrenceUnit.YEAR
    category.recurrence_anchor = date(2026, 3, 1)

    assert category.occurs_in(BillingPeriod(2027, 3))
    assert not category.occurs_in(BillingPeriod(2027, 4))
