"""Add schema-validated category data.

Revision ID: 8d4f6a1b2c3e
Revises: c1d2e3f4a5b6
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "8d4f6a1b2c3e"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "category_data_schema",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", "version"),
    )
    op.create_index(
        "uq_category_data_schema_active",
        "category_data_schema",
        ["category_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )
    op.create_table(
        "category_data",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["category_id", "schema_version"],
            ["category_data_schema.category_id", "category_data_schema.version"],
        ),
        sa.PrimaryKeyConstraint("category_id"),
    )


def downgrade() -> None:
    op.drop_table("category_data")
    op.drop_index("uq_category_data_schema_active", table_name="category_data_schema")
    op.drop_table("category_data_schema")
