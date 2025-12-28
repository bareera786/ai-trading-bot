from flask import Flask
import pytest

pytest.importorskip("flask_mail")

from app.routes.status import status_bp


class DummyOptimizer:
    def __init__(self):
        self.checkpoints_dir = "bot_persistence/ribs_checkpoints"

    def get_archive_stats(self):
        return {"num_elites": 5, "coverage": 0.5, "qd_score": 123.0}


class DummyWorker:
    def __init__(self):
        self.ribs_enabled = True
        self.ribs_optimizer = DummyOptimizer()


def test_ribs_archive_status_live(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(status_bp)

    runtime = type("R", (), {"self_improvement_worker": DummyWorker()})
    app.extensions["ai_bot_context"] = {
        "service_runtime": runtime,
        "dashboard_data": {},
    }

    with app.test_client() as client:
        resp = client.get("/api/ribs/archive/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("available") is True
        assert "archive_stats" in data
