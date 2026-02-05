"""Convert Float to Numeric for financial precision

Revision ID: convert_float_to_numeric
Revises: 
Create Date: 2026-01-18

CRITICAL SECURITY FIX: Convert all financial Float fields to Numeric(20, 8)
to prevent floating-point precision errors in P&L calculations.

Float precision errors are unacceptable for financial data.
Example: 0.1 + 0.2 != 0.3 in float arithmetic

This migration converts 24 Float columns across 3 tables:
- UserTrade: quantity, entry_price, exit_price, pnl, confidence_score, cost_basis, realized_pnl, realized_gains
- UserPortfolio: quantity, avg_price, current_price, pnl, pnl_percent, max_position_size, stop_loss, take_profit, total_balance, available_balance, total_profit_loss, daily_pnl
- DailyMetrics: total_pnl, total_volume, max_drawdown
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'convert_float_to_numeric'
down_revision = None  # Update this to the latest migration
branch_labels = None
depends_on = None


def upgrade():
    """Convert Float columns to Numeric(20, 8) for financial precision."""
    
    # Determine if we're using PostgreSQL or SQLite
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    
    # Numeric type with 20 total digits, 8 decimal places
    # Supports values up to 999,999,999,999.99999999
    numeric_type = sa.Numeric(precision=20, scale=8)
    
    # Helper to check if table exists
    from sqlalchemy import inspect
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    
    def table_has_column(table_name, column_name):
        if table_name not in existing_tables:
            return False
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns
    
    # UserTrade table conversions
    if 'user_trade' in existing_tables:
        with op.batch_alter_table('user_trade', schema=None) as batch_op:
            if table_has_column('user_trade', 'quantity'):
                batch_op.alter_column('quantity',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True)
            if table_has_column('user_trade', 'entry_price'):
                batch_op.alter_column('entry_price',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True)
            if table_has_column('user_trade', 'exit_price'):
                batch_op.alter_column('exit_price',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('user_trade', 'pnl'):
                batch_op.alter_column('pnl',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('user_trade', 'confidence_score'):
                batch_op.alter_column('confidence_score',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True)
            if table_has_column('user_trade', 'cost_basis'):
                batch_op.alter_column('cost_basis',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            # NOTE: realized_pnl column removed - doesn't exist in current schema
            if table_has_column('user_trade', 'realized_gains'):
                batch_op.alter_column('realized_gains',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
    
    # UserPortfolio table conversions
    if 'user_portfolio' in existing_tables:
        with op.batch_alter_table('user_portfolio', schema=None) as batch_op:
            if table_has_column('user_portfolio', 'quantity'):
                batch_op.alter_column('quantity',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('user_portfolio', 'avg_price'):
                batch_op.alter_column('avg_price',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('user_portfolio', 'current_price'):
                batch_op.alter_column('current_price',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('user_portfolio', 'pnl'):
                batch_op.alter_column('pnl',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('user_portfolio', 'pnl_percent'):
                batch_op.alter_column('pnl_percent',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('user_portfolio', 'max_position_size'):
                batch_op.alter_column('max_position_size',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='1000.0')
            if table_has_column('user_portfolio', 'stop_loss'):
                batch_op.alter_column('stop_loss',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True)
            if table_has_column('user_portfolio', 'take_profit'):
                batch_op.alter_column('take_profit',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True)
            if table_has_column('user_portfolio', 'total_balance'):
                batch_op.alter_column('total_balance',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='10000.0')
            if table_has_column('user_portfolio', 'available_balance'):
                batch_op.alter_column('available_balance',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='10000.0')
            if table_has_column('user_portfolio', 'total_profit_loss'):
                batch_op.alter_column('total_profit_loss',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('user_portfolio', 'daily_pnl'):
                batch_op.alter_column('daily_pnl',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
    
    # DailyMetrics table conversions - only if table exists
    if 'daily_metrics' in existing_tables:
        with op.batch_alter_table('daily_metrics', schema=None) as batch_op:
            if table_has_column('daily_metrics', 'total_pnl'):
                batch_op.alter_column('total_pnl',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('daily_metrics', 'total_volume'):
                batch_op.alter_column('total_volume',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')
            if table_has_column('daily_metrics', 'max_drawdown'):
                batch_op.alter_column('max_drawdown',
                                      existing_type=sa.Float(),
                                      type_=numeric_type,
                                      existing_nullable=True,
                                      existing_server_default='0.0')


def downgrade():
    """Revert Numeric columns back to Float (NOT RECOMMENDED - loses precision)."""
    
    # WARNING: Downgrading will lose precision! Only use for rollback in emergency.
    
    # DailyMetrics table reversions
    with op.batch_alter_table('daily_metrics', schema=None) as batch_op:
        batch_op.alter_column('max_drawdown',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('total_volume',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('total_pnl',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
    
    # UserPortfolio table reversions
    with op.batch_alter_table('user_portfolio', schema=None) as batch_op:
        batch_op.alter_column('daily_pnl',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('total_profit_loss',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('available_balance',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('total_balance',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('take_profit',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('stop_loss',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('max_position_size',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('pnl_percent',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('pnl',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('current_price',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('avg_price',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('quantity',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
    
    # UserTrade table reversions
    with op.batch_alter_table('user_trade', schema=None) as batch_op:
        batch_op.alter_column('realized_gains',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        # NOTE: realized_pnl column removed - doesn't exist in current schema
        batch_op.alter_column('cost_basis',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('confidence_score',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('pnl',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('exit_price',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('entry_price',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
        batch_op.alter_column('quantity',
                              existing_type=sa.Numeric(precision=20, scale=8),
                              type_=sa.Float(),
                              existing_nullable=True)
