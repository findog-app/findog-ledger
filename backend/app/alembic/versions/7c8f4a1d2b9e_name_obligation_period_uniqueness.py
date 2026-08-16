"""Name obligation period uniqueness constraint

Revision ID: 7c8f4a1d2b9e
Revises: 4d3b52b7a6c1
Create Date: 2026-03-25 00:00:01.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7c8f4a1d2b9e"
down_revision = "4d3b52b7a6c1"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "uq_obligation_ledger_template_period"
LEGACY_CONSTRAINT_NAME = "obligation_ledger_id_template_id_period_year_period_month_key"


def upgrade() -> None:
    # Keep the earliest record per (ledger, template, year, month) group.
    # Deleting duplicates is acceptable at this stage and keeps the migration simple.
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY ledger_id, template_id, period_year, period_month
                        ORDER BY created_at ASC, id ASC
                    ) AS row_number
                FROM obligation
            )
            DELETE FROM obligation
            WHERE id IN (
                SELECT id
                FROM ranked
                WHERE row_number > 1
            )
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            ALTER TABLE obligation
            DROP CONSTRAINT IF EXISTS {LEGACY_CONSTRAINT_NAME}
            """
        )
    )

    connection = op.get_bind()
    constraint_exists = connection.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_constraint
            WHERE conname = :constraint_name
            """
        ),
        {"constraint_name": CONSTRAINT_NAME},
    ).scalar()
    if constraint_exists:
        return

    op.create_unique_constraint(
        CONSTRAINT_NAME,
        "obligation",
        ["ledger_id", "template_id", "period_year", "period_month"],
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "obligation", type_="unique")
    op.create_unique_constraint(
        LEGACY_CONSTRAINT_NAME,
        "obligation",
        ["ledger_id", "template_id", "period_year", "period_month"],
    )
