import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import (
    SessionDep,
    require_ledger_edit_access,
    require_ledger_view_access,
)
from app.models import Category, CategoryGroup, Ledger
from app.schemas import (
    CategoriesPublic,
    CategoryCreate,
    CategoryGroupCreate,
    CategoryGroupPublic,
    CategoryGroupsPublic,
    CategoryPublic,
)
from app.use_cases import categories as category_use_cases
from app.use_cases.exceptions import (
    CategoryGroupArchivedError,
    CategoryGroupHasActiveChildrenError,
    CategoryGroupNotFoundError,
    CategoryNotFoundError,
    CrossLedgerReferenceError,
    DuplicateCategoryCodeError,
    DuplicateCategoryError,
    DuplicateCategoryGroupError,
    InvalidCategoryDueDayError,
)

router = APIRouter(tags=["categories"])


def _to_category_group_public(category_group: CategoryGroup) -> CategoryGroupPublic:
    return CategoryGroupPublic.model_validate(category_group)


def _to_category_public(category: Category) -> CategoryPublic:
    return CategoryPublic.model_validate(category)


@router.get("/ledgers/{ledger_id}/category-groups", response_model=CategoryGroupsPublic)
def read_category_groups(
    session: SessionDep,
    include_archived: bool = False,
    ledger: Ledger = Depends(require_ledger_view_access),
) -> Any:
    category_groups = category_use_cases.list_category_groups_for_ledger(
        session=session,
        ledger_id=ledger.id,
        include_archived=include_archived,
    )
    return CategoryGroupsPublic(
        data=[_to_category_group_public(group) for group in category_groups],
        count=len(category_groups),
    )


@router.post("/ledgers/{ledger_id}/category-groups", response_model=CategoryGroupPublic)
def create_category_group(
    *,
    session: SessionDep,
    category_group_in: CategoryGroupCreate,
    ledger: Ledger = Depends(require_ledger_edit_access),
) -> Any:
    try:
        category_group = category_use_cases.create_category_group(
            session=session,
            ledger_id=ledger.id,
            name=category_group_in.name,
            description=category_group_in.description,
        )
    except DuplicateCategoryGroupError:
        raise HTTPException(status_code=409, detail="Category group already exists")

    return _to_category_group_public(category_group)


@router.patch(
    "/ledgers/{ledger_id}/category-groups/{category_group_id}/archive",
    response_model=CategoryGroupPublic,
)
def archive_category_group(
    *,
    session: SessionDep,
    category_group_id: uuid.UUID,
    ledger: Ledger = Depends(require_ledger_edit_access),
) -> Any:
    try:
        category_group = category_use_cases.archive_category_group(
            session=session,
            ledger_id=ledger.id,
            category_group_id=category_group_id,
        )
    except CategoryGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Category group not found")
    except CategoryGroupHasActiveChildrenError:
        raise HTTPException(
            status_code=409,
            detail="Category group has active categories",
        )

    return _to_category_group_public(category_group)


@router.get("/ledgers/{ledger_id}/categories", response_model=CategoriesPublic)
def read_categories(
    session: SessionDep,
    include_archived: bool = False,
    category_group_id: uuid.UUID | None = None,
    ledger: Ledger = Depends(require_ledger_view_access),
) -> Any:
    categories = category_use_cases.list_categories_for_ledger(
        session=session,
        ledger_id=ledger.id,
        category_group_id=category_group_id,
        include_archived=include_archived,
    )
    return CategoriesPublic(
        data=[_to_category_public(category) for category in categories],
        count=len(categories),
    )


@router.post("/ledgers/{ledger_id}/categories", response_model=CategoryPublic)
def create_category(
    *,
    session: SessionDep,
    category_in: CategoryCreate,
    ledger: Ledger = Depends(require_ledger_edit_access),
) -> Any:
    try:
        category = category_use_cases.create_category(
            session=session,
            ledger_id=ledger.id,
            category_group_id=category_in.category_group_id,
            name=category_in.name,
            description=category_in.description,
            code=category_in.code,
            creation_policy=category_in.creation_policy,
            period_generation_policy=category_in.period_generation_policy,
            currency=category_in.currency,
            due_day=category_in.due_day,
        )
    except CategoryGroupNotFoundError:
        raise HTTPException(status_code=404, detail="Category group not found")
    except CrossLedgerReferenceError:
        raise HTTPException(status_code=404, detail="Category group not found")
    except DuplicateCategoryError:
        raise HTTPException(status_code=409, detail="Category already exists")
    except DuplicateCategoryCodeError:
        raise HTTPException(status_code=409, detail="Category code already exists")
    except InvalidCategoryDueDayError:
        raise HTTPException(status_code=422, detail="Due day must be between 1 and 31")
    except CategoryGroupArchivedError:
        raise HTTPException(status_code=409, detail="Category group is archived")

    return _to_category_public(category)


@router.patch(
    "/ledgers/{ledger_id}/categories/{category_id}/archive",
    response_model=CategoryPublic,
)
def archive_category(
    *,
    session: SessionDep,
    category_id: uuid.UUID,
    ledger: Ledger = Depends(require_ledger_edit_access),
) -> Any:
    try:
        category = category_use_cases.archive_category(
            session=session,
            ledger_id=ledger.id,
            category_id=category_id,
        )
    except CategoryNotFoundError:
        raise HTTPException(status_code=404, detail="Category not found")

    return _to_category_public(category)
