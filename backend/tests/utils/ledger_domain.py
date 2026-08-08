from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain import ObligationCreationPolicy, PeriodGenerationPolicy
from app.models import Category, CategoryGroup, Ledger
from app.use_cases import categories as category_use_cases
from app.use_cases import ledgers as ledger_use_cases
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def create_test_ledger(db: Session) -> Ledger:
    owner = create_random_user(db)
    return ledger_use_cases.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )


def create_category_tree(db: Session) -> tuple[Ledger, CategoryGroup, Category]:
    ledger = create_test_ledger(db)
    category_group = category_use_cases.create_category_group(
        session=db,
        ledger_id=ledger.id,
        name=f"group-{random_lower_string()}",
    )
    category = category_use_cases.create_category(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
        name=f"category-{random_lower_string()}",
    )
    return ledger, category_group, category


def create_category_with_obligation_policy(
    db: Session,
    *,
    period_generation_policy: PeriodGenerationPolicy = PeriodGenerationPolicy.PRECREATE,
) -> tuple[Ledger, CategoryGroup, Category]:
    ledger, category_group, category = create_category_tree(db)
    category.creation_policy = ObligationCreationPolicy.HYBRID
    category.period_generation_policy = period_generation_policy
    category.currency = "PLN"
    category.due_day = 10
    category.code = "TEST"
    db.commit()
    db.refresh(category)
    return ledger, category_group, category
