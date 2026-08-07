from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.domain import ObligationCreationPolicy, PeriodGenerationPolicy
from app.use_cases import obligation_templates as template_use_cases
from app.use_cases.exceptions import (
    CategoryArchivedError,
    CrossLedgerReferenceError,
    DuplicateTemplateCodeError,
    InvalidDefaultDueDayError,
)
from tests.utils.ledger_domain import create_category_tree
from tests.utils.utils import random_lower_string


def test_create_obligation_template_creates_template_in_correct_ledger(
    db: Session,
) -> None:
    ledger, _, category = create_category_tree(db)

    template = template_use_cases.create_obligation_template(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        name=f"template-{random_lower_string()}",
        code=f"code-{random_lower_string()}",
        creation_policy=ObligationCreationPolicy.HYBRID,
        period_generation_policy=PeriodGenerationPolicy.PRECREATE,
        currency="PLN",
        due_day=15,
    )

    assert template.ledger_id == ledger.id
    assert template.category_id == category.id
    assert template.due_day == 15


def test_create_obligation_template_rejects_category_from_another_ledger(
    db: Session,
) -> None:
    ledger_one, _, _ = create_category_tree(db)
    _, _, category_two = create_category_tree(db)

    with pytest.raises(CrossLedgerReferenceError):
        template_use_cases.create_obligation_template(
            session=db,
            ledger_id=ledger_one.id,
            category_id=category_two.id,
            name=f"template-{random_lower_string()}",
            code=f"code-{random_lower_string()}",
            creation_policy=ObligationCreationPolicy.HYBRID,
            period_generation_policy=PeriodGenerationPolicy.PRECREATE,
        )


def test_create_obligation_template_rejects_invalid_default_due_day(
    db: Session,
) -> None:
    ledger, _, category = create_category_tree(db)

    with pytest.raises(InvalidDefaultDueDayError):
        template_use_cases.create_obligation_template(
            session=db,
            ledger_id=ledger.id,
            category_id=category.id,
            name=f"template-{random_lower_string()}",
            code=f"code-{random_lower_string()}",
            creation_policy=ObligationCreationPolicy.HYBRID,
            period_generation_policy=PeriodGenerationPolicy.PRECREATE,
            due_day=32,
        )


def test_create_obligation_template_rejects_duplicate_code_in_same_ledger(
    db: Session,
) -> None:
    ledger, _, category = create_category_tree(db)
    code = f"code-{random_lower_string()}"
    template_use_cases.create_obligation_template(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
        name=f"template-{random_lower_string()}",
        code=code,
        creation_policy=ObligationCreationPolicy.HYBRID,
        period_generation_policy=PeriodGenerationPolicy.PRECREATE,
    )

    with pytest.raises(DuplicateTemplateCodeError):
        template_use_cases.create_obligation_template(
            session=db,
            ledger_id=ledger.id,
            category_id=category.id,
            name=f"template-{random_lower_string()}",
            code=code,
            creation_policy=ObligationCreationPolicy.HYBRID,
            period_generation_policy=PeriodGenerationPolicy.PRECREATE,
        )


def test_create_obligation_template_allows_same_code_across_ledgers(
    db: Session,
) -> None:
    ledger_one, _, category_one = create_category_tree(db)
    ledger_two, _, category_two = create_category_tree(db)
    code = f"code-{random_lower_string()}"

    template_one = template_use_cases.create_obligation_template(
        session=db,
        ledger_id=ledger_one.id,
        category_id=category_one.id,
        name=f"template-{random_lower_string()}",
        code=code,
        creation_policy=ObligationCreationPolicy.HYBRID,
        period_generation_policy=PeriodGenerationPolicy.PRECREATE,
    )
    template_two = template_use_cases.create_obligation_template(
        session=db,
        ledger_id=ledger_two.id,
        category_id=category_two.id,
        name=f"template-{random_lower_string()}",
        code=code,
        creation_policy=ObligationCreationPolicy.HYBRID,
        period_generation_policy=PeriodGenerationPolicy.PRECREATE,
    )

    assert template_one.code == template_two.code


def test_create_obligation_template_rejects_archived_category(
    db: Session,
) -> None:
    ledger, _, category = create_category_tree(db)
    category.is_active = False
    db.commit()

    with pytest.raises(CategoryArchivedError):
        template_use_cases.create_obligation_template(
            session=db,
            ledger_id=ledger.id,
            category_id=category.id,
            name=f"template-{random_lower_string()}",
            code=f"code-{random_lower_string()}",
            creation_policy=ObligationCreationPolicy.HYBRID,
            period_generation_policy=PeriodGenerationPolicy.PRECREATE,
        )
