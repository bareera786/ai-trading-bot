"""Merge conflicting heads

Revision ID: 6db7d32f431a
Revises: ae092e49e678, d6815894d43f
Create Date: 2026-01-13 04:09:02.806737

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6db7d32f431a'
down_revision = ('ae092e49e678', 'd6815894d43f')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
