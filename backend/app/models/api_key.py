from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, get_datetime_utc


class ApiKey(Base):
    __tablename__ = "api_key"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ledger.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
