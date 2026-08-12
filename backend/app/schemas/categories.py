import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain import Currency, DataSourcePolicy, RecurrenceUnit


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
    code: str = Field(min_length=4, max_length=4, pattern=r"^[A-Z]{4}$")
    data_source_policy: DataSourcePolicy = DataSourcePolicy.HYBRID
    recurrence_interval: int | None = Field(default=None, gt=0)
    recurrence_unit: RecurrenceUnit | None = None
    recurrence_anchor: date | None = None
    currency: Currency = Currency.PLN
    due_day: int | None = Field(default=None, ge=1, le=31)


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    data_source_policy: DataSourcePolicy
    recurrence_interval: int | None = Field(default=None, gt=0)
    recurrence_unit: RecurrenceUnit | None = None
    recurrence_anchor: date | None = None
    currency: Currency = Currency.PLN
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
    code: str
    data_source_policy: DataSourcePolicy
    recurrence_interval: int | None
    recurrence_unit: RecurrenceUnit | None
    recurrence_anchor: date | None
    currency: Currency
    due_day: int | None
    archived_at: datetime | None


class CategoriesPublic(BaseModel):
    data: list[CategoryPublic]
    count: int
