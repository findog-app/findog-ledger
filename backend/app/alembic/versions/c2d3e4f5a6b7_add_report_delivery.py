"""Add scheduled report delivery tracking.

Revision ID: c2d3e4f5a6b7
Revises: b0c1d2e3f4a5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "c2d3e4f5a6b7"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "report_delivery",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(length=100), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_key", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum("SENT", "FAILED", name="reportdeliverystatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.String(length=1000)),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "delivery_key"),
    )


def downgrade() -> None:
    op.drop_table("report_delivery")
