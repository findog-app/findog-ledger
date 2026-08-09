from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import LedgerAccessRole
from app.models import Ledger, LedgerMembership, User
from app.use_cases.exceptions import (
    LedgerAccessConflictError,
    LedgerMembershipNotFoundError,
    LedgerNotFoundError,
    UserNotFoundError,
)


def _require_user(*, session: Session, user_id: uuid.UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise UserNotFoundError
    return user


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


def create_ledger(
    *,
    session: Session,
    owner_user_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> Ledger:
    _require_user(session=session, user_id=owner_user_id)

    ledger = Ledger(
        owner_user_id=owner_user_id,
        name=_normalize_name(name),
        description=description,
    )
    session.add(ledger)
    session.flush()

    session.add(
        LedgerMembership(
            ledger_id=ledger.id,
            user_id=owner_user_id,
            role=LedgerAccessRole.OWNER,
        )
    )
    session.commit()
    session.refresh(ledger)
    return ledger


def share_ledger(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role: LedgerAccessRole,
) -> LedgerMembership:
    ledger = _require_ledger(session=session, ledger_id=ledger_id)
    _require_user(session=session, user_id=target_user_id)

    if role == LedgerAccessRole.OWNER and target_user_id != ledger.owner_user_id:
        raise LedgerAccessConflictError

    membership = session.get(
        LedgerMembership,
        {"ledger_id": ledger_id, "user_id": target_user_id},
    )
    if membership is None:
        membership = LedgerMembership(
            ledger_id=ledger_id,
            user_id=target_user_id,
            role=(
                LedgerAccessRole.OWNER
                if target_user_id == ledger.owner_user_id
                else role
            ),
        )
        session.add(membership)
    elif membership.role != LedgerAccessRole.OWNER:
        membership.role = (
            LedgerAccessRole.OWNER if target_user_id == ledger.owner_user_id else role
        )

    session.commit()
    session.refresh(membership)
    return membership


def update_ledger_membership(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    target_user_id: uuid.UUID,
    role: LedgerAccessRole,
) -> LedgerMembership:
    ledger = _require_ledger(session=session, ledger_id=ledger_id)
    membership = session.get(
        LedgerMembership,
        {"ledger_id": ledger_id, "user_id": target_user_id},
    )
    if membership is None:
        raise LedgerMembershipNotFoundError
    if (
        target_user_id == ledger.owner_user_id
        or membership.role == LedgerAccessRole.OWNER
    ):
        raise LedgerAccessConflictError
    if role == LedgerAccessRole.OWNER:
        raise LedgerAccessConflictError

    membership.role = role
    session.commit()
    session.refresh(membership)
    return membership


def remove_ledger_membership(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    target_user_id: uuid.UUID,
) -> None:
    ledger = _require_ledger(session=session, ledger_id=ledger_id)
    membership = session.get(
        LedgerMembership,
        {"ledger_id": ledger_id, "user_id": target_user_id},
    )
    if membership is None:
        raise LedgerMembershipNotFoundError
    if (
        target_user_id == ledger.owner_user_id
        or membership.role == LedgerAccessRole.OWNER
    ):
        raise LedgerAccessConflictError

    session.delete(membership)
    session.commit()


def list_ledgers_for_user(*, session: Session, user_id: uuid.UUID) -> list[Ledger]:
    _require_user(session=session, user_id=user_id)

    return list(
        session.scalars(
            select(Ledger)
            .join(LedgerMembership, LedgerMembership.ledger_id == Ledger.id)
            .where(LedgerMembership.user_id == user_id)
            .order_by(Ledger.name.asc(), Ledger.created_at.asc(), Ledger.id.asc())
        ).all()
    )
