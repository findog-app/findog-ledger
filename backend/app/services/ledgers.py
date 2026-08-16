from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.domain import LedgerAccessRole
from app.models import Ledger, LedgerMembership


def create_ledger(
    *,
    session: Session,
    owner_user_id: uuid.UUID,
    name: str,
    description: str | None = None,
) -> Ledger:
    ledger = Ledger(
        owner_user_id=owner_user_id,
        name=name,
        description=description,
    )
    session.add(ledger)
    session.flush()

    owner_membership = LedgerMembership(
        ledger_id=ledger.id,
        user_id=owner_user_id,
        role=LedgerAccessRole.OWNER,
    )
    session.add(owner_membership)
    session.commit()
    session.refresh(ledger)
    return ledger


def add_membership(
    *,
    session: Session,
    ledger: Ledger,
    user_id: uuid.UUID,
    role: LedgerAccessRole,
) -> LedgerMembership:
    membership = session.get(
        LedgerMembership,
        {"ledger_id": ledger.id, "user_id": user_id},
    )
    if membership is None:
        membership = LedgerMembership(
            ledger_id=ledger.id,
            user_id=user_id,
            role=role,
        )
        session.add(membership)
    else:
        membership.role = role

    session.commit()
    session.refresh(membership)
    return membership
