"""Update User model for enterprise-grade user management

Revision ID: d6815894d43f
Revises: 
Create Date: 2026-01-13 03:44:05.550062

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'd6815894d43f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Make this migration idempotent: check for existing columns/indexes first
    bind = op.get_bind()
    insp = inspect(bind)
    with op.batch_alter_table('user', schema=None) as batch_op:
        # Use get_columns to detect presence of a column rather than
        # relying on a (non-public) helper on Inspector which some
        # linters/type-checkers may not recognise.
        existing_columns = [c.get('name') for c in insp.get_columns('user')]
        if 'last_ip' not in existing_columns:
            batch_op.add_column(sa.Column('last_ip', sa.String(length=45), nullable=True))
        if 'failed_login_count' not in existing_columns:
            batch_op.add_column(sa.Column('failed_login_count', sa.Integer(), nullable=True))

        # create index if it does not exist
        existing_indexes = [idx.get('name') for idx in insp.get_indexes('user')]
        if batch_op.f('ix_user_email') not in existing_indexes:
            batch_op.create_index(batch_op.f('ix_user_email'), ['email'], unique=True)

    # Skip dropping columns to avoid conflicts
    pass


def downgrade():
    # Skip adding columns to avoid conflicts
    pass
