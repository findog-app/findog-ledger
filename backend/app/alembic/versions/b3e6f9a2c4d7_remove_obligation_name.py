"""Remove duplicated obligation name.

Revision ID: b3e6f9a2c4d7
Revises: f2a9c5d7e3b1
"""

import sqlalchemy as sa
from alembic import op

revision = "b3e6f9a2c4d7"
down_revision = "f2a9c5d7e3b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("obligation", "name")


def downgrade() -> None:
    op.add_column("obligation", sa.Column("name", sa.String(length=255), nullable=True))
    op.execute(
        """
        UPDATE obligation
        SET name = category.name
        FROM category
        WHERE category.id = obligation.category_id
        """
    )
    op.alter_column("obligation", "name", nullable=False)
