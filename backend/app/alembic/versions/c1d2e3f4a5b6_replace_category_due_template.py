"""Replace category recurrence anchor and due day with first due date.

Revision ID: c1d2e3f4a5b6
Revises: 6f7a8b9c0d1e
"""

from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "6f7a8b9c0d1e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("category", sa.Column("first_due_date", sa.Date(), nullable=True))
    op.execute(
        """
        UPDATE category
        SET first_due_date = make_date(
            EXTRACT(YEAR FROM recurrence_anchor)::integer,
            EXTRACT(MONTH FROM recurrence_anchor)::integer,
            LEAST(
                COALESCE(due_day, EXTRACT(DAY FROM recurrence_anchor)::integer),
                EXTRACT(
                    DAY FROM (date_trunc('month', recurrence_anchor)
                    + INTERVAL '1 month - 1 day')
                )::integer
            )
        )
        WHERE recurrence_anchor IS NOT NULL
        """
    )
    op.drop_constraint("ck_category_due_day", "category", type_="check")
    op.drop_column("category", "due_day")
    op.drop_column("category", "recurrence_anchor")


def downgrade() -> None:
    raise NotImplementedError("The category due-date template cannot be split safely")
