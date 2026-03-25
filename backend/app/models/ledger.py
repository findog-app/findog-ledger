from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import LedgerAccessRole
from app.models.base import Base, get_datetime_utc

if TYPE_CHECKING:
    from app.models.category import Category, CategoryGroup
    from app.models.obligation import Obligation
    from app.models.obligation_template import ObligationTemplate
    from app.models.user import User


class Ledger(Base):
    __tablename__ = "ledger"
    __table_args__ = (UniqueConstraint("owner_user_id", "name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_datetime_utc,
        onupdate=get_datetime_utc,
        nullable=False,
    )

    owner: Mapped[User] = relationship(foreign_keys=[owner_user_id])
    memberships: Mapped[list[LedgerMembership]] = relationship(
        back_populates="ledger", cascade="all, delete-orphan"
    )
    category_groups: Mapped[list[CategoryGroup]] = relationship(
        back_populates="ledger", cascade="all, delete-orphan"
    )
    categories: Mapped[list[Category]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
        overlaps="category_group,categories",
    )
    obligation_templates: Mapped[list[ObligationTemplate]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
        overlaps="category,obligation_templates",
    )
    obligations: Mapped[list[Obligation]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
        overlaps="category,template,obligations",
    )


class LedgerMembership(Base):
    __tablename__ = "ledger_membership"
    __table_args__ = (UniqueConstraint("ledger_id", "user_id"),)

    ledger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ledger.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[LedgerAccessRole] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=get_datetime_utc, nullable=False
    )

    ledger: Mapped[Ledger] = relationship(back_populates="memberships")
    user: Mapped[User] = relationship()
