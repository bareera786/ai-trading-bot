"""Merge user-related heads

Revision ID: 20260115_merge_user_heads
Revises: 20260114_add_user_role, 20260115_add_missing_user_columns
Create Date: 2026-01-15
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260115_merge_user_heads'
down_revision = ('20260114_add_user_role', '20260115_add_missing_user_columns')
branch_labels = None
depends_on = None


def upgrade():
    # This merge migration intentionally does not alter the schema.
    # It simply combines two heads into a single branch so Alembic can proceed.
    pass


def downgrade():
    pass
