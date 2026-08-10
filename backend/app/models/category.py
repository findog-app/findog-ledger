from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import BillingPeriod, DataSourcePolicy, RecurrenceUnit
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
        CheckConstraint("code IS NULL OR code ~ '^[A-Z]{4}$'"),
        CheckConstraint("due_day IS NULL OR (due_day >= 1 AND due_day <= 31)"),
        CheckConstraint("recurrence_interval IS NULL OR recurrence_interval > 0"),
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
    code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    data_source_policy: Mapped[DataSourcePolicy] = mapped_column(nullable=False)
    recurrence_interval: Mapped[int | None] = mapped_column(nullable=True)
    recurrence_unit: Mapped[RecurrenceUnit | None] = mapped_column(nullable=True)
    recurrence_anchor: Mapped[date | None] = mapped_column(Date, nullable=True)
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

    def occurs_in(self, period: BillingPeriod) -> bool:
        if (
            self.recurrence_interval is None
            or self.recurrence_unit is None
            or self.recurrence_anchor is None
        ):
            return False

        anchor_period = BillingPeriod.from_date(self.recurrence_anchor)
        month_difference = (period.year - anchor_period.year) * 12 + (
            period.month - anchor_period.month
        )
        if month_difference < 0:
            return False
        if self.recurrence_unit is RecurrenceUnit.MONTH:
            return month_difference % self.recurrence_interval == 0
        return (
            period.month == anchor_period.month
            and (period.year - anchor_period.year) % self.recurrence_interval == 0
        )
