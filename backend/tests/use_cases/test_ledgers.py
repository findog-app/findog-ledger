from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import LedgerAccessRole
from app.models import LedgerMembership
from app.use_cases import ledgers as ledger_use_cases
from app.use_cases.exceptions import (
    LedgerAccessConflictError,
    LedgerNotFoundError,
    UserNotFoundError,
)
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def test_create_ledger_creates_owner_membership(db: Session) -> None:
    owner = create_random_user(db)

    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )

    membership = db.get(
        LedgerMembership,
        {"ledger_id": ledger.id, "user_id": owner.id},
    )

    assert ledger.owner_user_id == owner.id
    assert membership is not None
    assert membership.role == LedgerAccessRole.OWNER


def test_share_ledger_creates_membership_for_another_user(db: Session) -> None:
    owner = create_random_user(db)
    target = create_random_user(db)
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )

    membership = ledger_use_cases.share_ledger(
        session=db,
        ledger_id=ledger.id,
        target_user_id=target.id,
        role=LedgerAccessRole.EDITOR,
    )

    assert membership.user_id == target.id
    assert membership.role == LedgerAccessRole.EDITOR


def test_share_ledger_updates_existing_membership_role(db: Session) -> None:
    owner = create_random_user(db)
    target = create_random_user(db)
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )
    ledger_use_cases.share_ledger(
        session=db,
        ledger_id=ledger.id,
        target_user_id=target.id,
        role=LedgerAccessRole.VIEWER,
    )

    membership = ledger_use_cases.share_ledger(
        session=db,
        ledger_id=ledger.id,
        target_user_id=target.id,
        role=LedgerAccessRole.EDITOR,
    )

    assert membership.role == LedgerAccessRole.EDITOR


def test_update_ledger_membership_changes_role(db: Session) -> None:
    owner = create_random_user(db)
    target = create_random_user(db)
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )
    ledger_use_cases.share_ledger(
        session=db,
        ledger_id=ledger.id,
        target_user_id=target.id,
        role=LedgerAccessRole.VIEWER,
    )

    membership = ledger_use_cases.update_ledger_membership(
        session=db,
        ledger_id=ledger.id,
        target_user_id=target.id,
        role=LedgerAccessRole.EDITOR,
    )

    assert membership.role == LedgerAccessRole.EDITOR


def test_remove_ledger_membership_removes_access(db: Session) -> None:
    owner = create_random_user(db)
    target = create_random_user(db)
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )
    ledger_use_cases.share_ledger(
        session=db,
        ledger_id=ledger.id,
        target_user_id=target.id,
        role=LedgerAccessRole.VIEWER,
    )

    ledger_use_cases.remove_ledger_membership(
        session=db,
        ledger_id=ledger.id,
        target_user_id=target.id,
    )

    assert (
        db.get(
            LedgerMembership,
            {"ledger_id": ledger.id, "user_id": target.id},
        )
        is None
    )


def test_ledger_owner_membership_cannot_be_changed_or_removed(db: Session) -> None:
    owner = create_random_user(db)
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )

    with pytest.raises(LedgerAccessConflictError):
        ledger_use_cases.update_ledger_membership(
            session=db,
            ledger_id=ledger.id,
            target_user_id=owner.id,
            role=LedgerAccessRole.VIEWER,
        )
    with pytest.raises(LedgerAccessConflictError):
        ledger_use_cases.remove_ledger_membership(
            session=db,
            ledger_id=ledger.id,
            target_user_id=owner.id,
        )


def test_share_ledger_does_not_downgrade_owner(db: Session) -> None:
    owner = create_random_user(db)
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )

    membership = ledger_use_cases.share_ledger(
        session=db,
        ledger_id=ledger.id,
        target_user_id=owner.id,
        role=LedgerAccessRole.VIEWER,
    )

    assert membership.role == LedgerAccessRole.OWNER


def test_share_ledger_rejects_missing_ledger(db: Session) -> None:
    target = create_random_user(db)

    with pytest.raises(LedgerNotFoundError):
        ledger_use_cases.share_ledger(
            session=db,
            ledger_id=uuid.uuid4(),
            target_user_id=target.id,
            role=LedgerAccessRole.EDITOR,
        )


def test_share_ledger_rejects_missing_user(db: Session) -> None:
    owner = create_random_user(db)
    ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )

    with pytest.raises(UserNotFoundError):
        ledger_use_cases.share_ledger(
            session=db,
            ledger_id=ledger.id,
            target_user_id=uuid.uuid4(),
            role=LedgerAccessRole.EDITOR,
        )


def test_list_ledgers_for_user_returns_owned_and_shared_ledgers(db: Session) -> None:
    owner = create_random_user(db)
    shared_user = create_random_user(db)
    owned_ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=shared_user.id,
        name=f"owned-{random_lower_string()}",
    )
    shared_ledger = ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"shared-{random_lower_string()}",
    )
    ledger_use_cases.share_ledger(
        session=db,
        ledger_id=shared_ledger.id,
        target_user_id=shared_user.id,
        role=LedgerAccessRole.VIEWER,
    )

    ledgers = ledger_use_cases.list_ledgers_for_user(
        session=db,
        user_id=shared_user.id,
    )

    assert {ledger.id for ledger in ledgers} == {owned_ledger.id, shared_ledger.id}
    membership_rows = db.scalars(
        select(LedgerMembership).where(LedgerMembership.user_id == shared_user.id)
    ).all()
    assert len(membership_rows) == 2
