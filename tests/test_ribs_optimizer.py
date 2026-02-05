import importlib
import sys
import types
import yaml
import numpy as np
import pandas as pd
from pathlib import Path


def make_fake_ribs():
    """Create a minimal fake `ribs` module exposing archives, emitters, schedulers used by the optimizer."""
    fake = types.SimpleNamespace()

    class FakeStats:
        def __init__(self):
            self.num_elites = 0
            self.coverage = 0.0
            self.qd_score = 0.0

    class GridArchive:
        def __init__(self, **kwargs):
            self._stats = FakeStats()

        @property
        def stats(self):
            return self._stats

        def sample_elites(self, n):
            return []

    class EvolutionStrategyEmitter:
        def __init__(self, **kwargs):
            pass

    class Scheduler:
        def __init__(self, archive, emitters):
            self._archive = archive
            self._emitters = emitters

        def ask(self):
            # return two simple solutions (numpy arrays)
            return [np.zeros(10), np.ones(10) * 0.1]

        def tell(self, objectives, behaviors):
            # no-op for tests
            return None

    fake.archives = types.SimpleNamespace(GridArchive=GridArchive)
    fake.emitters = types.SimpleNamespace(
        EvolutionStrategyEmitter=EvolutionStrategyEmitter
    )
    fake.schedulers = types.SimpleNamespace(Scheduler=Scheduler)

    return fake


def make_config(tmp_path: Path):
    cfg = {
        "ribs": {
            "solution_dim": 10,
            "archive_dimensions": [10],
            "archive_ranges": [[0, 1]] * 10,
            "num_emitters": 2,
            "sigma0": 0.1,
            "batch_size": 2,
            "progress_interval": 1,
        }
    }
    p = tmp_path / "ribs_config.yaml"
    p.write_text(yaml.safe_dump(cfg))
    return str(p)


def test_decode_solution_and_sanitization(tmp_path, monkeypatch):
    fake = make_fake_ribs()
    monkeypatch.setitem(sys.modules, "ribs", fake)

    cfg_path = make_config(tmp_path)

    from app.services.ribs_optimizer import TradingRIBSOptimizer

    opt = TradingRIBSOptimizer(config_path=cfg_path)

    # Provide a solution with extreme/invalid values
    sol = np.array([1000, -1000, None, 1e9, -5, 0, -10, 0, 2, 100])
    params = opt.decode_solution(sol)

    # Check core clamps and sensible defaults
    assert 1 <= params["rsi_period"] <= 100
    assert params["macd_slow"] > params["macd_fast"]
    assert params["take_profit"] >= 0.1
    assert params["stop_loss"] >= 0.1
    assert 0.001 <= params["position_size"] <= 1.0


def test_calculate_rsi_malformed_period(monkeypatch):
    fake = make_fake_ribs()
    monkeypatch.setitem(sys.modules, "ribs", fake)

    from app.services.ribs_optimizer import TradingRIBSOptimizer

    # Use a small in-memory config via monkeypatching load_config
    monkeypatch.setattr(
        TradingRIBSOptimizer,
        "load_config",
        lambda self, p: {
            "solution_dim": 10,
            "archive_dimensions": [10],
            "archive_ranges": [[0, 1]] * 10,
            "num_emitters": 1,
            "sigma0": 0.1,
            "batch_size": 1,
        },
    )

    opt = TradingRIBSOptimizer(config_path="irrelevant")

    prices = pd.Series([1.0, 1.1, 1.2, 1.15])
    rsi = opt.calculate_rsi(prices, period="bad")
    # Should return a neutral series (50s)
    assert all(v == 50 for v in rsi.tolist())


def test_run_backtest_empty_and_small(monkeypatch):
    fake = make_fake_ribs()
    monkeypatch.setitem(sys.modules, "ribs", fake)

    from app.services.ribs_optimizer import TradingRIBSOptimizer

    monkeypatch.setattr(
        TradingRIBSOptimizer,
        "load_config",
        lambda self, p: {
            "solution_dim": 10,
            "archive_dimensions": [10],
            "archive_ranges": [[0, 1]] * 10,
            "num_emitters": 1,
            "sigma0": 0.1,
            "batch_size": 1,
        },
    )

    opt = TradingRIBSOptimizer(config_path="irrelevant")

    # Empty df -> penalty
    res = opt.run_backtest({}, {"ohlcv": pd.DataFrame()})
    assert res["total_return"] == -50.0

    # Small df should return neutral or penalized result (no trades)
    df = pd.DataFrame({"close": [1.0, 1.05, 1.02]})
    res2 = opt.run_backtest({}, {"ohlcv": df})
    assert "total_return" in res2


def test_run_optimization_cycle_smoke(tmp_path, monkeypatch):
    fake = make_fake_ribs()
    monkeypatch.setitem(sys.modules, "ribs", fake)

    cfg_path = make_config(tmp_path)

    from app.services.ribs_optimizer import TradingRIBSOptimizer

    opt = TradingRIBSOptimizer(config_path=cfg_path)

    # Prepare simple market data with some movement so strategies can produce returns
    df = pd.DataFrame({"close": [1.0, 0.95, 1.1, 1.2, 0.9, 1.0, 1.3, 1.25]})
    elites = opt.run_optimization_cycle({"ohlcv": df}, iterations=2)

    # Should return a list (possibly empty) and not raise
    assert isinstance(elites, list)
