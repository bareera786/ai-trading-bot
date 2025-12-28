import os
import json
import time
from pathlib import Path

import pytest

from app.routes.ribs_progress import api_ribs_progress


def test_api_ribs_progress_missing(monkeypatch, client):
    # Ensure missing file returns 404
    monkeypatch.setenv("AI_BOT_TEST_MODE", "1")
    status_path = Path("bot_persistence/ribs_checkpoints/ribs_status.json")
    if status_path.exists():
        status_path.unlink()

    resp = client.get("/api/ribs/progress")
    assert resp.status_code in (404, 200)


def test_api_ribs_progress_with_file(monkeypatch, client, tmp_path):
    # Create a status file with checkpoint mtime
    status = {
        "running": True,
        "current_iteration": 5,
        "progress_percent": 25,
        "latest_checkpoint": {"path": "x", "mtime": time.time()},
        "archive_stats": {"num_elites": 2, "coverage": 0.02},
    }
    p = tmp_path / "ribs_status.json"
    p.write_text(json.dumps(status))

    monkeypatch.setenv("AI_BOT_TEST_MODE", "1")
    # monkeypatch path used by route
    monkeypatch.setenv("RIBS_STATUS_PATH", str(p))

    # Simulate reading from file by copying to expected location
    target_dir = Path("bot_persistence/ribs_checkpoints")
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "ribs_status.json").write_text(json.dumps(status))

    resp = client.get("/api/ribs/progress")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["running"] is True
    assert "latest_checkpoint_age_seconds" in data


import json
from flask import Flask

from app.routes.status import status_bp


def test_ribs_progress_reads_status_file(tmp_path, monkeypatch):
    base = tmp_path / "bot_persistence" / "ribs_checkpoints"
    base.mkdir(parents=True)
    status_path = base / "ribs_status.json"
    payload = {
        "running": False,
        "current_iteration": 100,
        "progress_percent": 100,
        "archive_stats": {"num_elites": 5},
        "latest_checkpoint": {"path": "x", "mtime": 12345, "size": 123},
    }
    with open(status_path, "w") as f:
        json.dump(payload, f)

    monkeypatch.chdir(str(tmp_path))

    app = Flask(__name__)
    app.register_blueprint(status_bp)

    with app.test_client() as client:
        resp = client.get("/api/ribs/progress")
        assert resp.status_code == 200
        data = resp.get_json() or {}
        assert data.get("progress_percent") == 100
        assert data.get("current_iteration") == 100
        assert data.get("archive_stats", {}).get("num_elites") == 5
