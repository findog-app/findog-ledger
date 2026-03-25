from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class CategoryGroup:
    id: uuid.UUID
    ledger_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def can_archive(self, *, has_active_children: bool) -> bool:
        return not has_active_children


@dataclass(slots=True)
class Category:
    id: uuid.UUID
    ledger_id: uuid.UUID
    category_group_id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    def archive(self, *, archived_at: datetime) -> None:
        self.is_active = False
        self.archived_at = archived_at
