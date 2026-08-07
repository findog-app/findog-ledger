from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.use_cases import categories as category_use_cases
from app.use_cases.exceptions import (
    CategoryGroupArchivedError,
    CategoryGroupHasActiveChildrenError,
    CrossLedgerReferenceError,
    DuplicateCategoryError,
    DuplicateCategoryGroupError,
)
from tests.utils.ledger_domain import create_category_tree, create_test_ledger
from tests.utils.utils import random_lower_string


def test_create_category_group_creates_group_in_correct_ledger(db: Session) -> None:
    ledger = create_test_ledger(db)

    category_group = category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger.id,
        name=f"group-{random_lower_string()}",
    )

    assert category_group.ledger_id == ledger.id
    assert category_group.is_active is True


def test_create_category_rejects_cross_ledger_category_group_reference(
    db: Session,
) -> None:
    ledger_one = create_test_ledger(db)
    ledger_two = create_test_ledger(db)
    category_group = category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger_two.id,
        name=f"group-{random_lower_string()}",
    )

    with pytest.raises(CrossLedgerReferenceError):
        category_use_cases.create_category(
            session=db,
            ledger_id=ledger_one.id,
            category_group_id=category_group.id,
            name=f"category-{random_lower_string()}",
        )


def test_create_category_rejects_archived_group(db: Session) -> None:
    ledger = create_test_ledger(db)
    category_group = category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger.id,
        name=f"group-{random_lower_string()}",
    )
    category_use_cases.archive_category_group(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
    )

    with pytest.raises(CategoryGroupArchivedError):
        category_use_cases.create_category(
            session=db,
            ledger_id=ledger.id,
            category_group_id=category_group.id,
            name=f"category-{random_lower_string()}",
        )


def test_create_category_group_rejects_duplicate_name_in_same_ledger(
    db: Session,
) -> None:
    ledger = create_test_ledger(db)
    name = f"group-{random_lower_string()}"
    category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger.id,
        name=name,
    )

    with pytest.raises(DuplicateCategoryGroupError):
        category_use_cases.create_category_group(
            session=db,
            ledger_id=ledger.id,
            name=name,
        )


def test_create_category_rejects_duplicate_name_in_same_group(db: Session) -> None:
    ledger = create_test_ledger(db)
    category_group = category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger.id,
        name=f"group-{random_lower_string()}",
    )
    name = f"category-{random_lower_string()}"
    category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
        name=name,
    )

    with pytest.raises(DuplicateCategoryError):
        category_use_cases.create_category(
            session=db,
            ledger_id=ledger.id,
            category_group_id=category_group.id,
            name=name,
        )


def test_same_group_and_category_names_across_ledgers_are_allowed(
    db: Session,
) -> None:
    ledger_one = create_test_ledger(db)
    ledger_two = create_test_ledger(db)
    group_name = f"group-{random_lower_string()}"
    category_name = f"category-{random_lower_string()}"

    group_one = category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger_one.id,
        name=group_name,
    )
    group_two = category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger_two.id,
        name=group_name,
    )
    category_one = category_use_cases.create_category(
        session=db,
        ledger_id=ledger_one.id,
        category_group_id=group_one.id,
        name=category_name,
    )
    category_two = category_use_cases.create_category(
        session=db,
        ledger_id=ledger_two.id,
        category_group_id=group_two.id,
        name=category_name,
    )

    assert group_one.name == group_two.name
    assert category_one.name == category_two.name


def test_archive_category_archives_category(db: Session) -> None:
    ledger, _, category = create_category_tree(db)

    archived = category_use_cases.archive_category(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
    )

    assert archived.is_active is False
    assert archived.archived_at is not None


def test_archive_category_group_fails_with_active_child_categories(
    db: Session,
) -> None:
    ledger, category_group, _ = create_category_tree(db)

    with pytest.raises(CategoryGroupHasActiveChildrenError):
        category_use_cases.archive_category_group(
            session=db,
            ledger_id=ledger.id,
            category_group_id=category_group.id,
        )


def test_archive_empty_category_group_succeeds(db: Session) -> None:
    ledger = create_test_ledger(db)
    category_group = category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger.id,
        name=f"group-{random_lower_string()}",
    )

    archived_group = category_use_cases.archive_category_group(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
    )

    assert archived_group.is_active is False
    assert archived_group.archived_at is not None


def test_archive_category_group_succeeds_when_all_children_archived(
    db: Session,
) -> None:
    ledger, category_group, category = create_category_tree(db)
    category_use_cases.archive_category(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
    )

    archived_group = category_use_cases.archive_category_group(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
    )

    assert archived_group.is_active is False
    assert archived_group.archived_at is not None
