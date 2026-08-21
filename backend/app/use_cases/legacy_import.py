from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.domain import (
    BillingPeriod,
    Currency,
    CurrentValueSource,
    DataSourcePolicy,
    EffectiveValueSourceMode,
    ObligationLifecycle,
    ValueState,
)
from app.models import Category, CategoryGroup, Ledger, Obligation
from app.use_cases.exceptions import LedgerNotFoundError


class LegacyPayment(Protocol):
    amount: float
    paid: bool
    due_date: datetime


class LegacyCategory(Protocol):
    name: str
    code: str | None


class LegacySheet(Protocol):
    name: str


class LegacyPaymentListItem(Protocol):
    payment: LegacyPayment
    category: LegacyCategory
    sheet: LegacySheet


class LegacyPaymentBook(Protocol):
    payment_list: list[LegacyPaymentListItem]


class LegacyImportError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LegacyImportResult:
    created_category_groups: int
    created_categories: int
    replaced_categories: int
    imported_obligations: int


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def import_legacy_payment_book(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    payment_book: LegacyPaymentBook,
    current_period: BillingPeriod,
    progress: Callable[[int, int], None] | None = None,
) -> LegacyImportResult:
    """Replace imported categories with historical and current legacy payments.

    The legacy adapter exposes only the current period and earlier rows. This
    use case enforces that boundary again so a malformed workbook cannot seed
    future obligations.
    """

    if session.get(Ledger, ledger_id) is None:
        raise LedgerNotFoundError

    try:
        items = [
            item
            for item in payment_book.payment_list
            if (item.payment.due_date.year, item.payment.due_date.month)
            <= (current_period.year, current_period.month)
        ]
        total = len(items)

        groups_by_name = {
            category_group.name: category_group
            for category_group in session.scalars(
                select(CategoryGroup).where(CategoryGroup.ledger_id == ledger_id)
            )
        }
        categories_by_code = {
            category.code: category
            for category in session.scalars(
                select(Category).where(Category.ledger_id == ledger_id)
            )
        }
        categories_by_group_and_name = {
            (category.category_group_id, category.name): category
            for category in categories_by_code.values()
        }
        new_groups: list[CategoryGroup] = []
        new_categories: list[Category] = []
        obligations: list[Obligation] = []
        replaced_category_ids: set[uuid.UUID] = set()

        for item in items:
            payment = item.payment
            period = BillingPeriod(
                year=payment.due_date.year,
                month=payment.due_date.month,
            )
            group_name = item.sheet.name.strip()
            if not group_name:
                raise LegacyImportError("Legacy payment sheet name must not be empty")
            category_group = groups_by_name.get(group_name)
            if category_group is None:
                category_group = CategoryGroup(
                    id=uuid.uuid4(),
                    ledger_id=ledger_id,
                    name=group_name,
                    description=None,
                    is_active=True,
                )
                groups_by_name[group_name] = category_group
                new_groups.append(category_group)
            elif not category_group.is_active:
                raise LegacyImportError(
                    f"Legacy payment sheet {group_name!r} maps to an archived category group"
                )

            category_name = item.category.name.strip()
            category_code = item.category.code
            if not category_name:
                raise LegacyImportError(
                    "Legacy payment category name must not be empty"
                )
            if category_code is None:
                raise LegacyImportError(
                    f"Legacy payment category {category_name!r} is missing its four-letter code"
                )
            category = categories_by_code.get(category_code)
            if category is not None:
                if category.category_group_id != category_group.id:
                    raise LegacyImportError(
                        f"Legacy payment category {category_code!r} belongs to "
                        f"{category_group.name!r}, but the ledger category belongs "
                        "to a different group"
                    )
                replaced_category_ids.add(category.id)
            else:
                name_conflict = categories_by_group_and_name.get(
                    (category_group.id, category_name)
                )
                if name_conflict is not None:
                    raise LegacyImportError(
                        f"Legacy payment category {category_name!r} has a different "
                        "code than the ledger category"
                    )
                category = Category(
                    id=uuid.uuid4(),
                    ledger_id=ledger_id,
                    category_group_id=category_group.id,
                    name=category_name,
                    description=None,
                    is_active=True,
                    code=category_code,
                    data_source_policy=DataSourcePolicy.MANUAL,
                    recurrence_interval=None,
                    recurrence_unit=None,
                    recurrence_anchor=None,
                    currency=Currency.PLN,
                    due_day=None,
                )
                categories_by_code[category_code] = category
                categories_by_group_and_name[(category_group.id, category_name)] = (
                    category
                )
                new_categories.append(category)

            due_date = payment.due_date.date()
            obligations.append(
                Obligation(
                    ledger_id=ledger_id,
                    category_id=category.id,
                    notes=None,
                    lifecycle=(
                        ObligationLifecycle.PAID
                        if payment.paid
                        else ObligationLifecycle.READY
                    ),
                    period_year=period.year,
                    period_month=period.month,
                    effective_value_source=EffectiveValueSourceMode.LEGACY,
                    current_amount=Decimal(str(payment.amount)),
                    amount_state=ValueState.CONFIRMED,
                    amount_source=CurrentValueSource.LEGACY,
                    issue_date=None,
                    issue_date_state=ValueState.UNKNOWN,
                    issue_date_source=CurrentValueSource.UNKNOWN,
                    due_date=due_date,
                    due_date_state=ValueState.CONFIRMED,
                    due_date_source=CurrentValueSource.LEGACY,
                    currency=Currency.PLN,
                    paid_at=_to_utc(payment.due_date) if payment.paid else None,
                )
            )
            imported_obligation_count = len(obligations)
            if progress is not None and (
                imported_obligation_count % 50 == 0
                or imported_obligation_count == total
            ):
                progress(imported_obligation_count, total)

        if replaced_category_ids:
            session.execute(
                delete(Obligation).where(
                    Obligation.ledger_id == ledger_id,
                    Obligation.category_id.in_(replaced_category_ids),
                )
            )
        session.add_all(new_groups)
        session.add_all(new_categories)
        session.add_all(obligations)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return LegacyImportResult(
        created_category_groups=len(new_groups),
        created_categories=len(new_categories),
        replaced_categories=len(replaced_category_ids),
        imported_obligations=len(obligations),
    )
