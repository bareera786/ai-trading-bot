"""add training_job columns

Revision ID: 20260130000001
Revises: 20260130000000
Create Date: 2026-01-30 00:00:01.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '20260130000001'
down_revision = '20260130000000'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('training_job', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('completed_at', sa.DateTime(), nullable=True))

    # Optional: Backfill created_at if specific logic needed (e.g. now())
    op.execute(sa.text("UPDATE training_job SET created_at = NOW() WHERE created_at IS NULL"))

def downgrade():
    with op.batch_alter_table('training_job', schema=None) as batch_op:
        batch_op.drop_column('completed_at')
        batch_op.drop_column('created_at')
