from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import ObligationCreationPolicy, PeriodGenerationPolicy
from app.models import Category, Ledger, ObligationTemplate
from app.use_cases.exceptions import (
    CategoryArchivedError,
    CategoryNotFoundError,
    CrossLedgerReferenceError,
    DuplicateTemplateCodeError,
    InvalidDefaultDueDayError,
    LedgerNotFoundError,
)


def _require_ledger(*, session: Session, ledger_id: uuid.UUID) -> Ledger:
    ledger = session.get(Ledger, ledger_id)
    if ledger is None:
        raise LedgerNotFoundError
    return ledger


def _normalize_required_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("name must not be empty")
    return normalized


def _normalize_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_due_day(due_day: int | None) -> None:
    if due_day is not None and not 1 <= due_day <= 31:
        raise InvalidDefaultDueDayError


def create_obligation_template(
    *,
    session: Session,
    ledger_id: uuid.UUID,
    category_id: uuid.UUID,
    name: str,
    creation_policy: ObligationCreationPolicy,
    period_generation_policy: PeriodGenerationPolicy,
    code: str | None = None,
    description: str | None = None,
    currency: str | None = None,
    due_day: int | None = None,
    is_active: bool = True,
) -> ObligationTemplate:
    _require_ledger(session=session, ledger_id=ledger_id)

    category = session.get(Category, category_id)
    if category is None:
        raise CategoryNotFoundError
    if category.ledger_id != ledger_id:
        raise CrossLedgerReferenceError
    if not category.is_active:
        raise CategoryArchivedError

    normalized_name = _normalize_required_name(name)
    normalized_code = _normalize_code(code)
    _validate_due_day(due_day)

    if normalized_code is not None:
        existing = session.scalar(
            select(ObligationTemplate.id).where(
                ObligationTemplate.ledger_id == ledger_id,
                ObligationTemplate.code == normalized_code,
            )
        )
        if existing is not None:
            raise DuplicateTemplateCodeError

    template = ObligationTemplate(
        ledger_id=ledger_id,
        category_id=category_id,
        name=normalized_name,
        code=normalized_code,
        description=description,
        is_active=is_active,
        creation_policy=creation_policy,
        period_generation_policy=period_generation_policy,
        currency=currency,
        due_day=due_day,
    )
    session.add(template)
    session.commit()
    session.refresh(template)
    return template
