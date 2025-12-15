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
