import importlib
import os

import pytest

pytest.importorskip("flask_mail")


def test_ribs_stress_runner_checkpoints_dir_fallback(monkeypatch, tmp_path):
    calls = {}

    class FakeOpt:
        def __init__(self, *args, **kwargs):
            calls["init"] = True

        def run_optimization_cycle(self, market_data, iterations=0):
            calls["ran"] = iterations
            return []

    mod = importlib.import_module("scripts.ribs_stress_runner")
    monkeypatch.setattr(mod, "TradingRIBSOptimizer", FakeOpt)

    # Capture the status_path the runner will pass to watch_progress
    captured = {}

    def fake_watch_progress(status_path, total):
        captured["path"] = status_path
        return None

    monkeypatch.setattr(mod, "watch_progress", fake_watch_progress)

    mod.main(iterations=3)

    assert calls.get("init") is True
    assert calls.get("ran") == 3
    assert captured.get("path") == os.path.join(
        "bot_persistence", "ribs_checkpoints", "ribs_status.json"
    )
