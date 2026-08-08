from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import (
    CurrentUser,
    SessionDep,
    require_ledger_owner_access,
    require_ledger_view_access,
)
from app.models import Ledger, LedgerMembership
from app.schemas import (
    LedgerCreate,
    LedgerMemberPublic,
    LedgerMembersPublic,
    LedgerPublic,
    LedgerShare,
    LedgersPublic,
)
from app.services import users as user_service
from app.use_cases import ledgers as ledger_use_cases
from app.use_cases.exceptions import (
    LedgerAccessConflictError,
    LedgerNotFoundError,
    UserNotFoundError,
)

router = APIRouter(prefix="/ledgers", tags=["ledgers"])


def _to_ledger_public(ledger: Ledger) -> LedgerPublic:
    return LedgerPublic.model_validate(ledger)


def _to_ledger_member_public(membership: LedgerMembership) -> LedgerMemberPublic:
    return LedgerMemberPublic(
        ledger_id=membership.ledger_id,
        user_id=membership.user_id,
        email=membership.user.email,
        full_name=membership.user.full_name,
        role=membership.role,
        created_at=membership.created_at,
    )


@router.get("/", response_model=LedgersPublic)
def read_ledgers(session: SessionDep, current_user: CurrentUser) -> Any:
    ledgers = ledger_use_cases.list_ledgers_for_user(
        session=session,
        user_id=current_user.id,
    )
    return LedgersPublic(
        data=[_to_ledger_public(ledger) for ledger in ledgers],
        count=len(ledgers),
    )


@router.post("/", response_model=LedgerPublic)
def create_ledger(
    *, session: SessionDep, current_user: CurrentUser, ledger_in: LedgerCreate
) -> Any:
    ledger = ledger_use_cases.create_ledger(
        session=session,
        owner_user_id=current_user.id,
        name=ledger_in.name,
        description=ledger_in.description,
    )
    return _to_ledger_public(ledger)


@router.get("/{ledger_id}", response_model=LedgerPublic)
def read_ledger(ledger: Ledger = Depends(require_ledger_view_access)) -> Any:
    return _to_ledger_public(ledger)


@router.get("/{ledger_id}/members", response_model=LedgerMembersPublic)
def read_ledger_members(
    session: SessionDep,
    ledger: Ledger = Depends(require_ledger_view_access),
) -> Any:
    memberships = session.scalars(
        select(LedgerMembership)
        .where(LedgerMembership.ledger_id == ledger.id)
        .order_by(LedgerMembership.created_at.asc(), LedgerMembership.user_id.asc())
    ).all()
    return LedgerMembersPublic(
        data=[_to_ledger_member_public(membership) for membership in memberships],
        count=len(memberships),
    )


@router.post("/{ledger_id}/members", response_model=LedgerMemberPublic)
def share_ledger(
    *,
    session: SessionDep,
    share_in: LedgerShare,
    ledger: Ledger = Depends(require_ledger_owner_access),
) -> Any:
    target_user_id = share_in.user_id
    if share_in.email is not None:
        target_user = user_service.get_user_by_email(
            session=session,
            email=str(share_in.email),
        )
        if target_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        target_user_id = target_user.id

    assert target_user_id is not None
    try:
        membership = ledger_use_cases.share_ledger(
            session=session,
            ledger_id=ledger.id,
            target_user_id=target_user_id,
            role=share_in.role,
        )
    except LedgerNotFoundError:
        raise HTTPException(status_code=404, detail="Ledger not found")
    except UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except LedgerAccessConflictError:
        raise HTTPException(status_code=409, detail="Ledger membership conflict")

    return _to_ledger_member_public(membership)
