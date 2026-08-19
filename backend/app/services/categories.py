from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, CategoryGroup


class CategoryNotFoundError(Exception):
    pass


class CategoryGroupNotFoundError(Exception):
    pass


class CategoryGroupHasActiveChildrenError(Exception):
    pass


def archive_category(
    *, session: Session, ledger_id: uuid.UUID, category_id: uuid.UUID
) -> Category:
    category = session.scalar(
        select(Category).where(
            Category.id == category_id,
            Category.ledger_id == ledger_id,
        )
    )
    if category is None:
        raise CategoryNotFoundError

    if category.is_active:
        now = datetime.now(UTC)
        category.is_active = False
        category.archived_at = now

    session.flush()
    return category


def archive_category_group(
    *, session: Session, ledger_id: uuid.UUID, category_group_id: uuid.UUID
) -> CategoryGroup:
    category_group = session.scalar(
        select(CategoryGroup).where(
            CategoryGroup.id == category_group_id,
            CategoryGroup.ledger_id == ledger_id,
        )
    )
    if category_group is None:
        raise CategoryGroupNotFoundError

    active_children = session.scalar(
        select(Category.id)
        .where(
            Category.category_group_id == category_group_id,
            Category.ledger_id == ledger_id,
            Category.is_active.is_(True),
        )
        .limit(1)
    )
    if active_children is not None:
        raise CategoryGroupHasActiveChildrenError

    if category_group.is_active:
        now = datetime.now(UTC)
        category_group.is_active = False
        category_group.archived_at = now

    session.flush()
    return category_group
