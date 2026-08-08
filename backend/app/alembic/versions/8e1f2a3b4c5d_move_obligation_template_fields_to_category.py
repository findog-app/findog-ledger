"""Move obligation template configuration onto categories.

Revision ID: 8e1f2a3b4c5d
Revises: 7c8f4a1d2b9e
"""

from alembic import op
import sqlalchemy as sa


revision = "8e1f2a3b4c5d"
down_revision = "7c8f4a1d2b9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("category", sa.Column("code", sa.String(length=100), nullable=True))
    op.add_column(
        "category",
        sa.Column(
            "creation_policy",
            sa.Enum(
                "MANUAL_ONLY", "AUTO_ONLY", "HYBRID",
                name="obligationcreationpolicy", native_enum=False,
            ),
            nullable=False,
            server_default="HYBRID",
        ),
    )
    op.add_column(
        "category",
        sa.Column(
            "period_generation_policy",
            sa.Enum(
                "PRECREATE", "ON_DEMAND",
                name="periodgenerationpolicy", native_enum=False,
            ),
            nullable=False,
            server_default="PRECREATE",
        ),
    )
    op.add_column("category", sa.Column("currency", sa.String(length=3), nullable=True))
    op.add_column("category", sa.Column("due_day", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_category_due_day", "category",
        "due_day IS NULL OR (due_day >= 1 AND due_day <= 31)",
    )

    # A category is the replacement identity. If legacy data contains more than
    # one template for a category, retain the earliest template deterministically.
    op.execute(
        sa.text(
            """
            WITH selected AS (
                SELECT DISTINCT ON (category_id)
                    category_id, code, creation_policy, period_generation_policy,
                    currency, due_day
                FROM obligation_template
                ORDER BY category_id, created_at ASC, id ASC
            )
            UPDATE category AS c
            SET code = selected.code,
                creation_policy = selected.creation_policy,
                period_generation_policy = selected.period_generation_policy,
                currency = selected.currency,
                due_day = selected.due_day
            FROM selected
            WHERE c.id = selected.category_id
            """
        )
    )

    # Existing obligations already carry category_id. Remove duplicates before
    # changing the period uniqueness key from template to category.
    op.execute(
        sa.text(
            """
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (
                    PARTITION BY ledger_id, category_id, period_year, period_month
                    ORDER BY created_at ASC, id ASC
                ) AS row_number
                FROM obligation
            )
            DELETE FROM obligation
            WHERE id IN (SELECT id FROM ranked WHERE row_number > 1)
            """
        )
    )
    op.drop_constraint("uq_obligation_ledger_template_period", "obligation", type_="unique")
    op.create_unique_constraint(
        "uq_obligation_ledger_category_period", "obligation",
        ["ledger_id", "category_id", "period_year", "period_month"],
    )
    op.drop_constraint("obligation_ledger_id_template_id_fkey", "obligation", type_="foreignkey")
    op.drop_index("ix_obligation_template_id", table_name="obligation")
    op.drop_column("obligation", "template_id")

    op.create_unique_constraint("uq_category_ledger_code", "category", ["ledger_id", "code"])
    op.drop_index("ix_obligation_template_ledger_id", table_name="obligation_template")
    op.drop_index("ix_obligation_template_category_id", table_name="obligation_template")
    op.drop_table("obligation_template")

    op.alter_column("category", "creation_policy", server_default=None)
    op.alter_column("category", "period_generation_policy", server_default=None)


def downgrade() -> None:
    raise NotImplementedError("The legacy obligation-template domain was removed")
