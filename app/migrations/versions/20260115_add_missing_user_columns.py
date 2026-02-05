"""Add missing columns to user table

Revision ID: 20260115_add_missing_user_columns
Revises: 20260115_reset_user_table
Create Date: 2026-01-15 12:45:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260115_add_missing_user_columns"
down_revision = "20260115_reset_user_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    from sqlalchemy import inspect
    import sqlalchemy as sa
    
    inspector = inspect(conn)
    columns = [x['name'] for x in inspector.get_columns('user')]

    if 'last_login' not in columns:
        op.add_column('user', sa.Column('last_login', sa.DateTime(), nullable=True))
    
    if 'selected_symbols' not in columns:
        op.add_column('user', sa.Column('selected_symbols', sa.Text(), server_default='[]', nullable=True))

    if 'custom_symbols' not in columns:
        op.add_column('user', sa.Column('custom_symbols', sa.Text(), server_default='[]', nullable=True))

    if 'failed_login_count' not in columns:
        op.add_column('user', sa.Column('failed_login_count', sa.Integer(), server_default='0', nullable=True))

    if 'locked_until' not in columns:
        op.add_column('user', sa.Column('locked_until', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.execute("ALTER TABLE \"user\" DROP COLUMN IF EXISTS locked_until")
    op.execute("ALTER TABLE \"user\" DROP COLUMN IF EXISTS failed_login_count")
    op.execute("ALTER TABLE \"user\" DROP COLUMN IF EXISTS custom_symbols")
    op.execute("ALTER TABLE \"user\" DROP COLUMN IF EXISTS selected_symbols")
    op.execute("ALTER TABLE \"user\" DROP COLUMN IF EXISTS last_login")
