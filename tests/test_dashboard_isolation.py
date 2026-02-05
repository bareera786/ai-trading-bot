import json
import os
import tempfile

import pytest

pytest.importorskip("flask_mail")

from app import create_app
from app.extensions import db
from app.models import User


class _FakeTradeHistory:
    def __init__(self, owner: str, symbol: str):
        self._owner = owner
        self._symbol = symbol

    def get_trade_history(self):
        return [
            {
                "trade_id": f"{self._owner}-t1",
                "symbol": self._symbol,
                "side": "BUY",
                "status": "OPEN",
            }
        ]

    def get_journal_events(self, limit: int = 10):
        return [
            {
                "id": f"{self._owner}-e1",
                "owner": self._owner,
                "message": f"event for {self._owner}",
            }
        ][:limit]


class _FakeTrader:
    def __init__(self, owner: str, symbol: str):
        self.owner = owner
        self.trading_enabled = True
        self.paper_trading = True
        self.real_trading_enabled = False
        self.futures_trading_enabled = False
        self.futures_trader = None
        self.positions = {symbol: {"qty": 1.0}}
        self.trade_history = _FakeTradeHistory(owner, symbol)

    def get_performance_summary(self):
        return {"owner": self.owner, "pnl": 1.0 if self.owner == "u1" else -1.0}

    def get_portfolio_summary(self, prices):
        return {
            "owner": self.owner,
            "symbols": sorted(self.positions.keys()),
            "prices": dict(prices),
        }


class _FakeMarketDataService:
    def __init__(self, ultimate_by_user, optimized_by_user):
        self._ultimate_by_user = ultimate_by_user
        self._optimized_by_user = optimized_by_user

    def _get_or_create_user_traders(self, user_id: int):
        return self._ultimate_by_user[int(user_id)], self._optimized_by_user[int(user_id)]

    def get_real_market_data(self, _symbol: str):
        return {"price": 123.45}


def _make_user(app, username: str, password: str):
    user = User()
    # Assign fields explicitly to match model signature across versions.
    user.username = username
    user.email = f"{username}@test"
    user.is_admin = True
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, username: str, password: str):
    resp = client.post("/login", json={"username": username, "password": password})
    assert resp.status_code == 200


def _logout(client):
    resp = client.get("/logout")
    # Logout redirects to login page.
    assert resp.status_code in (302, 303)


def test_api_dashboard_is_user_scoped_in_multiuser_mode():
    os.environ["AI_BOT_TEST_MODE"] = "true"

    db_fd, db_path = tempfile.mkstemp()
    try:
        app = create_app()
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        )

        with app.app_context():
            db.create_all()
            user1 = _make_user(app, "u1", "pw1")
            user2 = _make_user(app, "u2", "pw2")

            u1_ultimate = _FakeTrader("u1", "BTCUSDT")
            u1_optimized = _FakeTrader("u1", "BTCUSDT")
            u2_ultimate = _FakeTrader("u2", "ETHUSDT")
            u2_optimized = _FakeTrader("u2", "ETHUSDT")

            market = _FakeMarketDataService(
                ultimate_by_user={int(user1.id): u1_ultimate, int(user2.id): u2_ultimate},
                optimized_by_user={int(user1.id): u1_optimized, int(user2.id): u2_optimized},
            )

            # Set a shared dashboard_data payload that would be wrong if returned
            # as-is to all users; /api/dashboard must derive sensitive sections
            # from per-user traders instead.
            app.extensions["ai_bot_context"] = {
                "dashboard_data": {
                    "system_status": {"last_trade": {"symbol": "SHARED"}},
                    "optimized_system_status": {"last_trade": {"symbol": "SHARED"}},
                    "performance": {"owner": "SHARED"},
                    "portfolio": {"owner": "SHARED", "symbols": ["SHARED"]},
                    "journal_events": [{"owner": "SHARED"}],
                },
                "market_data_service": market,
            }

            client = app.test_client()

            _login(client, "u1", "pw1")
            r1 = client.get("/api/dashboard")
            _logout(client)
            _login(client, "u2", "pw2")
            r2 = client.get("/api/dashboard")
            assert r1.status_code == 200
            assert r2.status_code == 200

            j1 = r1.get_json()
            j2 = r2.get_json()

            assert j1.get("user", {}).get("username") == "u1"
            assert j2.get("user", {}).get("username") == "u2"

            assert j1["portfolio"]["owner"] == "u1"
            assert j2["portfolio"]["owner"] == "u2"

            assert j1["portfolio"]["symbols"] == ["BTCUSDT"]
            assert j2["portfolio"]["symbols"] == ["ETHUSDT"]

            assert j1["performance"]["owner"] == "u1"
            assert j2["performance"]["owner"] == "u2"

            assert j1["system_status"].get("last_trade", {}).get("symbol") == "BTCUSDT"
            assert j2["system_status"].get("last_trade", {}).get("symbol") == "ETHUSDT"

            assert j1["journal_events"][0]["owner"] == "u1"
            assert j2["journal_events"][0]["owner"] == "u2"

            # No cross-user symbols should appear in the other user's response.
            raw1 = json.dumps(j1)
            raw2 = json.dumps(j2)
            assert "ETHUSDT" not in raw1
            assert "BTCUSDT" not in raw2

    finally:
        os.close(db_fd)
        os.unlink(db_path)


