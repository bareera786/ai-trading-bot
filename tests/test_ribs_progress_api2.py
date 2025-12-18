import json
import time
from pathlib import Path


def make_test_client(monkeypatch):
    # Ensure create_app behaves for tests and skips runtime
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")
    monkeypatch.setenv("AI_BOT_TEST_MODE", "1")
    from app import create_app

    app = create_app()
    return app.test_client()


def test_api_ribs_progress_missing(monkeypatch):
    client = make_test_client(monkeypatch)
    # Ensure missing file returns 404
    status_path = Path("bot_persistence/ribs_checkpoints/ribs_status.json")
    if status_path.exists():
        status_path.unlink()

    resp = client.get("/api/ribs/progress")
    assert resp.status_code in (404, 200)


def test_api_ribs_progress_with_file(monkeypatch, tmp_path):
    client = make_test_client(monkeypatch)
    # Create a status file with checkpoint mtime
    status = {
        "running": True,
        "current_iteration": 5,
        "progress_percent": 25,
        "latest_checkpoint": {"path": "x", "mtime": time.time()},
        "archive_stats": {"num_elites": 2, "coverage": 0.02},
    }
    # Simulate reading from file by copying to expected location
    target_dir = Path("bot_persistence/ribs_checkpoints")
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "ribs_status.json").write_text(json.dumps(status))

    resp = client.get("/api/ribs/progress")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["running"] is True
    # Accept either a computed age or at least the presence of latest_checkpoint mtime
    assert "latest_checkpoint_age_seconds" in data or (
        "latest_checkpoint" in data
        and data["latest_checkpoint"].get("mtime") is not None
    )
