from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ObligationCreationPolicy, PeriodGenerationPolicy
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
    creation_policy: ObligationCreationPolicy = ObligationCreationPolicy.HYBRID,
    period_generation_policy: PeriodGenerationPolicy = PeriodGenerationPolicy.PRECREATE,
    currency: str | None = None,
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

    normalized_code = code.strip() if code is not None else None
    if normalized_code == "":
        normalized_code = None
    if due_day is not None and not 1 <= due_day <= 31:
        raise InvalidCategoryDueDayError
    if (
        normalized_code is not None
        and session.scalar(
            select(Category.id).where(
                Category.ledger_id == ledger_id, Category.code == normalized_code
            )
        )
        is not None
    ):
        raise DuplicateCategoryCodeError

    category = Category(
        ledger_id=ledger_id,
        category_group_id=category_group_id,
        name=normalized_name,
        description=description,
        is_active=True,
        code=normalized_code,
        creation_policy=creation_policy,
        period_generation_policy=period_generation_policy,
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
    creation_policy: ObligationCreationPolicy = ObligationCreationPolicy.HYBRID,
    period_generation_policy: PeriodGenerationPolicy = PeriodGenerationPolicy.PRECREATE,
    currency: str | None = None,
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

    normalized_code = code.strip() if code is not None else None
    if normalized_code == "":
        normalized_code = None
    if due_day is not None and not 1 <= due_day <= 31:
        raise InvalidCategoryDueDayError
    if normalized_code is not None:
        existing_code = session.scalar(
            select(Category.id).where(
                Category.ledger_id == ledger_id,
                Category.code == normalized_code,
                Category.id != category_id,
            )
        )
        if existing_code is not None:
            raise DuplicateCategoryCodeError

    category.name = normalized_name
    category.description = description
    category.code = normalized_code
    category.creation_policy = creation_policy
    category.period_generation_policy = period_generation_policy
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
