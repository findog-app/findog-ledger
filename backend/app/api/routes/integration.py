"""Ledger-scoped, API-key authenticated integration endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import ApiContext, require_scope
from app.api.routes.obligations import to_obligation_public
from app.domain import ObligationKey, ObligationLifecycle
from app.schemas import (
    ObligationIntegrationUpdate,
    ObligationNoteAppend,
    ObligationPublic,
    ObligationsPublic,
)
from app.schemas.ledgers import LedgerPublic, LedgerUpdate
from app.use_cases import ledgers as ledger_use_cases
from app.use_cases import obligations as obligation_use_cases
from app.use_cases.exceptions import (
    ObligationInvalidLifecycleError,
    ObligationNotFoundError,
    ObligationReadOnlyError,
)

router = APIRouter(prefix="/integration", tags=["integration"])


@router.get("/ledger", response_model=LedgerPublic)
def read_integration_ledger(
    context: ApiContext = Depends(require_scope("ledger:read")),
) -> LedgerPublic:
    """Return only the ledger selected by the authenticated API key."""
    return LedgerPublic.model_validate(context.ledger)


@router.patch("/ledger", response_model=LedgerPublic)
def update_integration_ledger(
    ledger_in: LedgerUpdate,
    context: ApiContext = Depends(require_scope("ledger:write")),
) -> LedgerPublic:
    """Update the key's ledger through the shared ledger use case."""
    ledger = ledger_use_cases.update_ledger(
        session=context.session,
        ledger_id=context.ledger.id,
        name=ledger_in.name,
        description=ledger_in.description,
    )
    return LedgerPublic.model_validate(ledger)


def _parse_obligation_key(obligation_key: str) -> ObligationKey:
    try:
        return ObligationKey.parse(obligation_key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid obligation key") from exc


def _not_found_as_http(call: Any) -> ObligationPublic:
    try:
        return to_obligation_public(call())
    except ObligationNotFoundError:
        raise HTTPException(status_code=404, detail="Obligation not found")


@router.get("/obligations", response_model=ObligationsPublic)
def read_integration_obligations(
    context: ApiContext = Depends(require_scope("ledger:read")),
    year: int | None = Query(default=None, ge=1, le=9999),
    month: int | None = Query(default=None, ge=1, le=12),
    category_code: str | None = Query(default=None, pattern=r"^[A-Z]{4}$"),
    lifecycle: ObligationLifecycle | None = None,
) -> ObligationsPublic:
    obligations = obligation_use_cases.list_obligations_for_ledger(
        session=context.session,
        ledger_id=context.ledger.id,
        year=year,
        month=month,
        category_code=category_code,
        lifecycle=lifecycle,
    )
    return ObligationsPublic(
        data=[to_obligation_public(obligation) for obligation in obligations],
        count=len(obligations),
    )


@router.get("/obligations/{obligation_key}", response_model=ObligationPublic)
def read_integration_obligation(
    obligation_key: str,
    context: ApiContext = Depends(require_scope("ledger:read")),
) -> ObligationPublic:
    key = _parse_obligation_key(obligation_key)
    return _not_found_as_http(
        lambda: obligation_use_cases.get_obligation_by_key(
            session=context.session, ledger_id=context.ledger.id, key=key
        )
    )


@router.patch("/obligations/{obligation_key}", response_model=ObligationPublic)
def update_integration_obligation(
    obligation_key: str,
    obligation_in: ObligationIntegrationUpdate,
    context: ApiContext = Depends(require_scope("ledger:write")),
) -> ObligationPublic:
    key = _parse_obligation_key(obligation_key)
    try:
        obligation = obligation_use_cases.update_integration_obligation(
            session=context.session,
            ledger_id=context.ledger.id,
            key=key,
            **obligation_in.model_dump(exclude_unset=True),
        )
    except ObligationNotFoundError:
        raise HTTPException(status_code=404, detail="Obligation not found")
    except ObligationReadOnlyError:
        raise HTTPException(
            status_code=409,
            detail="Only draft and collecting data obligations can be edited",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return to_obligation_public(obligation)


def _run_integration_action(
    *, context: ApiContext, obligation_key: str, action: Any
) -> ObligationPublic:
    key = _parse_obligation_key(obligation_key)
    try:
        obligation = action(
            session=context.session, ledger_id=context.ledger.id, key=key
        )
    except ObligationNotFoundError:
        raise HTTPException(status_code=404, detail="Obligation not found")
    except ObligationInvalidLifecycleError:
        raise HTTPException(status_code=409, detail="Invalid obligation lifecycle")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return to_obligation_public(obligation)


@router.patch("/obligations/{obligation_key}/ready", response_model=ObligationPublic)
def mark_integration_obligation_ready(
    obligation_key: str,
    context: ApiContext = Depends(require_scope("ledger:write")),
) -> ObligationPublic:
    return _run_integration_action(
        context=context,
        obligation_key=obligation_key,
        action=obligation_use_cases.mark_obligation_ready,
    )


@router.post("/obligations/{obligation_key}/mark-paid", response_model=ObligationPublic)
def mark_integration_obligation_paid(
    obligation_key: str,
    context: ApiContext = Depends(require_scope("ledger:write")),
) -> ObligationPublic:
    return _run_integration_action(
        context=context,
        obligation_key=obligation_key,
        action=obligation_use_cases.mark_obligation_paid,
    )


@router.post("/obligations/{obligation_key}/cancel", response_model=ObligationPublic)
def cancel_integration_obligation(
    obligation_key: str,
    context: ApiContext = Depends(require_scope("ledger:write")),
) -> ObligationPublic:
    return _run_integration_action(
        context=context,
        obligation_key=obligation_key,
        action=obligation_use_cases.cancel_obligation,
    )


@router.post("/obligations/{obligation_key}/reopen", response_model=ObligationPublic)
def reopen_integration_obligation(
    obligation_key: str,
    context: ApiContext = Depends(require_scope("ledger:write")),
) -> ObligationPublic:
    return _run_integration_action(
        context=context,
        obligation_key=obligation_key,
        action=obligation_use_cases.reopen_obligation,
    )


@router.post("/obligations/{obligation_key}/error", response_model=ObligationPublic)
def mark_integration_obligation_error(
    obligation_key: str,
    context: ApiContext = Depends(require_scope("ledger:write")),
) -> ObligationPublic:
    return _run_integration_action(
        context=context,
        obligation_key=obligation_key,
        action=obligation_use_cases.mark_obligation_error,
    )


@router.post("/obligations/{obligation_key}/notes", response_model=ObligationPublic)
def append_integration_obligation_note(
    obligation_key: str,
    note_in: ObligationNoteAppend,
    context: ApiContext = Depends(require_scope("ledger:write")),
) -> ObligationPublic:
    key = _parse_obligation_key(obligation_key)
    try:
        obligation = obligation_use_cases.append_integration_note(
            session=context.session,
            ledger_id=context.ledger.id,
            key=key,
            integration_name=context.api_key.name,
            text=note_in.text,
        )
    except ObligationNotFoundError:
        raise HTTPException(status_code=404, detail="Obligation not found")
    return to_obligation_public(obligation)
