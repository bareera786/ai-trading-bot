"""Reset user table to simple schema

Revision ID: 20260115_reset_user_table
Revises: d6815894d43f
Create Date: 2026-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260115_reset_user_table'
down_revision = '6db7d32f431a'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing user table
    op.drop_table('user')

    # Create the new simple user table
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(length=150), nullable=False, unique=True),
        sa.Column('email', sa.String(length=150), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(length=150), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.text('now()')),
    )


def downgrade():
    # Drop the simple user table
    op.drop_table('user')

    # Recreate the complex user table (for rollback purposes)
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('username', sa.String(length=150), nullable=False, unique=True),
        sa.Column('email', sa.String(length=150), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(length=150), nullable=False),
        sa.Column('role', sa.Enum('admin', 'trader', 'viewer', name='roleenum'), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('1')),
        sa.Column('email_verified', sa.Boolean(), nullable=True, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('last_ip', sa.String(length=45), nullable=True),
        sa.Column('failed_login_count', sa.Integer(), nullable=True, server_default=sa.text('0')),
        sa.Column('locked_until', sa.DateTime(), nullable=True),
    )