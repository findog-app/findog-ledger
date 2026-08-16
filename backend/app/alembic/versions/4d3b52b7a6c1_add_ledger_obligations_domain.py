"""Add ledger obligations domain

Revision ID: 4d3b52b7a6c1
Revises: 22ee75a08d64
Create Date: 2026-03-25 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "4d3b52b7a6c1"
down_revision = "22ee75a08d64"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_user_id", "name"),
    )
    op.create_index(op.f("ix_ledger_owner_user_id"), "ledger", ["owner_user_id"])

    op.create_table(
        "ledger_membership",
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "role",
            sa.Enum("OWNER", "EDITOR", "VIEWER", name="ledgeraccessrole", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledger.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ledger_id", "user_id"),
        sa.UniqueConstraint("ledger_id", "user_id"),
    )

    op.create_table(
        "category_group",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledger.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ledger_id", "id"),
        sa.UniqueConstraint("ledger_id", "name"),
    )
    op.create_index(
        op.f("ix_category_group_ledger_id"), "category_group", ["ledger_id"]
    )

    op.create_table(
        "category",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["ledger_id", "category_group_id"],
            ["category_group.ledger_id", "category_group.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledger.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ledger_id", "category_group_id", "name"),
        sa.UniqueConstraint("ledger_id", "id"),
    )
    op.create_index(op.f("ix_category_category_group_id"), "category", ["category_group_id"])
    op.create_index(op.f("ix_category_ledger_id"), "category", ["ledger_id"])

    op.create_table(
        "obligation_template",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "creation_policy",
            sa.Enum(
                "MANUAL_ONLY",
                "AUTO_ONLY",
                "HYBRID",
                name="obligationcreationpolicy",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "period_generation_policy",
            sa.Enum(
                "PRECREATE",
                "ON_DEMAND",
                name="periodgenerationpolicy",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("due_day", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("due_day IS NULL OR (due_day >= 1 AND due_day <= 31)"),
        sa.ForeignKeyConstraint(
            ["ledger_id", "category_id"],
            ["category.ledger_id", "category.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledger.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ledger_id", "code"),
        sa.UniqueConstraint("ledger_id", "id"),
    )
    op.create_index(
        op.f("ix_obligation_template_category_id"),
        "obligation_template",
        ["category_id"],
    )
    op.create_index(
        op.f("ix_obligation_template_ledger_id"),
        "obligation_template",
        ["ledger_id"],
    )

    op.create_table(
        "obligation",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ledger_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "lifecycle",
            sa.Enum(
                "DRAFT",
                "COLLECTING_DATA",
                "READY",
                "PAID",
                "CANCELED",
                "ERROR",
                name="obligationlifecycle",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("period_year", sa.Integer(), nullable=False),
        sa.Column("period_month", sa.Integer(), nullable=False),
        sa.Column(
            "effective_value_source",
            sa.Enum(
                "UNKNOWN",
                "AUTOMATIC",
                "MANUAL",
                "MIXED",
                name="effectivevaluesourcemode",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("current_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column(
            "amount_state",
            sa.Enum(
                "UNKNOWN",
                "ESTIMATED",
                "CONFIRMED",
                "OVERRIDDEN",
                name="valuestate",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "amount_source",
            sa.Enum(
                "UNKNOWN",
                "AUTOMATIC",
                "MANUAL",
                name="currentvaluesource",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column(
            "issue_date_state",
            sa.Enum(
                "UNKNOWN",
                "ESTIMATED",
                "CONFIRMED",
                "OVERRIDDEN",
                name="valuestate",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "issue_date_source",
            sa.Enum(
                "UNKNOWN",
                "AUTOMATIC",
                "MANUAL",
                name="currentvaluesource",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "due_date_state",
            sa.Enum(
                "UNKNOWN",
                "ESTIMATED",
                "CONFIRMED",
                "OVERRIDDEN",
                name="valuestate",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "due_date_source",
            sa.Enum(
                "UNKNOWN",
                "AUTOMATIC",
                "MANUAL",
                name="currentvaluesource",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("last_auto_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("period_month >= 1 AND period_month <= 12"),
        sa.ForeignKeyConstraint(
            ["ledger_id", "category_id"],
            ["category.ledger_id", "category.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledger.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["ledger_id", "template_id"],
            ["obligation_template.ledger_id", "obligation_template.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ledger_id", "id"),
        sa.UniqueConstraint(
            "ledger_id",
            "template_id",
            "period_year",
            "period_month",
            name="uq_obligation_ledger_template_period",
        ),
    )
    op.create_index(op.f("ix_obligation_category_id"), "obligation", ["category_id"])
    op.create_index(op.f("ix_obligation_ledger_id"), "obligation", ["ledger_id"])
    op.create_index(op.f("ix_obligation_template_id"), "obligation", ["template_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_obligation_template_id"), table_name="obligation")
    op.drop_index(op.f("ix_obligation_ledger_id"), table_name="obligation")
    op.drop_index(op.f("ix_obligation_category_id"), table_name="obligation")
    op.drop_table("obligation")

    op.drop_index(
        op.f("ix_obligation_template_ledger_id"), table_name="obligation_template"
    )
    op.drop_index(
        op.f("ix_obligation_template_category_id"), table_name="obligation_template"
    )
    op.drop_table("obligation_template")

    op.drop_index(op.f("ix_category_ledger_id"), table_name="category")
    op.drop_index(op.f("ix_category_category_group_id"), table_name="category")
    op.drop_table("category")

    op.drop_index(op.f("ix_category_group_ledger_id"), table_name="category_group")
    op.drop_table("category_group")

    op.drop_table("ledger_membership")
    op.drop_index(op.f("ix_ledger_owner_user_id"), table_name="ledger")
    op.drop_table("ledger")
