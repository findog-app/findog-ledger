import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.system_run import (
    SystemRunSkipReason,
    SystemRunStatus,
    SystemRunStepStatus,
    SystemRunTrigger,
    TaskRunMode,
)


class SystemRunStart(BaseModel):
    task_names: list[str] | None = Field(default=None, max_length=100)


class SystemRunTaskPublic(BaseModel):
    name: str
    mode: TaskRunMode


class SystemRunStepPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_name: str
    ledger_id: uuid.UUID | None
    status: SystemRunStepStatus
    skip_reason: SystemRunSkipReason | None
    error: str | None
    summary: dict[str, object] | None
    started_at: datetime
    finished_at: datetime | None


class SystemRunPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: SystemRunStatus
    trigger: SystemRunTrigger
    effective_at: datetime
    timezone: str
    business_date: date
    summary: dict[str, object] | None
    error: str | None
    started_at: datetime
    finished_at: datetime | None
    steps: list[SystemRunStepPublic] = Field(default_factory=list)


class SystemRunsPublic(BaseModel):
    data: list[SystemRunPublic]
    count: int
