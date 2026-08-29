import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.system_run import (
    SystemRunSkipReason,
    SystemRunStatus,
    SystemRunStepStatus,
)
from app.models.base import Base, get_datetime_utc


class SystemRun(Base):
    __tablename__ = "system_run"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[SystemRunStatus] = mapped_column(nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SystemRunStep(Base):
    __tablename__ = "system_run_step"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    system_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("system_run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    ledger_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ledger.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[SystemRunStepStatus] = mapped_column(nullable=False)
    skip_reason: Mapped[SystemRunSkipReason | None] = mapped_column()
    error: Mapped[str | None] = mapped_column(String(1000))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
