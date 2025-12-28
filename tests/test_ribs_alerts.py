import os

import pytest

pytest.importorskip("flask_mail")

from app.tasks.self_improvement import SelfImprovementWorker


def test_send_ribs_alert_posts_webhook(monkeypatch, tmp_path):
    called = {}

    def fake_post(url, json=None, timeout=None):
        called["url"] = url
        called["json"] = json
        called["timeout"] = timeout
        return type("R", (), {"status_code": 200})

    monkeypatch.setenv("RIBS_ALERT_WEBHOOK", "https://example.invalid/webhook")
    monkeypatch.setattr("requests.post", fake_post)

    worker = SelfImprovementWorker(
        ultimate_trader=None,
        optimized_trader=None,
        ultimate_ml_system=None,
        optimized_ml_system=None,
        dashboard_data={},
        trading_config={},
        logger=None,
        project_root=tmp_path,
    )

    # Should not raise and should call the webhook
    worker._send_ribs_alert("test message")

    assert called.get("url") == "https://example.invalid/webhook"
    assert called.get("json") == {"text": "test message"}
