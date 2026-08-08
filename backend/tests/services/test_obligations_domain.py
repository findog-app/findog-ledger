from sqlalchemy.orm import Session

from app.domain import BillingPeriod, PeriodGenerationPolicy
from app.models import Obligation
from app.services import obligations as obligation_service
from tests.utils.ledger_domain import create_category_with_obligation_policy


def test_ensure_obligations_creates_current_and_next_drafts(db: Session) -> None:
    ledger, _, category = create_category_with_obligation_policy(db)

    created = obligation_service.ensure_obligations_for_period(
        session=db, ledger_id=ledger.id, current_period=BillingPeriod(2026, 3)
    )

    assert len(created) == 2
    assert {(item.period_year, item.period_month) for item in created} == {
        (2026, 3),
        (2026, 4),
    }
    assert all(item.category_id == category.id for item in created)


def test_ensure_obligations_is_idempotent(db: Session) -> None:
    ledger, _, _ = create_category_with_obligation_policy(db)
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


def test_ensure_obligations_ignores_on_demand_categories(db: Session) -> None:
    ledger, _, _ = create_category_with_obligation_policy(
        db, period_generation_policy=PeriodGenerationPolicy.ON_DEMAND
    )

    assert (
        obligation_service.ensure_obligations_for_period(
            session=db, ledger_id=ledger.id, current_period=BillingPeriod(2026, 3)
        )
        == []
    )
