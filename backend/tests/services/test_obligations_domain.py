from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.domain import (
    BillingPeriod,
    LedgerAccessRole,
    ObligationCreationPolicy,
    ObligationLifecycle,
    PeriodGenerationPolicy,
)
from app.models import (
    Category,
    CategoryGroup,
    LedgerMembership,
    Obligation,
    ObligationTemplate,
)
from app.services import categories as category_service
from app.services import ledgers as ledger_service
from app.services import obligations as obligation_service
from tests.utils.user import create_random_user
from tests.utils.utils import random_lower_string


def _create_category_tree(db: Session):
    owner = create_random_user(db)
    ledger = ledger_service.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"ledger-{random_lower_string()}",
    )
    category_group = CategoryGroup(
        ledger_id=ledger.id,
        name=f"group-{random_lower_string()}",
    )
    db.add(category_group)
    db.flush()
    category = Category(
        ledger_id=ledger.id,
        category_group_id=category_group.id,
        name=f"category-{random_lower_string()}",
    )
    db.add(category)
    db.commit()
    db.refresh(category_group)
    db.refresh(category)
    return ledger, category_group, category


def _create_template(
    db: Session,
    *,
    period_generation_policy: PeriodGenerationPolicy = PeriodGenerationPolicy.PRECREATE,
):
    ledger, category_group, category = _create_category_tree(db)
    template = ObligationTemplate(
        ledger_id=ledger.id,
        category_id=category.id,
        name=f"template-{random_lower_string()}",
        code=f"code-{random_lower_string()}",
        creation_policy=ObligationCreationPolicy.HYBRID,
        period_generation_policy=period_generation_policy,
        currency="PLN",
        due_day=10,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return ledger, category_group, category, template


def test_billing_period_next_wraps_year() -> None:
    assert BillingPeriod(year=2026, month=3).next() == BillingPeriod(year=2026, month=4)
    assert BillingPeriod(year=2026, month=12).next() == BillingPeriod(
        year=2027, month=1
    )


def test_ensure_obligations_creates_current_and_next_drafts(db: Session) -> None:
    ledger, _, _, template = _create_template(db)

    created = obligation_service.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        current_period=BillingPeriod(year=2026, month=3),
    )
    db.commit()

    assert len(created) == 2
    periods = sorted((item.period_year, item.period_month) for item in created)
    assert periods == [(2026, 3), (2026, 4)]
    assert all(item.lifecycle == ObligationLifecycle.DRAFT for item in created)
    assert all(item.template_id == template.id for item in created)


def test_ensure_obligations_is_idempotent(db: Session) -> None:
    ledger, _, _, _ = _create_template(db)
    current_period = BillingPeriod(year=2026, month=3)

    first = obligation_service.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        current_period=current_period,
    )
    second = obligation_service.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger.id,
        current_period=current_period,
    )
    db.commit()

    obligations = db.query(Obligation).filter(Obligation.ledger_id == ledger.id).all()
    assert len(first) == 2
    assert second == []
    assert len(obligations) == 2


def test_get_or_create_obligation_keeps_single_record_for_same_period(
    db: Session,
) -> None:
    ledger, _, _, template = _create_template(db)
    period = BillingPeriod(year=2026, month=7)

    first_obligation, first_created = obligation_service.get_or_create_obligation(
        session=db,
        template=template,
        period=period,
    )
    second_obligation, second_created = obligation_service.get_or_create_obligation(
        session=db,
        template=template,
        period=period,
    )
    db.commit()

    obligations = db.query(Obligation).filter(Obligation.ledger_id == ledger.id).all()

    assert first_created is True
    assert second_created is False
    assert first_obligation.id == second_obligation.id
    assert len(obligations) == 1


def test_archive_leaf_category(db: Session) -> None:
    ledger, _, category = _create_category_tree(db)

    archived = category_service.archive_category(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
    )
    db.commit()

    assert archived.is_active is False
    assert archived.archived_at is not None


def test_prevent_archiving_group_with_active_children(db: Session) -> None:
    ledger, category_group, _ = _create_category_tree(db)

    with pytest.raises(category_service.CategoryGroupHasActiveChildrenError):
        category_service.archive_category_group(
            session=db,
            ledger_id=ledger.id,
            category_group_id=category_group.id,
        )


def test_allow_archiving_group_when_all_children_archived(db: Session) -> None:
    ledger, category_group, category = _create_category_tree(db)
    category_service.archive_category(
        session=db,
        ledger_id=ledger.id,
        category_id=category.id,
    )

    archived_group = category_service.archive_category_group(
        session=db,
        ledger_id=ledger.id,
        category_group_id=category_group.id,
    )
    db.commit()

    assert archived_group.is_active is False
    assert archived_group.archived_at is not None


