"""Integration tests for trading endpoints that exercise DB recording."""
from __future__ import annotations

import os
import json

import pytest

from app import create_app
from app.extensions import db
from app.models import User, UserTrade
from app.services.trading import record_user_trade


class MockUserTrader:
    def __init__(self, success: bool = True):
        self.success = success

    def execute_manual_trade(self, symbol, side, quantity, price=None):
        if self.success:
            return {"success": True, "price": price or 50000.0, "order": {"symbol": symbol, "side": side, "quantity": quantity}}
        return {"success": False, "error": "Trade execution failed"}

    def execute_manual_futures_trade(self, symbol, side, quantity, leverage=1, price=None):
        if self.success:
            return {"success": True, "price": price or 50000.0, "order": {"symbol": symbol, "side": side, "quantity": quantity, "leverage": leverage}}
        return {"success": False, "error": "Futures trade execution failed"}


import pytest


@pytest.mark.integration
def test_spot_trade_records_db(monkeypatch):
    # Ensure test-mode so create_app uses an in-memory DB
    monkeypatch.setenv("AI_BOT_TEST_MODE", "1")
    app = create_app()

    with app.app_context():
        db.create_all()

        # Create a test user
        user = User(username="int_test_user", email="int@example.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        # Install a minimal bot context that provides a user trader and
        # the real record_user_trade function so DB writes occur.
        app.extensions["ai_bot_context"] = {
            "dashboard_data": {"system_status": {}, "optimized_system_status": {}},
            "get_user_trader": lambda uid, profile: MockUserTrader(success=True),
            "record_user_trade": record_user_trade,
        }

        client = app.test_client()
        # Log in by setting session directly so Flask-Login finds our user
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True

        payload = {"symbol": "BTC", "side": "BUY", "quantity": 0.001, "price": 50000.0}
        resp = client.post("/api/spot/trade", json=payload)
        assert resp.status_code == 200

        trades = UserTrade.query.filter_by(user_id=user.id).all()
        assert len(trades) == 1
        assert trades[0].symbol == "BTCUSDT"


@pytest.mark.integration
def test_futures_trade_records_db(monkeypatch):
    monkeypatch.setenv("AI_BOT_TEST_MODE", "1")
    app = create_app()

    with app.app_context():
        db.create_all()

        user = User(username="int_futures", email="intf@example.com")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()

        app.extensions["ai_bot_context"] = {
            "dashboard_data": {"system_status": {}, "optimized_system_status": {}},
            "get_user_trader": lambda uid, profile: MockUserTrader(success=True),
            "record_user_trade": record_user_trade,
        }

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)
            sess["_fresh"] = True

        payload = {"symbol": "BTC", "side": "SELL", "quantity": 0.002, "leverage": 5, "price": 50000.0}
        resp = client.post("/api/futures/trade", json=payload)
        assert resp.status_code == 200

        trades = UserTrade.query.filter_by(user_id=user.id).all()
        assert len(trades) == 1
        assert trades[0].trade_type == "manual_futures"
