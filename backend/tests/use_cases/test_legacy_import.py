from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import (
    BillingPeriod,
    CurrentValueSource,
    EffectiveValueSourceMode,
    ObligationLifecycle,
    ValueState,
)
from app.models import Category, Obligation
from app.services import obligations as obligation_service
from app.use_cases import legacy_import
from tests.utils.ledger_domain import create_category_tree


def _legacy_item(
    *,
    sheet_name: str,
    category_name: str,
    code: str,
    amount: float,
    paid: bool,
    due_date: datetime,
) -> SimpleNamespace:
    return SimpleNamespace(
        sheet=SimpleNamespace(name=sheet_name),
        category=SimpleNamespace(name=category_name, code=code),
        payment=SimpleNamespace(amount=amount, paid=paid, due_date=due_date),
    )


def test_import_replaces_existing_category_obligations_and_marks_legacy_values(
    db: Session,
) -> None:
    ledger, group, category = create_category_tree(db)
    category_code = category.code
    category.name = "Rent"
    group.name = "Home"
    db.commit()

    old_obligation, _ = obligation_service.get_or_create_obligation(
        session=db,
        category=category,
        period=BillingPeriod(2026, 6),
    )
    db.commit()

    payment_book = SimpleNamespace(
        payment_list=[
            _legacy_item(
                sheet_name="Home",
                category_name="Rent",
                code=category_code,
                amount=1200.50,
                paid=True,
                due_date=datetime(2026, 8, 10),
            ),
            _legacy_item(
                sheet_name="Home",
                category_name="Rent",
                code=category_code,
                amount=1100.25,
                paid=False,
                due_date=datetime(2026, 7, 10),
            ),
            _legacy_item(
                sheet_name="Home",
                category_name="Rent",
                code=category_code,
                amount=1300,
                paid=False,
                due_date=datetime(2026, 9, 10),
            ),
        ]
    )

    result = legacy_import.import_legacy_payment_book(
        session=db,
        ledger_id=ledger.id,
        payment_book=payment_book,
        current_period=BillingPeriod(2026, 8),
    )

    obligations = db.scalars(
        select(Obligation)
        .where(Obligation.category_id == category.id)
        .order_by(Obligation.period_year, Obligation.period_month)
    ).all()
    assert result.created_category_groups == 0
    assert result.created_categories == 0
    assert result.replaced_categories == 1
    assert result.imported_obligations == 2
    assert old_obligation.id not in {obligation.id for obligation in obligations}
    assert [(item.period_year, item.period_month) for item in obligations] == [
        (2026, 7),
        (2026, 8),
    ]

    confirmed, paid = obligations
    assert confirmed.lifecycle is ObligationLifecycle.READY
    assert paid.lifecycle is ObligationLifecycle.PAID
    for obligation in obligations:
        assert obligation.amount_state is ValueState.CONFIRMED
        assert obligation.due_date_state is ValueState.CONFIRMED
        assert obligation.amount_source is CurrentValueSource.LEGACY
        assert obligation.due_date_source is CurrentValueSource.LEGACY
        assert obligation.effective_value_source is EffectiveValueSourceMode.LEGACY
    assert confirmed.current_amount == Decimal("1100.25")
    assert paid.current_amount == Decimal("1200.5")
    assert paid.paid_at == datetime(2026, 8, 10, tzinfo=UTC)


def test_import_creates_group_and_category_when_ledger_does_not_have_them(
    db: Session,
) -> None:
    ledger, _, _ = create_category_tree(db)
    payment_book = SimpleNamespace(
        payment_list=[
            _legacy_item(
                sheet_name="Utilities",
                category_name="Internet",
                code="NETW",
                amount=89.99,
                paid=False,
                due_date=datetime(2026, 8, 5),
            )
        ]
    )

    result = legacy_import.import_legacy_payment_book(
        session=db,
        ledger_id=ledger.id,
        payment_book=payment_book,
        current_period=BillingPeriod(2026, 8),
    )

    category = db.scalar(
        select(Category).where(Category.ledger_id == ledger.id, Category.code == "NETW")
    )
    assert category is not None
    assert category.name == "Internet"
    assert category.category_group.name == "Utilities"
    assert result.created_category_groups == 1
    assert result.created_categories == 1
    assert result.replaced_categories == 0
    assert result.imported_obligations == 1
