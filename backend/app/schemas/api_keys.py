import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApiKeyScope = Literal["ledger:read", "ledger:write"]


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: set[ApiKeyScope] = Field(min_length=1)
    expires_at: datetime | None = None


class ApiKeyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    key_prefix: str
    scopes: list[ApiKeyScope]
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_by_user_id: uuid.UUID


class ApiKeyCreated(ApiKeyPublic):
    key: str


class ApiKeysPublic(BaseModel):
    data: list[ApiKeyPublic]
    count: int
