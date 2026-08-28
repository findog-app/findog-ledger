"""Add obligation components.

Revision ID: 7b9e2c4d6f8a
Revises: 2a6e9d4c7b1f
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "7b9e2c4d6f8a"
down_revision = "2a6e9d4c7b1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "obligation_component",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("obligation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["obligation_id"], ["obligation.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_obligation_component_obligation_id", "obligation_component", ["obligation_id"]
    )
    op.create_index(
        "uq_obligation_component_source_external_id",
        "obligation_component",
        ["obligation_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("source IS NOT NULL AND external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("obligation_component")
