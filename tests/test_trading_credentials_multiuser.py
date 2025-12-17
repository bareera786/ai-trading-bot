import json
import pytest

pytest.importorskip("flask_mail")

from flask import Flask
from flask_login import LoginManager

from app.routes.trading import trading_bp
from app.services.binance import BinanceCredentialStore


class SimpleUser:
    def __init__(self, user_id: int):
        self.id = user_id
        self.is_authenticated = True
        # Flask-Login expects an is_active attribute/property
        self.is_active = True

    def get_id(self):
        return str(self.id)


def make_app_with_store(store):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "key"

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        return json.dumps({"error": "auth required"}), 401

    @login_manager.user_loader
    def load_user(user_id):
        return SimpleUser(int(user_id))

    app.register_blueprint(trading_bp, url_prefix="")
    return app


def test_credentials_endpoint_scopes_by_user(tmp_path):
    store = BinanceCredentialStore(storage_dir=str(tmp_path))
    app = make_app_with_store(store)

    ctx = {
        "dashboard_data": {},
        "ultimate_trader": None,
        "optimized_trader": None,
        "get_binance_credential_status": lambda include_connection, include_logs, user_id=None: {},
        "apply_binance_credentials": lambda account_type, creds: True,
        "binance_credentials_store": store,
        "binance_log_manager": None,
        "binance_credential_service": type(
            "_",
            (),
            {
                "test_credentials": staticmethod(
                    lambda api_key, api_secret, testnet=True: {"connected": False}
                )
            },
        )(),
    }

    # Use separate test clients to simulate different users to avoid session caching
    # issues when switching user identities within the same client instance.
    with app.test_client() as client1:
        client1.application.extensions = {"ai_bot_context": ctx}
        with client1.session_transaction() as session:
            session["_user_id"] = str(1)
            session["_fresh"] = True
        resp = client1.post(
            "/api/binance/credentials",
            json={"apiKey": "U1KEY", "apiSecret": "U1SEC", "accountType": "spot"},
        )
        assert resp.status_code == 200

    with app.test_client() as client2:
        client2.application.extensions = {"ai_bot_context": ctx}
        with client2.session_transaction() as session:
            session["_user_id"] = str(2)
            session["_fresh"] = True
        resp = client2.post(
            "/api/binance/credentials",
            json={"apiKey": "U2KEY", "apiSecret": "U2SEC", "accountType": "spot"},
        )
        assert resp.status_code == 200
    # Check isolation
    creds1 = store.get_credentials("spot", user_id=1)
    creds2 = store.get_credentials("spot", user_id=2)
    assert creds1["api_key"] == "U1KEY"
    assert creds2["api_key"] == "U2KEY"

    # Test credential validation endpoint (should respond, even if not connected)
    with app.test_client() as client3:
        client3.application.extensions = {"ai_bot_context": ctx}
        with client3.session_transaction() as session:
            session["_user_id"] = str(1)
            session["_fresh"] = True
        resp = client3.post(
            "/api/binance/credentials/test", json={"apiKey": "X", "apiSecret": "Y"}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "connected" in data
