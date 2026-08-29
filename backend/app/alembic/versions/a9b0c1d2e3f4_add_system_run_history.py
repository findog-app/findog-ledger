"""Add system-run execution history.

Revision ID: a9b0c1d2e3f4
Revises: 7b9e2c4d6f8a, f2a9c5d7e3b1
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "a9b0c1d2e3f4"
down_revision = ("7b9e2c4d6f8a", "f2a9c5d7e3b1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "system_run_step",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("system_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_name", sa.String(length=100), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True)),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("skip_reason", sa.String()),
        sa.Column("error", sa.String(length=1000)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["system_run_id"], ["system_run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledger.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_system_run_step_system_run_id", "system_run_step", ["system_run_id"])
    op.create_index("ix_system_run_step_ledger_id", "system_run_step", ["ledger_id"])


def downgrade() -> None:
    op.drop_index("ix_system_run_step_ledger_id", table_name="system_run_step")
    op.drop_index("ix_system_run_step_system_run_id", table_name="system_run_step")
    op.drop_table("system_run_step")
    op.drop_table("system_run")
