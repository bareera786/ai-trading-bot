import pytest
from app import create_app
from app.extensions import db
from app.models import User, UserTrade

import ai_ml_auto_bot_final as bot_module


def test_system_trade_records_to_db():
    app = create_app()
    app.testing = True
    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create a system user to attribute automated trades to
        user = User(username="system_user", email="system@example.com")  # type: ignore
        user.set_password("pass")
        db.session.add(user)
        db.session.commit()

        # Ensure the user has a portfolio with sufficient balance so buys succeed
        from app.models import UserPortfolio

        portfolio = UserPortfolio(
            user_id=user.id, available_balance=100000.0, total_balance=100000.0
        )
        db.session.add(portfolio)
        db.session.commit()

        # Enable system recording and set the configured system user id
        bot_module.TRADING_CONFIG["record_system_trades_to_db"] = True
        bot_module.TRADING_CONFIG["system_trade_user_id"] = user.id

        trader = bot_module.UltimateAIAutoTrader()

        trade = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "price": 20000.0,
            "type": "AUTO",
            "signal": "TEST_SIGNAL",
            "confidence": 0.75,
        }

        # Call the private helper directly
        trader._maybe_record_system_trade(trade)

        db.session.commit()

        recorded = UserTrade.query.filter_by(user_id=user.id).all()
        assert len(recorded) >= 1
        t = recorded[-1]
        assert t.symbol == "BTCUSDT"
        assert t.side == "BUY"
        assert t.entry_price == 20000.0
        assert t.status == "open"
        assert pytest.approx(t.quantity, rel=1e-6) == 0.01

        # Clean up toggles
        bot_module.TRADING_CONFIG["record_system_trades_to_db"] = False
        bot_module.TRADING_CONFIG["system_trade_user_id"] = None
