"""Make category codes immutable.

Revision ID: f2a9c5d7e3b1
Revises: c9e2f6a1b4d7
"""

from alembic import op


revision = "f2a9c5d7e3b1"
down_revision = "c9e2f6a1b4d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION prevent_category_code_change()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.code IS DISTINCT FROM OLD.code THEN
                RAISE EXCEPTION 'Category code is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER category_code_immutable
        BEFORE UPDATE ON category
        FOR EACH ROW EXECUTE FUNCTION prevent_category_code_change()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER category_code_immutable ON category")
    op.execute("DROP FUNCTION prevent_category_code_change()")
