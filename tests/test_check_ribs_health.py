import json
import os
import time
from pathlib import Path

import pytest


from scripts.check_ribs_health import check_status, send_alert


def test_check_status_missing(tmp_path):
    path = tmp_path / "nope.json"
    ok, msg = check_status(str(path), max_age_seconds=10)
    assert not ok
    assert "missing" in msg.lower()


def test_check_status_stale_and_checkpoint(tmp_path):
    status = {"running": True, "latest_checkpoint": {"mtime": time.time() - 3600}}
    fp = tmp_path / "ribs_status.json"
    fp.write_text(json.dumps(status))
    # make file mtime in the past beyond threshold
    old = time.time() - 3600
    os.utime(fp, (old, old))

    ok, msg = check_status(str(fp), max_age_seconds=10)
    assert not ok
    assert "stale" in msg.lower()


def test_check_status_ok(tmp_path):
    status = {"running": True, "latest_checkpoint": {"mtime": time.time()}}
    fp = tmp_path / "ribs_status.json"
    fp.write_text(json.dumps(status))
    ok, msg = check_status(str(fp), max_age_seconds=60)
    assert ok
    assert msg == "OK"


def test_send_alert_posts(monkeypatch):
    called = {}

    class Dummy:
        def __init__(self):
            self.status_code = 200

        def raise_for_status(self):
            return None

    def fake_post(url, json=None, timeout=None):
        called["url"] = url
        called["json"] = json
        called["timeout"] = timeout
        return Dummy()

    monkeypatch.setattr(
        "scripts.check_ribs_health.requests.post", fake_post, raising=False
    )

    send_alert("http://example.com/webhook", {"a": 1})
    assert called["url"] == "http://example.com/webhook"
    assert called["json"] == {"a": 1}
