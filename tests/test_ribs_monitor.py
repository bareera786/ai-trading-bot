import json
import os
import time
import pytest

pytest.importorskip("ribs")

from app.services.ribs_optimizer import TradingRIBSOptimizer


def test_check_checkpoint_freshness(tmp_path, monkeypatch):
    # Initialize optimizer but override checkpoints_dir to tmp_path
    opt = TradingRIBSOptimizer()
    opt.checkpoints_dir = str(tmp_path)

    # No status file -> missing
    res = opt.check_checkpoint_freshness(max_age_seconds=3600)
    assert res["status"] in ("missing", "no_checkpoint")

    # Create a fake status file with latest checkpoint
    ckpt = os.path.join(str(tmp_path), "ribs_checkpoint_test.pkl")
    with open(ckpt, "wb") as f:
        f.write(b"dummy")

    status = {
        "running": False,
        "latest_checkpoint": {
            "path": ckpt,
            "mtime": os.path.getmtime(ckpt),
            "size": os.path.getsize(ckpt),
        },
    }
    status_path = os.path.join(str(tmp_path), "ribs_status.json")
    with open(status_path, "w") as sf:
        json.dump(status, sf)

    res2 = opt.check_checkpoint_freshness(max_age_seconds=3600)
    assert res2["status"] == "ok"


def test_check_checkpoint_stale_and_alert(tmp_path, monkeypatch):
    opt = TradingRIBSOptimizer()
    opt.checkpoints_dir = str(tmp_path)

    # Create a fake checkpoint with old mtime
    ckpt = os.path.join(str(tmp_path), "ribs_checkpoint_old.pkl")
    with open(ckpt, "wb") as f:
        f.write(b"dummy")
    old_mtime = 1  # far in the past
    os.utime(ckpt, (old_mtime, old_mtime))

    status = {
        "running": False,
        "latest_checkpoint": {
            "path": ckpt,
            "mtime": old_mtime,
            "size": os.path.getsize(ckpt),
        },
    }
    status_path = os.path.join(str(tmp_path), "ribs_status.json")
    with open(status_path, "w") as sf:
        json.dump(status, sf)

    res = opt.check_checkpoint_freshness(max_age_seconds=3600)
    assert res["status"] == "stale"

    # Test alert posting via SelfImprovementWorker._send_ribs_alert
    from app.tasks.self_improvement import SelfImprovementWorker

    worker = SelfImprovementWorker(
        ultimate_trader=None,
        optimized_trader=None,
        ultimate_ml_system=None,
        optimized_ml_system=None,
        dashboard_data={},
        trading_config={},
        logger=None,
    )
    monkeypatch.setenv("RIBS_ALERT_WEBHOOK", "https://example.invalid/webhook")
    called = {}

    def fake_post(url, json=None, timeout=None):
        called["url"] = url
        called["json"] = json
        return type("R", (), {"status_code": 200})

    monkeypatch.setattr("requests.post", fake_post)
    worker._send_ribs_alert("test message")
    assert called.get("url") == "https://example.invalid/webhook"
