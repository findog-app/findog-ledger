"""Add persisted system-run execution context and summaries.

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "b0c1d2e3f4a5"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("system_run", sa.Column("trigger", sa.String(), nullable=True))
    op.add_column(
        "system_run", sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("system_run", sa.Column("timezone", sa.String(length=100), nullable=True))
    op.add_column("system_run", sa.Column("business_date", sa.Date(), nullable=True))
    op.add_column("system_run", sa.Column("summary", postgresql.JSONB()))
    op.add_column("system_run", sa.Column("error", sa.String(length=1000)))
    op.execute(
        """
        UPDATE system_run
        SET trigger = 'scheduled',
            effective_at = started_at,
            timezone = 'UTC',
            business_date = started_at::date
        WHERE trigger IS NULL
        """
    )
    op.alter_column("system_run", "trigger", nullable=False)
    op.alter_column("system_run", "effective_at", nullable=False)
    op.alter_column("system_run", "timezone", nullable=False)
    op.alter_column("system_run", "business_date", nullable=False)
    op.add_column("system_run_step", sa.Column("summary", postgresql.JSONB()))


def downgrade() -> None:
    op.drop_column("system_run_step", "summary")
    op.drop_column("system_run", "error")
    op.drop_column("system_run", "summary")
    op.drop_column("system_run", "business_date")
    op.drop_column("system_run", "timezone")
    op.drop_column("system_run", "effective_at")
    op.drop_column("system_run", "trigger")
