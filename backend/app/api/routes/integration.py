"""Ledger-scoped, API-key authenticated integration endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import ApiContext, require_scope
from app.schemas.ledgers import LedgerPublic, LedgerUpdate
from app.use_cases import ledgers as ledger_use_cases

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
