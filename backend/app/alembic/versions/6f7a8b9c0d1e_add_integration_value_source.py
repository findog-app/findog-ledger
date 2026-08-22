"""Add integration as an obligation value source.

Revision ID: 6f7a8b9c0d1e
Revises: 5e6f7a8b9c0d
"""

import sqlalchemy as sa
from alembic import op

revision = "6f7a8b9c0d1e"
down_revision = "5e6f7a8b9c0d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in (
        "effective_value_source",
        "amount_source",
        "issue_date_source",
        "due_date_source",
    ):
        op.alter_column(
            "obligation",
            column,
            existing_type=sa.String(length=9),
            type_=sa.String(length=11),
            existing_nullable=False,
        )


def downgrade() -> None:
    for column in (
        "effective_value_source",
        "amount_source",
        "issue_date_source",
        "due_date_source",
    ):
        op.alter_column(
            "obligation",
            column,
            existing_type=sa.String(length=11),
            type_=sa.String(length=9),
            existing_nullable=False,
        )
