import types
from flask import Flask

from app.routes.status import status_bp
from app.tasks import manager as task_manager


def _make_test_client():
    app = Flask(__name__)
    app.register_blueprint(status_bp)
    # Provide minimal ai_bot_context to satisfy _ctx()
    app.extensions["ai_bot_context"] = {"version_label": "test"}
    return app.test_client()


def test_health_uninitialized():
    # Ensure global manager is None
    task_manager._background_task_manager = None

    client = _make_test_client()

    res = client.get("/health")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["checks"]["background_worker"]["status"] == "uninitialized"


def test_health_worker_running(monkeypatch):
    # Create a fake manager and worker
    fake_worker = types.SimpleNamespace()
    fake_worker.is_running = lambda: True

    class FakeManager:
        self_improvement_worker = fake_worker

    monkeypatch.setattr(task_manager, "_background_task_manager", FakeManager())

    client = _make_test_client()
    res = client.get("/health")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["checks"]["background_worker"]["status"] == "ok"


def test_health_worker_stopped(monkeypatch):
    fake_worker = types.SimpleNamespace()
    fake_worker.is_running = lambda: False

    class FakeManager:
        self_improvement_worker = fake_worker

    monkeypatch.setattr(task_manager, "_background_task_manager", FakeManager())

    client = _make_test_client()
    res = client.get("/health")
    assert res.status_code == 200
    payload = res.get_json()
    assert payload["checks"]["background_worker"]["status"] == "stopped"
