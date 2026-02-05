import importlib
import types

import pytest

pytest.importorskip("flask_mail")


def test_ribs_stress_runner_uses_optimizer(monkeypatch, tmp_path):
    # Create a fake optimizer that records calls
    calls = {}

    class FakeOpt:
        def __init__(self, *args, **kwargs):
            calls["init"] = True

        def run_optimization_cycle(self, market_data, iterations=0):
            calls["ran"] = iterations
            return []

    monkeypatch.setenv("PYTHONPATH", ".")
    # Monkeypatch the imported class in the module
    mod = importlib.import_module("scripts.ribs_stress_runner")
    monkeypatch.setattr(mod, "TradingRIBSOptimizer", FakeOpt)

    # Run main
    mod.main(iterations=3)
    assert calls.get("init") is True
    assert calls.get("ran") == 3
