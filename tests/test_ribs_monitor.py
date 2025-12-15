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
