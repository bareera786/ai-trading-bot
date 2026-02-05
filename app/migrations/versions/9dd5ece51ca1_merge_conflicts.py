"""merge_conflicts

Revision ID: 9dd5ece51ca1
Revises: 20260115_merge_user_heads, convert_float_to_numeric
Create Date: 2026-01-20 19:33:59.436699

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9dd5ece51ca1'
down_revision = ('20260115_merge_user_heads', 'convert_float_to_numeric')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
