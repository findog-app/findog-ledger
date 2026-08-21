import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain import LegacyImportJobStatus
from app.models.base import Base, get_datetime_utc


class LegacyImportJob(Base):
    __tablename__ = "legacy_import_job"
    __table_args__ = (
        Index(
            "uq_legacy_import_job_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ledger.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[LegacyImportJobStatus] = mapped_column(nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    processed_obligations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    total_obligations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_category_groups: Mapped[int | None] = mapped_column(Integer)
    created_categories: Mapped[int | None] = mapped_column(Integer)
    replaced_categories: Mapped[int | None] = mapped_column(Integer)
    imported_obligations: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
