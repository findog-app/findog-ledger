"""Add legacy import jobs.

Revision ID: 3c4d5e6f7a8b
Revises: 2f7a9c4d6e8b
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "3c4d5e6f7a8b"
down_revision = "2f7a9c4d6e8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legacy_import_job",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("processed_obligations", sa.Integer(), nullable=False),
        sa.Column("total_obligations", sa.Integer(), nullable=False),
        sa.Column("created_category_groups", sa.Integer()),
        sa.Column("created_categories", sa.Integer()),
        sa.Column("replaced_categories", sa.Integer()),
        sa.Column("imported_obligations", sa.Integer()),
        sa.Column("error", sa.String(length=1000)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledger.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_legacy_import_job_ledger_id", "legacy_import_job", ["ledger_id"]
    )
    op.create_index(
        "uq_legacy_import_job_active",
        "legacy_import_job",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    op.drop_index("uq_legacy_import_job_active", table_name="legacy_import_job")
    op.drop_index("ix_legacy_import_job_ledger_id", table_name="legacy_import_job")
    op.drop_table("legacy_import_job")
