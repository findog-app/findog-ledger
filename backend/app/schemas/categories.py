import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain import ObligationCreationPolicy, PeriodGenerationPolicy


class CategoryGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CategoryGroupUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CategoryCreate(BaseModel):
    category_group_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    code: str | None = Field(default=None, max_length=100)
    creation_policy: ObligationCreationPolicy = ObligationCreationPolicy.HYBRID
    period_generation_policy: PeriodGenerationPolicy = PeriodGenerationPolicy.PRECREATE
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    due_day: int | None = Field(default=None, ge=1, le=31)


class CategoryUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    code: str | None = Field(default=None, max_length=100)
    creation_policy: ObligationCreationPolicy
    period_generation_policy: PeriodGenerationPolicy
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    due_day: int | None = Field(default=None, ge=1, le=31)


class CategoryGroupPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ledger_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    archived_at: datetime | None


class CategoryGroupsPublic(BaseModel):
    data: list[CategoryGroupPublic]
    count: int


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ledger_id: uuid.UUID
    category_group_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    code: str | None
    creation_policy: ObligationCreationPolicy
    period_generation_policy: PeriodGenerationPolicy
    currency: str | None
    due_day: int | None
    archived_at: datetime | None


class CategoriesPublic(BaseModel):
    data: list[CategoryPublic]
    count: int
