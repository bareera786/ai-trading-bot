import json
import os
from flask import Flask
import pytest

pytest.importorskip("flask_mail")

from app.routes.status import status_bp


def test_ribs_archive_status_fallback(tmp_path, monkeypatch):
    # Create a dummy status file in bot_persistence/ribs_checkpoints
    base = tmp_path / "bot_persistence" / "ribs_checkpoints"
    base.mkdir(parents=True)
    status_path = base / "ribs_status.json"
    payload = {
        "running": False,
        "latest_checkpoint": {"path": "dummy", "mtime": 12345, "size": 42},
    }
    with open(status_path, "w") as f:
        json.dump(payload, f)

    # Monkeypatch os.path.exists to point to our tmp status file by adjusting cwd
    monkeypatch.chdir(str(tmp_path))

    app = Flask(__name__)
    app.register_blueprint(status_bp)

    with app.test_client() as client:
        resp = client.get("/api/ribs/archive/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("available") is True
        assert "status_file" in data or "status_file" in data