def test_archive_category_is_scoped_by_ledger(db: Session) -> None:
    ledger_one, _, category = _create_category_tree(db)
    ledger_two, _, _ = _create_category_tree(db)

    with pytest.raises(category_service.CategoryNotFoundError):
        category_service.archive_category(
            session=db,
            ledger_id=ledger_two.id,
            category_id=category.id,
        )

    db.refresh(category)
    assert category.ledger_id == ledger_one.id
    assert category.is_active is True


def test_archive_category_group_is_scoped_by_ledger(db: Session) -> None:
    ledger_one, category_group, category = _create_category_tree(db)
    ledger_two, _, _ = _create_category_tree(db)

    category_service.archive_category(
        session=db,
        ledger_id=ledger_one.id,
        category_id=category.id,
    )

    with pytest.raises(category_service.CategoryGroupNotFoundError):
        category_service.archive_category_group(
            session=db,
            ledger_id=ledger_two.id,
            category_group_id=category_group.id,
        )


def test_ledger_membership_sharing_basics(db: Session) -> None:
    owner = create_random_user(db)
    editor = create_random_user(db)
    viewer = create_random_user(db)

    ledger = ledger_service.create_ledger(
        session=db,
        owner_user_id=owner.id,
        name=f"shared-{random_lower_string()}",
    )
    ledger_service.add_membership(
        session=db,
        ledger=ledger,
        user_id=editor.id,
        role=LedgerAccessRole.EDITOR,
    )
    ledger_service.add_membership(
        session=db,
        ledger=ledger,
        user_id=viewer.id,
        role=LedgerAccessRole.VIEWER,
    )

    memberships = (
        db.query(LedgerMembership)
        .filter(LedgerMembership.ledger_id == ledger.id)
        .order_by(LedgerMembership.user_id)
        .all()
    )

    assert ledger.owner_user_id == owner.id
    assert len(memberships) == 3
    roles = {membership.user_id: membership.role for membership in memberships}
    assert roles[owner.id] == LedgerAccessRole.OWNER
    assert roles[editor.id] == LedgerAccessRole.EDITOR
    assert roles[viewer.id] == LedgerAccessRole.VIEWER


def test_ledger_scoping_keeps_related_objects_in_same_ledger(db: Session) -> None:
    ledger_one, _, _, template_one = _create_template(db)
    ledger_two, _, category_two, _ = _create_template(
        db,
        period_generation_policy=PeriodGenerationPolicy.ON_DEMAND,
    )

    obligation = obligation_service.get_or_create_obligation(
        session=db,
        template=template_one,
        period=BillingPeriod(year=2026, month=5),
    )[0]
    db.commit()

    assert template_one.ledger_id == ledger_one.id
    assert category_two.ledger_id == ledger_two.id
    assert obligation.ledger_id == ledger_one.id
    assert obligation.category_id != category_two.id


def test_ensure_obligations_filters_templates_by_ledger_and_policy(db: Session) -> None:
    ledger_one, _, category_one, _ = _create_template(db)
    ledger_two, _, _, precreate_template_other_ledger = _create_template(db)
    on_demand_template = ObligationTemplate(
        ledger_id=ledger_one.id,
        category_id=category_one.id,
        name=f"template-{random_lower_string()}",
        code=f"code-{random_lower_string()}",
        creation_policy=ObligationCreationPolicy.HYBRID,
        period_generation_policy=PeriodGenerationPolicy.ON_DEMAND,
        currency="PLN",
        due_day=12,
    )
    db.add(on_demand_template)
    db.commit()
    db.refresh(on_demand_template)

    created = obligation_service.ensure_obligations_for_period(
        session=db,
        ledger_id=ledger_one.id,
        current_period=BillingPeriod(year=2026, month=6),
    )
    db.commit()

    ledger_one_obligations = (
        db.query(Obligation).filter(Obligation.ledger_id == ledger_one.id).all()
    )
    ledger_two_obligations = (
        db.query(Obligation).filter(Obligation.ledger_id == ledger_two.id).all()
    )

    assert len(created) == 2
    assert len(ledger_one_obligations) == 2
    assert ledger_two_obligations == []
    assert all(
        obligation.template_id != precreate_template_other_ledger.id
        for obligation in ledger_one_obligations
    )
    assert all(
        obligation.template_id != on_demand_template.id
        for obligation in ledger_one_obligations
    )
