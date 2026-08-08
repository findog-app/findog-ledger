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
    from app.models.ledger import Ledger
    from app.models.obligation import Obligation


class CategoryGroup(Base):
    __tablename__ = "category_group"
    __table_args__ = (
        UniqueConstraint("ledger_id", "id"),
        UniqueConstraint("ledger_id", "name"),
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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_datetime_utc,
        onupdate=get_datetime_utc,
        nullable=False,
    )

    ledger: Mapped[Ledger] = relationship(back_populates="category_groups")
    categories: Mapped[list[Category]] = relationship(
        back_populates="category_group",
        cascade="all, delete-orphan",
        overlaps="ledger",
    )


class Category(Base):
    __tablename__ = "category"
    __table_args__ = (
        ForeignKeyConstraint(
            ["ledger_id", "category_group_id"],
            ["category_group.ledger_id", "category_group.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("ledger_id", "id"),
        UniqueConstraint("ledger_id", "category_group_id", "name"),
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
    category_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    creation_policy: Mapped[ObligationCreationPolicy] = mapped_column(nullable=False)
    period_generation_policy: Mapped[PeriodGenerationPolicy] = mapped_column(
        nullable=False
    )
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    due_day: Mapped[int | None] = mapped_column(nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
        back_populates="categories",
        overlaps="categories,category_group",
    )
    category_group: Mapped[CategoryGroup] = relationship(
        back_populates="categories",
        overlaps="ledger,categories",
    )
    obligations: Mapped[list[Obligation]] = relationship(
        back_populates="category",
        overlaps="ledger,obligations",
    )
