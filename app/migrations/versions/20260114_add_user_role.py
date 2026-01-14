"""Idempotent: ensure `user.role` exists (Postgres enum or SQLite varchar)

Revision ID: 20260114_add_user_role
Revises: 9d3e8c5f0a12
Create Date: 2026-01-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# Alembic identifiers
revision = "20260114_add_user_role"
down_revision = "9d3e8c5f0a12"
branch_labels = None
depends_on = None


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    insp = inspect(bind)
    try:
        cols = [c.get("name") for c in insp.get_columns(table_name)]
    except Exception:
        return False
    return column_name in cols


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name.lower()

    # If column already exists, nothing to do
    if _column_exists(bind, "user", "role"):
        return

    if dialect in ("postgres", "postgresql"):
        # Create enum type if missing and add enum column if missing.
        # Use a DO block with checks to make the operation idempotent.
        op.execute(
            text(
                """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'roleenum') THEN
    CREATE TYPE roleenum AS ENUM ('admin', 'trader', 'viewer');
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'user' AND column_name = 'role'
  ) THEN
    ALTER TABLE "user" ADD COLUMN role roleenum NOT NULL DEFAULT 'viewer';
  END IF;
END
$$;
"""
            )
        )
    else:
        # SQLite and other dialects: add a VARCHAR fallback column with default
        # Use batch_alter_table for SQLite ALTER TABLE safety
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column("role", sa.String(length=20), nullable=False, server_default="viewer")
            )


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name.lower()

    # If column doesn't exist, nothing to do
    if not _column_exists(bind, "user", "role"):
        return

    if dialect in ("postgres", "postgresql"):
        # Drop the column if present. We avoid dropping the enum type to be conservative.
        op.execute(text('ALTER TABLE "user" DROP COLUMN IF EXISTS role;'))
    else:
        with op.batch_alter_table("user", schema=None) as batch_op:
            batch_op.drop_column("role")
