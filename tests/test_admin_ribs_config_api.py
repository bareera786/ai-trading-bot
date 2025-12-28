import json
from flask import Flask
from flask_login import LoginManager, login_user

from app.routes.admin_dashboard import admin_dashboard_bp
from app.services import ribs_admin
import pytest


class AdminUser:
    def __init__(self):
        self.id = 1
        self.is_authenticated = True
        self.is_active = True
        self.is_admin = True

    def get_id(self):
        return str(self.id)


class NonAdminUser(AdminUser):
    def __init__(self):
        super().__init__()
        self.is_admin = False


def make_app(user_cls=AdminUser):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "key"
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return user_cls()

    app.register_blueprint(admin_dashboard_bp)
    return app


def test_admin_get_forbidden_for_non_admin(monkeypatch):
    app = make_app(user_cls=NonAdminUser)

    client = app.test_client()
    with client:
        # mark session as logged in as non-admin
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
        # monkeypatch loader to return a non-admin user
        from flask_login import login_manager

        # call endpoint
        resp = client.get("/admin/api/ribs/config")
        assert resp.status_code == 403


def test_admin_put_and_get_persist(monkeypatch, tmp_path):
    app = make_app()

    # redirect overrides file to tmp path
    tmp_file = tmp_path / "ribs_overrides.json"
    monkeypatch.setattr(ribs_admin, "OVERRIDES_PATH", str(tmp_file))

    client = app.test_client()
    with client:
        # mark session as logged in as admin
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"

        # initial GET should succeed
        resp = client.get("/admin/api/ribs/config")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "effective" in data

        # PUT new overrides
        payload = {
            "ribs_deploy_min_return": 5.5,
            "ribs_deploy_min_sharpe": 0.8,
            "ribs_deploy_max_drawdown": 10.0,
            "ribs_deploy_min_win_rate": 0.3,
            "ribs_deploy_backtest_hours": 72,
        }
        resp = client.put("/admin/api/ribs/config", json=payload)
        assert resp.status_code == 200
        j = resp.get_json()
        assert j.get("success") is True

        # Confirm file was written
        saved = json.loads(tmp_file.read_text())
        assert saved["ribs_deploy_min_return"] == 5.5

        # GET should reflect overrides
        resp = client.get("/admin/api/ribs/config")
        assert resp.status_code == 200
        d2 = resp.get_json()
        assert d2.get("overrides", {}).get("ribs_deploy_min_return") == 5.5