def test_realtime_endpoints_do_not_leak_shared_dashboard_state():
    os.environ["AI_BOT_TEST_MODE"] = "true"

    db_fd, db_path = tempfile.mkstemp()
    try:
        app = create_app()
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI=f"sqlite:///{db_path}",
        )

        def _get_user_portfolio(user_id):
            uid = int(user_id)
            if uid == 1:
                return {
                    "owner": "u1",
                    "total_balance": 100.0,
                    "available_balance": 50.0,
                    "total_pnl": 1.0,
                    "daily_pnl": 0.5,
                    "open_positions": {"BTCUSDT": {"pnl": 0.25}},
                }
            if uid == 2:
                return {
                    "owner": "u2",
                    "total_balance": 200.0,
                    "available_balance": 150.0,
                    "total_pnl": -2.0,
                    "daily_pnl": -0.75,
                    "open_positions": {"ETHUSDT": {"pnl": -0.1}},
                }
            return {}

        with app.app_context():
            db.create_all()
            _make_user(app, "u1", "pw1")
            _make_user(app, "u2", "pw2")

            app.extensions["ai_bot_context"] = {
                "dashboard_data": {
                    "portfolio": {"owner": "SHARED"},
                    "performance": {"owner": "SHARED"},
                },
                "get_user_portfolio_data": _get_user_portfolio,
            }

            client = app.test_client()

            _login(client, "u1", "pw1")
            p1 = client.get("/api/realtime/portfolio").get_json()
            pnl1 = client.get("/api/realtime/pnl").get_json()
            perf1 = client.get("/api/realtime/performance").get_json()
            _logout(client)

            _login(client, "u2", "pw2")
            p2 = client.get("/api/realtime/portfolio").get_json()
            pnl2 = client.get("/api/realtime/pnl").get_json()
            perf2 = client.get("/api/realtime/performance").get_json()

            assert p1["data"]["owner"] == "u1"
            assert p2["data"]["owner"] == "u2"
            assert pnl1["data"]["total_pnl"] == 1.0
            assert pnl2["data"]["total_pnl"] == -2.0
            assert perf1["data"]["total_balance"] == 100.0
            assert perf2["data"]["total_balance"] == 200.0

            raw1 = json.dumps({"portfolio": p1, "pnl": pnl1, "performance": perf1})
            raw2 = json.dumps({"portfolio": p2, "pnl": pnl2, "performance": perf2})
            assert "SHARED" not in raw1
            assert "SHARED" not in raw2

    finally:
        os.close(db_fd)
        os.unlink(db_path)
