from __future__ import annotations

import pytest
from flask import Flask, jsonify

from app.auth.decorators import user_required


class MockUser:
    def __init__(self, user_id: int, *, is_admin: bool):
        self.id = user_id
        self.is_authenticated = True
        self.is_active = True
        self.is_admin = is_admin

    def get_id(self):
        return str(self.id)


@pytest.fixture()
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
        # By default non-admin. Tests control admin flag via session.
        from flask import session as flask_session

        return MockUser(int(user_id), is_admin=bool(flask_session.get("is_admin", False)))

    @app.route("/user-only")
    @user_required
    def user_only():
        return jsonify({"ok": True})

    return app


@pytest.fixture()
def client(app):
    return app.test_client()


def _login_as(client, user_id: int, *, is_admin: bool):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True
        sess["is_admin"] = bool(is_admin)


def test_user_required_allows_admin_superuser(client):
    _login_as(client, 1, is_admin=True)
    resp = client.get("/user-only")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}


def test_user_required_allows_normal_user(client):
    _login_as(client, 2, is_admin=False)
    resp = client.get("/user-only")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
