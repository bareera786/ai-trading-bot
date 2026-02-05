from __future__ import annotations

import pytest
from flask import Flask, jsonify
from flask import session as flask_session

from app.routes.system_ops import system_ops_bp


class MockUser:
    def __init__(self, user_id: int, *, is_admin: bool):
        self.id = user_id
        self.is_authenticated = True
        self.is_active = True
        self.is_admin = is_admin

    def get_id(self):
        return str(self.id)


class StubMLSystem:
    def get_training_logs(self):
        return ["ok"]


class StubTrader:
    def __init__(self):
        self.positions = {}


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"

    from flask_login import LoginManager

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Authentication required"}), 401

    @login_manager.user_loader
    def load_user(user_id: str):
        # Tests control admin vs non-admin via session.
        return MockUser(int(user_id), is_admin=bool(flask_session.get("is_admin", False)))

    app.register_blueprint(system_ops_bp, url_prefix="")

    with app.app_context():
        app.extensions["ai_bot_context"] = {
            "dashboard_data": {
                "performance_chart": {"labels": ["t"], "values": [1]},
                "system_status": {},
                "optimized_system_status": {},
            },
            "top_symbols": ["BTCUSDT", "ETHUSDT"],
            "disabled_symbols": [],
            "ultimate_trader": StubTrader(),
            "optimized_trader": StubTrader(),
            "ultimate_ml_system": StubMLSystem(),
            "optimized_ml_system": StubMLSystem(),
        }

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def _login_as(client, user_id: int, *, is_admin: bool):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["is_admin"] = bool(is_admin)


def test_performance_chart_requires_login(client, app):
    resp = client.get("/api/performance_chart")
    assert resp.status_code == 401


def test_performance_chart_allows_authenticated_user(client):
    _login_as(client, 1, is_admin=False)
    resp = client.get("/api/performance_chart")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "chart_data" in data


def test_symbols_list_allows_authenticated_user(client):
    _login_as(client, 1, is_admin=False)
    resp = client.get("/api/symbols?page=1&page_size=10")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data.get("symbols"), list)


def test_system_ops_are_admin_only_for_non_admin(client):
    _login_as(client, 1, is_admin=False)
    resp = client.post("/api/toggle_trading")
    assert resp.status_code == 403

    resp = client.get("/api/training_logs")
    assert resp.status_code == 403


def test_training_logs_allow_admin(client, monkeypatch):
    _login_as(client, 2, is_admin=True)
    resp = client.get("/api/training_logs?mode=ultimate")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["mode"] == "ultimate"
    assert data["logs"] == ["ok"]
