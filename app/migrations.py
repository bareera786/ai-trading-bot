"""Database migration helpers extracted from the legacy monolith."""
from __future__ import annotations

import logging

from app.extensions import db

LOGGER = logging.getLogger("ai_trading_bot")


def migrate_database() -> None:
    """Apply idempotent ALTER TABLE statements for legacy schemas."""
    try:
        inspector = db.inspect(db.engine)

        try:
            user_columns = [col["name"] for col in inspector.get_columns("user")]
        except Exception:
            user_columns = []

        if "selected_symbols" not in user_columns:
            try:
                with db.engine.connect() as conn:
                    conn.execute(
                        db.text(
                            "ALTER TABLE \"user\" ADD COLUMN selected_symbols TEXT DEFAULT '[]'"
                        )
                    )
                LOGGER.info("✅ Added selected_symbols column to user table")
            except Exception as exc:
                LOGGER.warning("Could not add selected_symbols column: %s", exc)

        if "custom_symbols" not in user_columns:
            try:
                with db.engine.connect() as conn:
                    conn.execute(
                        db.text(
                            "ALTER TABLE \"user\" ADD COLUMN custom_symbols TEXT DEFAULT '[]'"
                        )
                    )
                LOGGER.info("✅ Added custom_symbols column to user table")
            except Exception as exc:
                LOGGER.warning("Could not add custom_symbols column: %s", exc)

        # Ensure email_verified exists on user table (older DBs may not have it)
        if "email_verified" not in user_columns:
            try:
                with db.engine.connect() as conn:
                    conn.execute(
                        db.text(
                            "ALTER TABLE \"user\" ADD COLUMN email_verified BOOLEAN DEFAULT FALSE"
                        )
                    )
                LOGGER.info("✅ Added email_verified column to user table")
            except Exception as exc:
                LOGGER.warning("Could not add email_verified column: %s", exc)

        try:
            portfolio_columns = [
                col["name"] for col in inspector.get_columns("user_portfolio")
            ]
        except Exception:
            portfolio_columns = []

        if "risk_preference" not in portfolio_columns:
            try:
                with db.engine.connect() as conn:
                    conn.execute(
                        db.text(
                            "ALTER TABLE user_portfolio ADD COLUMN risk_preference VARCHAR(20) DEFAULT 'moderate'"
                        )
                    )
                LOGGER.info("✅ Added risk_preference column to user_portfolio table")
            except Exception as exc:
                LOGGER.warning("Could not add risk_preference column: %s", exc)

        try:
            statements = []
            column_defaults = {
                "symbol": "ALTER TABLE user_portfolio ADD COLUMN symbol VARCHAR(20)",
                "quantity": "ALTER TABLE user_portfolio ADD COLUMN quantity FLOAT DEFAULT 0.0",
                "avg_price": "ALTER TABLE user_portfolio ADD COLUMN avg_price FLOAT DEFAULT 0.0",
                "current_price": "ALTER TABLE user_portfolio ADD COLUMN current_price FLOAT DEFAULT 0.0",
                "pnl": "ALTER TABLE user_portfolio ADD COLUMN pnl FLOAT DEFAULT 0.0",
                "pnl_percent": "ALTER TABLE user_portfolio ADD COLUMN pnl_percent FLOAT DEFAULT 0.0",
                "max_position_size": "ALTER TABLE user_portfolio ADD COLUMN max_position_size FLOAT DEFAULT 1000.0",
                "stop_loss": "ALTER TABLE user_portfolio ADD COLUMN stop_loss FLOAT",
                "take_profit": "ALTER TABLE user_portfolio ADD COLUMN take_profit FLOAT",
                "auto_trade_enabled": "ALTER TABLE user_portfolio ADD COLUMN auto_trade_enabled BOOLEAN DEFAULT 0",
                "risk_level": "ALTER TABLE user_portfolio ADD COLUMN risk_level VARCHAR(20) DEFAULT 'medium'",
            }
            for column, statement in column_defaults.items():
                if column not in portfolio_columns:
                    statements.append(statement)

            if statements:
                with db.engine.connect() as conn:
                    for stmt in statements:
                        try:
                            conn.execute(db.text(stmt))
                            LOGGER.info("✅ Executed migration: %s", stmt)
                        except Exception as exc:
                            LOGGER.warning(
                                "Could not execute migration statement %s: %s",
                                stmt,
                                exc,
                            )
        except Exception:
            pass

        try:
            trade_columns = [col["name"] for col in inspector.get_columns("user_trade")]
        except Exception:
            trade_columns = []

        trade_statements = {
            "signal_source": "ALTER TABLE user_trade ADD COLUMN signal_source VARCHAR(50)",
            "confidence_score": "ALTER TABLE user_trade ADD COLUMN confidence_score FLOAT",
            "leverage": "ALTER TABLE user_trade ADD COLUMN leverage INTEGER DEFAULT 1",
            "cost_basis": "ALTER TABLE user_trade ADD COLUMN cost_basis FLOAT DEFAULT 0.0",
            "realized_gains": "ALTER TABLE user_trade ADD COLUMN realized_gains FLOAT DEFAULT 0.0",
            "holding_period": "ALTER TABLE user_trade ADD COLUMN holding_period INTEGER DEFAULT 0",
            "tax_lot_id": "ALTER TABLE user_trade ADD COLUMN tax_lot_id VARCHAR(50)",
        }
        for column, statement in trade_statements.items():
            if column in trade_columns:
                continue
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text(statement))
                LOGGER.info("✅ Added %s column to user_trade table", column)
            except Exception as exc:
                LOGGER.warning("Could not add %s column: %s", column, exc)

        LOGGER.info("✅ Database migration (idempotent) completed")
    except Exception as exc:
        LOGGER.exception("⚠️ Database migration failed: %s", exc)


__all__ = ["migrate_database"]
