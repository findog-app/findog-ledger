from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import BillingPeriod, ObligationLifecycle
from app.models import Ledger, Obligation
from app.services import obligations as obligation_service
from app.use_cases.exceptions import LedgerNotFoundError


def _require_ledger(*, session: Session, ledger_id: uuid.UUID) -> Ledger:
    ledger = session.get(Ledger, ledger_id)
    if ledger is None:
        raise LedgerNotFoundError
    return ledger


def ensure_obligations_for_period(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    period: BillingPeriod,
) -> list[Obligation]:
    _require_ledger(session=session, ledger_id=ledger_id)

    created = obligation_service.ensure_obligations_for_period(
        session=session,
        ledger_id=ledger_id,
        current_period=period,
    )
    session.commit()
    for obligation in created:
        session.refresh(obligation)
    return created


def list_obligations_for_period(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    period: BillingPeriod,
    lifecycle: ObligationLifecycle | None = None,
    template_id: uuid.UUID | None = None,
) -> list[Obligation]:
    _require_ledger(session=session, ledger_id=ledger_id)

    statement = select(Obligation).where(
        Obligation.ledger_id == ledger_id,
        Obligation.period_year == period.year,
        Obligation.period_month == period.month,
    )
    if lifecycle is not None:
        statement = statement.where(Obligation.lifecycle == lifecycle)
    if template_id is not None:
        statement = statement.where(Obligation.template_id == template_id)

    return list(
        session.scalars(
            statement.order_by(
                Obligation.name.asc(),
                Obligation.template_id.asc(),
                Obligation.id.asc(),
            )
        ).all()
    )
