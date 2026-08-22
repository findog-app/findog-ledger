"""Add ledger-scoped API keys.

Revision ID: 5e6f7a8b9c0d
Revises: 3c4d5e6f7a8b
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "5e6f7a8b9c0d"
down_revision = "3c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_key",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledger.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index(op.f("ix_api_key_ledger_id"), "api_key", ["ledger_id"])
    op.create_index(op.f("ix_api_key_created_by_user_id"), "api_key", ["created_by_user_id"])
    op.create_index(op.f("ix_api_key_key_prefix"), "api_key", ["key_prefix"])


def downgrade() -> None:
    op.drop_index(op.f("ix_api_key_key_prefix"), table_name="api_key")
    op.drop_index(op.f("ix_api_key_created_by_user_id"), table_name="api_key")
    op.drop_index(op.f("ix_api_key_ledger_id"), table_name="api_key")
    op.drop_table("api_key")
