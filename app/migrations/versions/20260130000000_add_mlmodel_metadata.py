"""add mlmodel metadata

Revision ID: 20260130000000
Revises: 20260120212500
Create Date: 2026-01-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260130000000'
down_revision = '20260120212500'
branch_labels = None
depends_on = None

def upgrade():
    # Use batch_alter_table for SQLite compatibility just in case, though production is Postgres
    with op.batch_alter_table('ml_model', schema=None) as batch_op:
        batch_op.add_column(sa.Column('symbol', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('file_path', sa.String(length=255), nullable=True))

def downgrade():
    with op.batch_alter_table('ml_model', schema=None) as batch_op:
        batch_op.drop_column('file_path')
        batch_op.drop_column('symbol')
