from flask import Flask
import threading
import time

import pytest

from flask_login import LoginManager

pytest.importorskip("flask_mail")

from app.routes.status import status_bp


class SimpleUser:
    def __init__(self, user_id: int):
        self.id = user_id
        self.is_authenticated = True
        self.is_active = True

    def get_id(self):
        return str(self.id)


class DummyWorker:
    def __init__(self):
        self.ribs_enabled = True
        self.started = False
        self._stop_event = threading.Event()

    def continuous_ribs_optimization(self):
        # quick mark to indicate start
        self.started = True

    def start_ribs_optimization(self):
        if self.started:
            return False
        self.started = True
        return True

    def stop_ribs_optimization(self):
        if not self.started:
            return False
        self.started = False
        return True


class DummyRuntime:
    def __init__(self):
        self.self_improvement_worker = DummyWorker()


def test_ribs_status_and_control_endpoints(monkeypatch):
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "key"

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return SimpleUser(int(user_id))

    app.register_blueprint(status_bp)

    # simulate ai_bot_context
    runtime = DummyRuntime()
    app.extensions["ai_bot_context"] = {
        "service_runtime": runtime,
        "dashboard_data": {},
    }

    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["_user_id"] = "1"
            sess["_fresh"] = True
        # status
        resp = client.get("/api/ribs/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "enabled" in data

        # start
        resp2 = client.post("/api/ribs/start")
        assert resp2.status_code == 200
        assert resp2.get_json().get("success") is True

        # pause
        resp3 = client.post("/api/ribs/pause")
        assert resp3.status_code == 200
        assert resp3.get_json().get("success") is True
