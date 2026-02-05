"""baseline schema

Revision ID: ae092e49e678
Revises: 
Create Date: 2026-01-13 04:02:30.964640

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'ae092e49e678'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Make creation idempotent: avoid creating enum type twice
    bind = op.get_bind()
    insp = inspect(bind)
    # Make this migration dialect-aware so it can run on SQLite (local dev)
    dialect_name = bind.dialect.name
    if dialect_name == 'postgresql':
        # PostgreSQL enum type check
        # PostgreSQL enum type check
        try:
            # Check if type exists in pg_type
            enum_exists = bool(bind.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'roleenum'"))
                                .fetchone())
        except Exception:
            enum_exists = False
            
        if not enum_exists:
            try:
                # Add extra safety try/except for race conditions
                op.execute(sa.text("CREATE TYPE roleenum AS ENUM ('admin', 'trader', 'viewer')"))
            except Exception as e:
                # If it fails with DuplicateObject, ignore it (it exists now)
                if 'DuplicateObject' not in str(e) and 'already exists' not in str(e):
                    raise e

        # Determine if we should tell SQLAlchemy to create the type
        # We handle creation explicitly above, so set create_type=False in the column definition
        # ONLY if the dialect handles it. Safest is to rely on the check above and 
        # ensure the column definition doesn't try to create it again.
        
        # Since roleenum persists and crashes migrations, we treat it as an existing server-side type
        # Or even simpler: Use sa.VARCHAR for SQLite compatibility if needed, but for Postgres:
        # We define the column as using the EXISTING type 'roleenum' without trying to create it.
        
        if not insp.has_table('user'):
            op.create_table(
                'user',
                sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),  # type: ignore
                sa.Column('username', sa.String(length=150), nullable=False, unique=True),
                sa.Column('email', sa.String(length=150), nullable=False, unique=True, index=True),
                sa.Column('password_hash', sa.String(length=150), nullable=False),
                # Bypass SQLAlchemy Enum creation logic entirely by using a custom type definition or just the name
                sa.Column('role', sa.dialects.postgresql.ENUM('admin', 'trader', 'viewer', name='roleenum', create_type=False), nullable=False, server_default='viewer'),
                sa.Column('is_active', sa.Boolean, server_default=sa.text('1')),
                sa.Column('email_verified', sa.Boolean, server_default=sa.text('0')),
                sa.Column('created_at', sa.DateTime, nullable=False),
                sa.Column('last_login_at', sa.DateTime, nullable=True),
                sa.Column('last_ip', sa.String(length=45), nullable=True),
                sa.Column('failed_login_count', sa.Integer, server_default=sa.text('0')),
                sa.Column('locked_until', sa.DateTime, nullable=True),
            )
        else:
            print("Table 'user' already exists, skipping creation.")
    else:
        # SQLite and other dialects: use compatible column types and skip CREATE TYPE
        op.create_table(
            'user',
            sa.Column('id', sa.String(length=36), nullable=False, primary_key=True),
            sa.Column('username', sa.String(length=150), nullable=False, unique=True),
            sa.Column('email', sa.String(length=150), nullable=False, unique=True),
            sa.Column('password_hash', sa.String(length=150), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False, server_default=sa.text("'viewer'")),
            sa.Column('is_active', sa.Boolean, server_default=sa.text('1')),
            sa.Column('email_verified', sa.Boolean, server_default=sa.text('0')),
            sa.Column('created_at', sa.DateTime, nullable=False),
            sa.Column('last_login_at', sa.DateTime, nullable=True),
            sa.Column('last_ip', sa.String(length=45), nullable=True),
            sa.Column('failed_login_count', sa.Integer, server_default=sa.text('0')),
            sa.Column('locked_until', sa.DateTime, nullable=True),
        )


def downgrade():
    op.drop_table('user')
