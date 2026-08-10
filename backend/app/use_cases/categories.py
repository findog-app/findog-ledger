from __future__ import annotations

import re
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Currency, DataSourcePolicy, RecurrenceUnit
from app.models import Category, CategoryGroup, Ledger
from app.services import categories as category_service
from app.use_cases.exceptions import (
    CategoryGroupArchivedError,
    CategoryGroupHasActiveChildrenError,
    CategoryGroupNotFoundError,
    CategoryNotFoundError,
    CrossLedgerReferenceError,
    DuplicateCategoryCodeError,
    DuplicateCategoryError,
    DuplicateCategoryGroupError,
    InvalidCategoryCodeError,
    InvalidCategoryDueDayError,
    LedgerNotFoundError,
)


def _require_ledger(*, session: Session, ledger_id: uuid.UUID) -> Ledger:
    ledger = session.get(Ledger, ledger_id)
    if ledger is None:
        raise LedgerNotFoundError
    return ledger


def _normalize_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("name must not be empty")
    return normalized


def _normalize_code(value: str) -> str:
    normalized = value.strip()
    if re.fullmatch(r"[A-Z]{4}", normalized) is None:
        raise InvalidCategoryCodeError
    return normalized


def _generate_code() -> str:
    return (
        uuid.uuid4()
        .hex[:4]
        .translate(str.maketrans("0123456789", "ABCDEFGHIJ"))
        .upper()
    )


