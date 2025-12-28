import json
import os
from flask import Flask

import pytest

pytest.importorskip("flask_mail")

from app.routes.status import status_bp


def test_ribs_status_malformed_file_returns_error(tmp_path, monkeypatch):
    base = tmp_path / "bot_persistence" / "ribs_checkpoints"
    base.mkdir(parents=True)
    status_path = base / "ribs_status.json"
    # Write malformed JSON
    with open(status_path, "w") as f:
        f.write("{ not valid json")

    monkeypatch.chdir(str(tmp_path))

    app = Flask(__name__)
    app.register_blueprint(status_bp)

    with app.test_client() as client:
        resp = client.get("/api/ribs/archive/status")
        assert resp.status_code == 500
        data = resp.get_json()
        assert "Failed to read status file" in data.get("error", "")

        resp2 = client.get("/api/health/ribs")
        # health endpoint should also report error
        assert resp2.status_code == 500
        data2 = resp2.get_json()
        assert data2.get("status") == "error"
        # Depending on implementation, the health endpoint may return the raw
        # JSON decode error message or a wrapped "Failed to read status file".
        err = data2.get("error", "")
        assert err
        assert (
            "Failed to read status file" in err
            or "Expecting property name" in err
            or "Expecting value" in err
        )
