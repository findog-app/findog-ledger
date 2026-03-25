from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import ObligationCreationPolicy, PeriodGenerationPolicy
from app.models.base import Base, get_datetime_utc

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.ledger import Ledger
    from app.models.obligation import Obligation


class ObligationTemplate(Base):
    __tablename__ = "obligation_template"
    __table_args__ = (
        ForeignKeyConstraint(
            ["ledger_id", "category_id"],
            ["category.ledger_id", "category.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("ledger_id", "id"),
        UniqueConstraint("ledger_id", "code"),
        CheckConstraint("due_day IS NULL OR (due_day >= 1 AND due_day <= 31)"),
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
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    creation_policy: Mapped[ObligationCreationPolicy] = mapped_column(nullable=False)
    period_generation_policy: Mapped[PeriodGenerationPolicy] = mapped_column(
        nullable=False
    )
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    due_day: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_datetime_utc,
        onupdate=get_datetime_utc,
        nullable=False,
    )

    ledger: Mapped[Ledger] = relationship(
        back_populates="obligation_templates",
        overlaps="category,obligation_templates",
    )
    category: Mapped[Category] = relationship(
        back_populates="obligation_templates",
        overlaps="ledger,obligation_templates",
    )
    obligations: Mapped[list[Obligation]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        overlaps="category,ledger,obligations",
    )
