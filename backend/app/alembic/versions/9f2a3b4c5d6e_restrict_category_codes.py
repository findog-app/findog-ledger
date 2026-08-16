"""Restrict category codes to four uppercase English letters.

Revision ID: 9f2a3b4c5d6e
Revises: 8e1f2a3b4c5d
"""

from alembic import op
import sqlalchemy as sa


revision = "9f2a3b4c5d6e"
down_revision = "8e1f2a3b4c5d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Legacy values cannot satisfy the new invariant; clear them so they can
    # be re-entered in the new format without blocking the migration.
    op.execute(
        sa.text(
            """
            UPDATE category
            SET code = NULL
            WHERE code IS NOT NULL
              AND code !~ '^[A-Z]{4}$'
            """
        )
    )
    op.alter_column(
        "category",
        "code",
        existing_type=sa.String(length=100),
        type_=sa.String(length=4),
    )
    op.create_check_constraint(
        "ck_category_code_four_uppercase",
        "category",
        "code IS NULL OR code ~ '^[A-Z]{4}$'",
    )


def downgrade() -> None:
    op.drop_constraint("ck_category_code_four_uppercase", "category", type_="check")
    op.alter_column(
        "category",
        "code",
        existing_type=sa.String(length=4),
        type_=sa.String(length=100),
    )
