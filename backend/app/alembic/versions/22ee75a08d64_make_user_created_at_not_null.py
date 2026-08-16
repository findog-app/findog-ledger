"""Make user.created_at not null

Revision ID: 22ee75a08d64
Revises: b1e4c8d5e2f1
Create Date: 2026-03-25 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "22ee75a08d64"
down_revision = "b1e4c8d5e2f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text('UPDATE "user" SET created_at = NOW() WHERE created_at IS NULL'))
    op.alter_column(
        "user",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )
