"""Add paid timestamp to obligations.

Revision ID: 2f7a9c4d6e8b
Revises: b3e6f9a2c4d7
"""

import sqlalchemy as sa
from alembic import op

revision = "2f7a9c4d6e8b"
down_revision = "b3e6f9a2c4d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("obligation", sa.Column("paid_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("obligation", "paid_at")
