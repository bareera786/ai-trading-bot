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
    }

    with app.test_client() as client:
        with app.app_context():
            app.extensions = {"ai_bot_context": ctx}

            # Post credentials as user 1
            from flask_login import login_user

            login_user(SimpleUser(1))
            resp = client.post(
                "/api/binance/credentials",
                json={"apiKey": "U1KEY", "apiSecret": "U1SEC", "accountType": "spot"},
            )
            assert resp.status_code == 200

            # Post credentials as user 2
            login_user(SimpleUser(2))
            resp = client.post(
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
            resp = client.post(
                "/api/binance/credentials/test", json={"apiKey": "X", "apiSecret": "Y"}
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert "connected" in data
