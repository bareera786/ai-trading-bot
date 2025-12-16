import json
from flask import Flask
from app import create_app
from app.extensions import db
from app.models import User, UserTrade
from app.routes.metrics import metrics_bp
from datetime import datetime


def test_api_trades_merge_db():
    app = create_app()
    app.testing = True

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create admin user and a DB trade
        admin = User(username="admin", email="admin@example.com", is_admin=True)
        admin.set_password("pass")
        db.session.add(admin)
        db.session.commit()

        ut = UserTrade(
            user_id=admin.id,
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.02,
            entry_price=21000.0,
            trade_type="AUTO",
            status="closed",
            signal_source="TEST",
            confidence_score=0.9,
            timestamp=datetime.utcnow(),
        )
        db.session.add(ut)
        db.session.commit()

        # Mock trader with a simple trade history
        class MockTH:
            def get_trade_history(self, filters=None):
                return [
                    {
                        "symbol": "BTCUSDT",
                        "side": "BUY",
                        "price": 20000.0,
                        "quantity": 0.01,
                        "type": "AUTO",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ]

        class MockTrader:
            def __init__(self):
                self.trade_history = MockTH()

        app.extensions["ai_bot_context"] = {"ultimate_trader": MockTrader()}

        client = app.test_client()
        # log in as admin via session
        with client.session_transaction() as sess:
            sess["_user_id"] = str(admin.id)
            sess["_fresh"] = True
            sess["user_id"] = admin.id

        resp = client.get("/api/trades?merge_db=1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "trades" in data
        # ensure at least one DB-origin trade is present when merged
        assert any(t.get("source") == "db" or t.get("db_id") for t in data["trades"])


def test_api_trades_merge_db_with_json_login():
    """Ensure JSON login flow sets up an authenticated session usable by the merged view."""
    app = create_app()
    app.testing = True

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create admin user and a DB trade
        admin = User(username="admin", email="admin@example.com", is_admin=True)
        admin.set_password("pass")
        db.session.add(admin)
        db.session.commit()

        ut = UserTrade(
            user_id=admin.id,
            symbol="BTCUSDT",
            side="SELL",
            quantity=0.02,
            entry_price=21000.0,
            trade_type="AUTO",
            status="closed",
            signal_source="TEST",
            confidence_score=0.9,
            timestamp=datetime.utcnow(),
        )
        db.session.add(ut)
        db.session.commit()

        # Mock trader with a simple trade history
        class MockTH:
            def get_trade_history(self, filters=None):
                return [
                    {
                        "symbol": "BTCUSDT",
                        "side": "BUY",
                        "price": 20000.0,
                        "quantity": 0.01,
                        "type": "AUTO",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ]

        class MockTrader:
            def __init__(self):
                self.trade_history = MockTH()

        app.extensions["ai_bot_context"] = {"ultimate_trader": MockTrader()}

        client = app.test_client()

        # login via JSON POST
        resp = client.post("/login", json={"username": "admin", "password": "pass"})
        assert resp.status_code == 200

        # now request merged view
        resp = client.get("/api/trades?merge_db=1")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert any(t.get("source") == "db" or t.get("db_id") for t in data["trades"])


def test_api_trades_merge_db_debug_header():
    """Ensure the debug header returns evaluated auth_state in response for merged view."""
    app = create_app()
    app.testing = True

    with app.app_context():
        db.drop_all()
        db.create_all()

        # Create admin user
        admin = User(username="admin", email="admin@example.com", is_admin=True)
        admin.set_password("pass")
        db.session.add(admin)
        db.session.commit()

        # Mock trader
        class MockTH:
            def get_trade_history(self, filters=None):
                return []

        class MockTrader:
            def __init__(self):
                self.trade_history = MockTH()

        app.extensions["ai_bot_context"] = {"ultimate_trader": MockTrader()}

        client = app.test_client()
        # login via JSON POST
        resp = client.post("/login", json={"username": "admin", "password": "pass"})
        assert resp.status_code == 200

        # request merged view with debug header
        resp = client.get("/api/trades?merge_db=1", headers={"X-Debug-Merged": "1"})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "debug" in data
        assert data["debug"].get("current_user_authenticated") is True
        assert data["debug"].get("current_user_id") == admin.id