def create_category_group(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> CategoryGroup:
    _require_ledger(session=session, ledger_id=ledger_id)
    normalized_name = _normalize_name(name)

    existing = session.scalar(
        select(CategoryGroup.id).where(
            CategoryGroup.ledger_id == ledger_id,
            CategoryGroup.name == normalized_name,
        )
    )
    if existing is not None:
        raise DuplicateCategoryGroupError

    category_group = CategoryGroup(
        ledger_id=ledger_id,
        name=normalized_name,
        description=description,
        is_active=True,
    )
    session.add(category_group)
    session.commit()
    session.refresh(category_group)
    return category_group


def list_category_groups_for_ledger(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    include_archived: bool = False,
) -> list[CategoryGroup]:
    _require_ledger(session=session, ledger_id=ledger_id)

    statement = select(CategoryGroup).where(CategoryGroup.ledger_id == ledger_id)
    if not include_archived:
        statement = statement.where(CategoryGroup.is_active.is_(True))

    return list(
        session.scalars(
            statement.order_by(CategoryGroup.name.asc(), CategoryGroup.id.asc())
        ).all()
    )


def update_category_group(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_group_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> CategoryGroup:
    _require_ledger(session=session, ledger_id=ledger_id)
    category_group = session.scalar(
        select(CategoryGroup).where(
            CategoryGroup.id == category_group_id,
            CategoryGroup.ledger_id == ledger_id,
        )
    )
    if category_group is None:
        raise CategoryGroupNotFoundError

    normalized_name = _normalize_name(name)
    existing = session.scalar(
        select(CategoryGroup.id).where(
            CategoryGroup.ledger_id == ledger_id,
            CategoryGroup.name == normalized_name,
            CategoryGroup.id != category_group_id,
        )
    )
    if existing is not None:
        raise DuplicateCategoryGroupError

    category_group.name = normalized_name
    category_group.description = description
    session.commit()
    session.refresh(category_group)
    return category_group


def create_category(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_group_id: uuid.UUID,
    name: str,
    description: str | None = None,
    code: str | None = None,
    data_source_policy: DataSourcePolicy = DataSourcePolicy.HYBRID,
    recurrence_interval: int | None = None,
    recurrence_unit: RecurrenceUnit | None = None,
    recurrence_anchor: date | None = None,
    currency: Currency = Currency.PLN,
    due_day: int | None = None,
) -> Category:
    _require_ledger(session=session, ledger_id=ledger_id)
    normalized_name = _normalize_name(name)

    category_group = session.scalar(
        select(CategoryGroup).where(
            CategoryGroup.id == category_group_id,
            CategoryGroup.ledger_id == ledger_id,
        )
    )
    if category_group is None:
        category_group_in_other_ledger = session.scalar(
            select(CategoryGroup.id).where(CategoryGroup.id == category_group_id)
        )
        if category_group_in_other_ledger is not None:
            raise CrossLedgerReferenceError
        raise CategoryGroupNotFoundError
    if not category_group.is_active:
        raise CategoryGroupArchivedError

    existing = session.scalar(
        select(Category.id).where(
            Category.ledger_id == ledger_id,
            Category.category_group_id == category_group_id,
            Category.name == normalized_name,
        )
    )
    if existing is not None:
        raise DuplicateCategoryError

    normalized_code = _normalize_code(code) if code is not None else _generate_code()
    if due_day is not None and not 1 <= due_day <= 31:
        raise InvalidCategoryDueDayError
    while (
        session.scalar(
            select(Category.id).where(
                Category.ledger_id == ledger_id, Category.code == normalized_code
            )
        )
        is not None
    ):
        if code is not None:
            raise DuplicateCategoryCodeError
        normalized_code = _generate_code()

    if data_source_policy is DataSourcePolicy.MANUAL:
        recurrence_interval = recurrence_unit = recurrence_anchor = None

    category = Category(
        ledger_id=ledger_id,
        category_group_id=category_group_id,
        name=normalized_name,
        description=description,
        is_active=True,
        code=normalized_code,
        data_source_policy=data_source_policy,
        recurrence_interval=recurrence_interval,
        recurrence_unit=recurrence_unit,
        recurrence_anchor=recurrence_anchor,
        currency=currency,
        due_day=due_day,
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def update_category(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_id: uuid.UUID,
    name: str,
    description: str | None = None,
    code: str | None = None,
    data_source_policy: DataSourcePolicy = DataSourcePolicy.HYBRID,
    recurrence_interval: int | None = None,
    recurrence_unit: RecurrenceUnit | None = None,
    recurrence_anchor: date | None = None,
    currency: Currency = Currency.PLN,
    due_day: int | None = None,
) -> Category:
    _require_ledger(session=session, ledger_id=ledger_id)
    category = session.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.ledger_id == ledger_id,
        )
    )
    if category is None:
        raise CategoryNotFoundError

    normalized_name = _normalize_name(name)
    existing_name = session.scalar(
        select(Category.id).where(
            Category.ledger_id == ledger_id,
            Category.category_group_id == category.category_group_id,
            Category.name == normalized_name,
            Category.id != category_id,
        )
    )
    if existing_name is not None:
        raise DuplicateCategoryError

    normalized_code = _normalize_code(code) if code is not None else _generate_code()
    if due_day is not None and not 1 <= due_day <= 31:
        raise InvalidCategoryDueDayError
    while (
        session.scalar(
            select(Category.id).where(
                Category.ledger_id == ledger_id,
                Category.code == normalized_code,
                Category.id != category_id,
            )
        )
        is not None
    ):
        if code is not None:
            raise DuplicateCategoryCodeError
        normalized_code = _generate_code()

    category.name = normalized_name
    category.description = description
    category.code = normalized_code
    category.data_source_policy = data_source_policy
    if data_source_policy is DataSourcePolicy.MANUAL:
        recurrence_interval = recurrence_unit = recurrence_anchor = None
    category.recurrence_interval = recurrence_interval
    category.recurrence_unit = recurrence_unit
    category.recurrence_anchor = recurrence_anchor
    category.currency = currency
    category.due_day = due_day
    session.commit()
    session.refresh(category)
    return category


def list_categories_for_ledger(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_group_id: uuid.UUID | None = None,
    include_archived: bool = False,
) -> list[Category]:
    _require_ledger(session=session, ledger_id=ledger_id)

    statement = select(Category).where(Category.ledger_id == ledger_id)
    if category_group_id is not None:
        statement = statement.where(Category.category_group_id == category_group_id)
    if not include_archived:
        statement = statement.where(Category.is_active.is_(True))

    return list(
        session.scalars(
            statement.order_by(Category.name.asc(), Category.id.asc())
        ).all()
    )


def archive_category(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    _require_ledger(session=session, ledger_id=ledger_id)

    try:
        category = category_service.archive_category(
            session=session,
            ledger_id=ledger_id,
            category_id=category_id,
        )
    except category_service.CategoryNotFoundError as exc:
        raise CategoryNotFoundError from exc

    session.commit()
    session.refresh(category)
    return category


def archive_category_group(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_group_id: uuid.UUID,
) -> CategoryGroup:
    _require_ledger(session=session, ledger_id=ledger_id)

    try:
        category_group = category_service.archive_category_group(
            session=session,
            ledger_id=ledger_id,
            category_group_id=category_group_id,
        )
    except category_service.CategoryGroupNotFoundError as exc:
        raise CategoryGroupNotFoundError from exc
    except category_service.CategoryGroupHasActiveChildrenError as exc:
        raise CategoryGroupHasActiveChildrenError from exc

    session.commit()
    session.refresh(category_group)
    return category_group
