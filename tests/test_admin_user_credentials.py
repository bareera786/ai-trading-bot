import json
from flask import Flask
from flask_login import LoginManager, login_user
import pytest

pytest.importorskip("flask_mail")

from app.routes.admin_user_api import admin_user_api_bp
from app.services.binance import BinanceCredentialStore


class AdminUser:
    def __init__(self):
        self.id = 1
        self.is_authenticated = True
        self.is_admin = True
        # Required by flask-login when calling login_user()
        self.is_active = True

    def get_id(self):
        return str(self.id)


def make_app(store):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "key"
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return AdminUser()

    app.register_blueprint(admin_user_api_bp)
    return app


def test_admin_credentials_crud(tmp_path):
    store = BinanceCredentialStore(storage_dir=str(tmp_path))
    app = make_app(store)
    ctx = {
        "binance_credentials_store": store,
        "binance_credential_service": None,
    }

    with app.test_client() as client:
        with app.app_context():
            app.extensions = {"ai_bot_context": ctx}
            # login admin (set session directly to avoid request-context issues)
            with client.session_transaction() as sess:
                sess["_user_id"] = "1"

            # set credentials for user 2
            resp = client.post(
                "/api/users/2/credentials",
                json={"apiKey": "A", "apiSecret": "B", "accountType": "spot"},
            )
            assert resp.status_code == 200

            # get credentials
            resp = client.get("/api/users/2/credentials")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data.get("credentials")

            # delete credentials
            resp = client.delete("/api/users/2/credentials")
            assert resp.status_code == 200
