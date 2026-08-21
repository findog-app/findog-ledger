import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain import LegacyImportJobStatus


class LegacyImportPublic(BaseModel):
    created_category_groups: int
    created_categories: int
    replaced_categories: int
    imported_obligations: int


class LegacyImportJobPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ledger_id: uuid.UUID
    status: LegacyImportJobStatus
    processed_obligations: int
    total_obligations: int
    created_category_groups: int | None
    created_categories: int | None
    replaced_categories: int | None
    imported_obligations: int | None
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
