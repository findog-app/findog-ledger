"""Refactor category data snapshots into timestamped records.

Revision ID: 2a6e9d4c7b1f
Revises: 8d4f6a1b2c3e
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "2a6e9d4c7b1f"
down_revision = "8d4f6a1b2c3e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("category_data", sa.Column("id", postgresql.UUID(as_uuid=True)))
    op.add_column("category_data", sa.Column("observed_at", sa.DateTime(timezone=True)))
    op.add_column("category_data", sa.Column("source", sa.String(length=255)))
    op.add_column("category_data", sa.Column("external_id", sa.String(length=255)))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT category_id FROM category_data")).all()
    for (category_id,) in rows:
        connection.execute(
            sa.text(
                "UPDATE category_data SET id = :id WHERE category_id = :category_id"
            ),
            {"id": uuid.uuid4(), "category_id": category_id},
        )
    connection.execute(
        sa.text(
            "UPDATE category_data SET observed_at = updated_at WHERE observed_at IS NULL"
        )
    )

    op.alter_column("category_data", "id", nullable=False)
    op.alter_column("category_data", "observed_at", nullable=False)
    op.drop_constraint("category_data_pkey", "category_data", type_="primary")
    op.create_primary_key("category_data_pkey", "category_data", ["id"])
    op.create_index(
        "ix_category_data_category_observed_at",
        "category_data",
        ["category_id", sa.text("observed_at DESC")],
    )
    op.create_index(
        "uq_category_data_source_external_id",
        "category_data",
        ["category_id", "source", "external_id"],
        unique=True,
        postgresql_where=sa.text("source IS NOT NULL AND external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_category_data_source_external_id", table_name="category_data")
    op.drop_index("ix_category_data_category_observed_at", table_name="category_data")
    op.drop_constraint("category_data_pkey", "category_data", type_="primary")
    op.create_primary_key("category_data_pkey", "category_data", ["category_id"])
    op.drop_column("category_data", "external_id")
    op.drop_column("category_data", "source")
    op.drop_column("category_data", "observed_at")
    op.drop_column("category_data", "id")
