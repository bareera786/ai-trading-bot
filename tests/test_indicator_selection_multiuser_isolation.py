import json

import pytest

pytest.importorskip("flask_mail")

from flask import Flask
from flask_login import LoginManager

from app.routes.dashboard import dashboard_bp
from app.runtime.context import UserScopedProxy
from app.runtime.indicators import IndicatorSelectionManager


class SimpleUser:
    def __init__(self, user_id: int):
        self.id = user_id
        self.is_authenticated = True
        self.is_active = True

    def get_id(self):
        return str(self.id)


def make_app_with_ctx(ctx):
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

    app.register_blueprint(dashboard_bp, url_prefix="")
    app.extensions = {"ai_bot_context": ctx}
    return app


def test_indicator_selection_isolated_and_dashboard_not_mutated():
    dashboard_data = {"indicator_selections": {"SENTINEL": ["GLOBAL"]}}

    base_manager = IndicatorSelectionManager()
    proxy = UserScopedProxy(base=base_manager, factory=IndicatorSelectionManager)

    def get_indicator_selection(profile):
        return proxy.get_selection(profile)

    def set_indicator_selection(profile, selections):
        return proxy.set_selection(profile, selections)

    def get_all_indicator_selections():
        return proxy.snapshot()

    ctx = {
        "dashboard_data": dashboard_data,
        "indicator_signal_options": ["CRT", "ICT", "SMC"],
        "indicator_profiles": ["ultimate", "optimized", "futures"],
        "get_indicator_selection": get_indicator_selection,
        "set_indicator_selection": set_indicator_selection,
        "get_all_indicator_selections": get_all_indicator_selections,
        # If routes incorrectly call this for authenticated users, it would mutate
        # the shared dashboard_data and cause cross-user leakage.
        "refresh_indicator_dashboard_state": lambda: dashboard_data.__setitem__(
            "indicator_selections", {"MUTATED": ["TRUE"]}
        ),
    }

    app = make_app_with_ctx(ctx)

    with app.test_client() as client1:
        with client1.session_transaction() as session:
            session["_user_id"] = str(1)
            session["_fresh"] = True
        resp = client1.post(
            "/api/indicator_selection",
            json={"profile": "ultimate", "selections": ["CRT"]},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["indicator_selections"].get("ultimate") == ["CRT"]

        resp = client1.get("/api/dashboard")
        assert resp.status_code == 200
        dashboard_payload = resp.get_json()
        assert dashboard_payload["indicator_selections"].get("ultimate") == ["CRT"]
        assert dashboard_payload["indicator_selections"] != {"SENTINEL": ["GLOBAL"]}

    with app.test_client() as client2:
        with client2.session_transaction() as session:
            session["_user_id"] = str(2)
            session["_fresh"] = True
        resp = client2.get("/api/indicator_selection?profile=ultimate")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["selections"] != ["CRT"], "user2 must not see user1 selection"

        resp = client2.get("/api/dashboard")
        assert resp.status_code == 200
        dashboard_payload = resp.get_json()
        assert dashboard_payload["indicator_selections"].get("ultimate") != ["CRT"]
        assert dashboard_payload["indicator_selections"] != {"SENTINEL": ["GLOBAL"]}

    # Authenticated flows must not mutate the shared dashboard_data cache.
    assert dashboard_data["indicator_selections"] == {"SENTINEL": ["GLOBAL"]}
