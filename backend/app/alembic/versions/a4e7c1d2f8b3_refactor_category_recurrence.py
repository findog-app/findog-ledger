"""Refactor category obligation configuration.

Revision ID: a4e7c1d2f8b3
Revises: 9f2a3b4c5d6e
"""

from alembic import op
import sqlalchemy as sa


revision = "a4e7c1d2f8b3"
down_revision = "9f2a3b4c5d6e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "category",
        sa.Column(
            "data_source_policy",
            sa.Enum(
                "MANUAL", "AUTOMATIC", "HYBRID",
                name="datasourcepolicy", native_enum=False,
            ),
            nullable=False,
            server_default="HYBRID",
        ),
    )
    op.add_column("category", sa.Column("recurrence_interval", sa.Integer(), nullable=True))
    op.add_column(
        "category",
        sa.Column(
            "recurrence_unit",
            sa.Enum("MONTH", "YEAR", name="recurrenceunit", native_enum=False),
            nullable=True,
        ),
    )
    op.add_column("category", sa.Column("recurrence_anchor", sa.Date(), nullable=True))

    op.execute(
        """
        UPDATE category
        SET data_source_policy = CASE creation_policy
            WHEN 'MANUAL_ONLY' THEN 'MANUAL'
            WHEN 'AUTO_ONLY' THEN 'AUTOMATIC'
            ELSE 'HYBRID'
        END,
        recurrence_interval = CASE
            WHEN period_generation_policy = 'PRECREATE' THEN 1
            ELSE NULL
        END,
        recurrence_unit = CASE
            WHEN period_generation_policy = 'PRECREATE' THEN 'MONTH'
            ELSE NULL
        END,
        recurrence_anchor = CASE
            WHEN period_generation_policy = 'PRECREATE' THEN DATE '2000-01-01'
            ELSE NULL
        END
        """
    )
    op.alter_column("category", "data_source_policy", server_default=None)
    op.create_check_constraint(
        "ck_category_recurrence_interval",
        "category",
        "recurrence_interval IS NULL OR recurrence_interval > 0",
    )
    op.drop_column("category", "creation_policy")
    op.drop_column("category", "period_generation_policy")


def downgrade() -> None:
    raise NotImplementedError("The category policy model was removed")
