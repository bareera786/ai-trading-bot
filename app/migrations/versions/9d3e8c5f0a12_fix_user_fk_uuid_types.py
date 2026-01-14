"""Fix user foreign key UUID types

Revision ID: 9d3e8c5f0a12
Revises: 6db7d32f431a
Create Date: 2026-01-14

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "9d3e8c5f0a12"
down_revision = "6db7d32f431a"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    dialect = bind.dialect.name
    # Only pass schema when using Postgres; SQLite doesn't have "public"
    if dialect == "postgresql":
        return table_name in insp.get_table_names(schema="public")
    return table_name in insp.get_table_names()


def upgrade():
    # The User table uses UUID PKs. Several dependent tables were previously
    # created with integer user_id columns, which breaks joins and can crash
    # request handling (e.g., portfolio refresh after login).
    #
    # We rebuild the affected tables with user_id as UUID.

    # Drop in dependency order. Use CASCADE on Postgres; plain DROP on SQLite.
    bind = op.get_bind()
    dialect = bind.dialect.name
    for table in ("audit_log", "user_subscription", "user_trade", "user_portfolio"):
        if _table_exists(table):
            if dialect == "postgresql":
                op.execute(sa.text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
            else:
                op.execute(sa.text(f'DROP TABLE IF EXISTS "{table}"'))

    bind = op.get_bind()
    dialect = bind.dialect.name

    # Create tables using Postgres-specific types when on Postgres,
    # otherwise use SQLite-compatible types/defaults.
    if dialect == "postgresql":
        # user_trade
        op.create_table(
            "user_trade",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("user.id"),
                nullable=False,
            ),
            sa.Column("symbol", sa.String(length=20)),
            sa.Column("trade_type", sa.String(length=20)),
            sa.Column("side", sa.String(length=10)),
            sa.Column("quantity", sa.Float()),
            sa.Column("entry_price", sa.Float()),
            sa.Column("exit_price", sa.Float(), server_default="0.0"),
            sa.Column("pnl", sa.Float(), server_default="0.0"),
            sa.Column("status", sa.String(length=20), server_default="open"),
            sa.Column("signal_source", sa.String(length=50)),
            sa.Column("confidence_score", sa.Float()),
            sa.Column("leverage", sa.Integer(), server_default="1"),
            sa.Column("timestamp", sa.DateTime(), server_default=sa.text("now()")),
            sa.Column("cost_basis", sa.Float(), server_default="0.0"),
            sa.Column("realized_gains", sa.Float(), server_default="0.0"),
            sa.Column("holding_period", sa.Integer(), server_default="0"),
            sa.Column("tax_lot_id", sa.String(length=50)),
        )
        op.create_index("ix_user_trade_user_id", "user_trade", ["user_id"])

        # user_portfolio
        op.create_table(
            "user_portfolio",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("user.id"),
                nullable=False,
            ),
            sa.Column("symbol", sa.String(length=20), nullable=True),
            sa.Column("quantity", sa.Float(), server_default="0.0"),
            sa.Column("avg_price", sa.Float(), server_default="0.0"),
            sa.Column("current_price", sa.Float(), server_default="0.0"),
            sa.Column("pnl", sa.Float(), server_default="0.0"),
            sa.Column("pnl_percent", sa.Float(), server_default="0.0"),
            sa.Column("max_position_size", sa.Float(), server_default="1000.0"),
            sa.Column("stop_loss", sa.Float(), nullable=True),
            sa.Column("take_profit", sa.Float(), nullable=True),
            sa.Column("auto_trade_enabled", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("risk_level", sa.String(length=20), server_default="medium"),
            sa.Column("total_balance", sa.Float(), server_default="10000.0"),
            sa.Column("available_balance", sa.Float(), server_default="10000.0"),
            sa.Column("total_profit_loss", sa.Float(), server_default="0.0"),
            sa.Column("daily_pnl", sa.Float(), server_default="0.0"),
            sa.Column("open_positions", sa.JSON(), server_default=sa.text("'{}'::json")),
            sa.Column("risk_preference", sa.String(length=20), server_default="moderate"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        )
        op.create_index("ix_user_portfolio_user_id", "user_portfolio", ["user_id"])

        # user_subscription
        op.create_table(
            "user_subscription",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("user.id"),
                nullable=False,
            ),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plan.id"), nullable=False),
            sa.Column("status", sa.String(length=20), server_default="trialing"),
            sa.Column("trial_end", sa.DateTime(), nullable=True),
            sa.Column("current_period_start", sa.DateTime(), server_default=sa.text("now()")),
            sa.Column("current_period_end", sa.DateTime(), nullable=True),
            sa.Column("next_billing_date", sa.DateTime(), nullable=True),
            sa.Column("auto_renew", sa.Boolean(), server_default=sa.text("true")),
            sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.text("false")),
            sa.Column("canceled_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.String(length=255)),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        )
        op.create_index(
            "ix_user_subscription_user_id",
            "user_subscription",
            ["user_id"],
        )

        # audit_log
        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("user.id"),
                nullable=True,
            ),
            sa.Column("action", sa.String(length=255), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("details", sa.Text(), nullable=True),
        )
        op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    else:
        # SQLite-compatible table creation
        op.create_table(
            "user_trade",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user.id"), nullable=False),
            sa.Column("symbol", sa.String(length=20)),
            sa.Column("trade_type", sa.String(length=20)),
            sa.Column("side", sa.String(length=10)),
            sa.Column("quantity", sa.Float()),
            sa.Column("entry_price", sa.Float()),
            sa.Column("exit_price", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("pnl", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("status", sa.String(length=20), server_default=sa.text("'open'")),
            sa.Column("signal_source", sa.String(length=50)),
            sa.Column("confidence_score", sa.Float()),
            sa.Column("leverage", sa.Integer(), server_default=sa.text('1')),
            sa.Column("timestamp", sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column("cost_basis", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("realized_gains", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("holding_period", sa.Integer(), server_default=sa.text('0')),
            sa.Column("tax_lot_id", sa.String(length=50)),
        )
        op.create_index("ix_user_trade_user_id", "user_trade", ["user_id"])

        op.create_table(
            "user_portfolio",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user.id"), nullable=False),
            sa.Column("symbol", sa.String(length=20), nullable=True),
            sa.Column("quantity", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("avg_price", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("current_price", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("pnl", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("pnl_percent", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("max_position_size", sa.Float(), server_default=sa.text('1000.0')),
            sa.Column("stop_loss", sa.Float(), nullable=True),
            sa.Column("take_profit", sa.Float(), nullable=True),
            sa.Column("auto_trade_enabled", sa.Boolean(), server_default=sa.text('0')),
            sa.Column("risk_level", sa.String(length=20), server_default=sa.text("'medium'")),
            sa.Column("total_balance", sa.Float(), server_default=sa.text('10000.0')),
            sa.Column("available_balance", sa.Float(), server_default=sa.text('10000.0')),
            sa.Column("total_profit_loss", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("daily_pnl", sa.Float(), server_default=sa.text('0.0')),
            sa.Column("open_positions", sa.Text(), server_default=sa.text("'{}'")),
            sa.Column("risk_preference", sa.String(length=20), server_default=sa.text("'moderate'")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        )
        op.create_index("ix_user_portfolio_user_id", "user_portfolio", ["user_id"])

        op.create_table(
            "user_subscription",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user.id"), nullable=False),
            sa.Column("plan_id", sa.Integer(), sa.ForeignKey("subscription_plan.id"), nullable=False),
            sa.Column("status", sa.String(length=20), server_default=sa.text("'trialing'")),
            sa.Column("trial_end", sa.DateTime(), nullable=True),
            sa.Column("current_period_start", sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column("current_period_end", sa.DateTime(), nullable=True),
            sa.Column("next_billing_date", sa.DateTime(), nullable=True),
            sa.Column("auto_renew", sa.Boolean(), server_default=sa.text('1')),
            sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.text('0')),
            sa.Column("canceled_at", sa.DateTime(), nullable=True),
            sa.Column("notes", sa.String(length=255)),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        )
        op.create_index(
            "ix_user_subscription_user_id",
            "user_subscription",
            ["user_id"],
        )

        op.create_table(
            "audit_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.String(length=36), sa.ForeignKey("user.id"), nullable=True),
            sa.Column("action", sa.String(length=255), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.Column("details", sa.Text(), nullable=True),
        )
        op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])


def downgrade():
    # Non-reversible without knowing prior schemas/data.
    pass
