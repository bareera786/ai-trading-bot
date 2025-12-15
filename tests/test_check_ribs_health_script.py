import json
import os
import tempfile
import time

import pytest

pytest.importorskip("flask_mail")

from scripts.check_ribs_health import main as check_main


def test_check_ribs_health_triggers_webhook(monkeypatch, tmp_path):
    base = tmp_path / "bot_persistence" / "ribs_checkpoints"
    base.mkdir(parents=True)
    status_path = base / "ribs_status.json"
    payload = {"latest_checkpoint": {"path": "x", "mtime": time.time() - 99999}}
    with open(status_path, "w") as f:
        json.dump(payload, f)

    monkeypatch.chdir(str(tmp_path))

    calls = {}

    def fake_post(url, json=None, timeout=5):
        calls["called"] = True
        calls["payload"] = json

        class R:
            status_code = 200

        return R()

    monkeypatch.setenv("RIBS_ALERT_WEBHOOK", "http://example.com/webhook")
    monkeypatch.setattr("scripts.check_ribs_health.requests.post", fake_post)

    rc = check_main(1)
    assert rc == 3
    assert calls.get("called") is True
