"""Require category codes and default category currency.

Revision ID: c9e2f6a1b4d7
Revises: a4e7c1d2f8b3
"""

from alembic import op
import sqlalchemy as sa


revision = "c9e2f6a1b4d7"
down_revision = "a4e7c1d2f8b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE category
        SET code = substring(
            translate(md5(id::text), '0123456789', 'ABCDEFGHIJ')
            FROM 1 FOR 4
        )
        WHERE code IS NULL OR code = ''
        """
    )
    op.execute("UPDATE category SET currency = 'PLN' WHERE currency IS NULL")
    op.alter_column("category", "code", nullable=False)
    op.alter_column("category", "currency", nullable=False, server_default="PLN")
    op.alter_column("category", "currency", server_default=None)
    op.drop_constraint("ck_category_code_four_uppercase", "category", type_="check")
    op.create_check_constraint("ck_category_code", "category", "code ~ '^[A-Z]{4}$'")


def downgrade() -> None:
    raise NotImplementedError("Category codes and currencies are now required")
