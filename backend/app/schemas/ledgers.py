import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain import LedgerAccessRole


class LedgerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class LedgerShare(BaseModel):
    user_id: uuid.UUID
    role: LedgerAccessRole


class LedgerPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_user_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class LedgersPublic(BaseModel):
    data: list[LedgerPublic]
    count: int


class LedgerMemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ledger_id: uuid.UUID
    user_id: uuid.UUID
    role: LedgerAccessRole
    created_at: datetime


class LedgerMembersPublic(BaseModel):
    data: list[LedgerMemberPublic]
    count: int
