import importlib.util
import pandas as pd
import numpy as np
import pytest


def load_optimizer_class():
    # Load the module directly from file to avoid importing the top-level `app` package
    # Ensure a minimal 'ribs' module exists for tests so the optimizer can import
    import sys
    import types

    if "ribs" not in sys.modules:
        # Minimal dummy implementations used by the optimizer
        class GridArchive:
            def __init__(self, *args, **kwargs):
                self.stats = types.SimpleNamespace(
                    num_elites=0, coverage=0.0, qd_score=0.0
                )

            def sample_elites(self, n):
                return []

        class EvolutionStrategyEmitter:
            def __init__(self, *args, **kwargs):
                pass

        class Scheduler:
            def __init__(self, *args, **kwargs):
                pass

            def ask(self):
                return []

            def tell(self, objectives, behaviors):
                return None

        ribs_mod = types.ModuleType("ribs")
        ribs_mod.archives = types.SimpleNamespace(GridArchive=GridArchive)
        ribs_mod.emitters = types.SimpleNamespace(
            EvolutionStrategyEmitter=EvolutionStrategyEmitter
        )
        ribs_mod.schedulers = types.SimpleNamespace(Scheduler=Scheduler)
        sys.modules["ribs"] = ribs_mod

    spec = importlib.util.spec_from_file_location(
        "ribs_optimizer_mod",
        "./app/services/ribs_optimizer.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TradingRIBSOptimizer


TradingRIBSOptimizer = load_optimizer_class()


def make_market_df():
    # minimal OHLCV
    return pd.DataFrame({"close": [1.0, 1.1, 1.2, 1.3, 1.4]})


def test_evaluate_solution_with_slice_does_not_raise():
    opt = TradingRIBSOptimizer(config_path="config/ribs_config.yaml")
    market = {"ohlcv": make_market_df()}

    # Pass an invalid solution (slice) which used to cause 'unhashable type: slice'
    obj, beh = opt.evaluate_solution(slice(None), market)

    # Evaluation should be handled and produce penalized objective (float)
    assert isinstance(obj, float)


def test_run_optimization_cycle_handles_invalid_solution(monkeypatch):
    opt = TradingRIBSOptimizer(config_path="config/ribs_config.yaml")
    market = {"ohlcv": make_market_df()}

    # Mock scheduler.ask to return one valid solution and one invalid slice
    def fake_ask():
        return [np.zeros(opt.config["solution_dim"]), slice(None)]

    # Replace the scheduler.ask with our fake_ask
    monkeypatch.setattr(opt.scheduler, "ask", fake_ask, raising=True)

    # Should run without raising and return a list (possibly empty) of elites
    elites = opt.run_optimization_cycle(market, iterations=1)
    assert isinstance(elites, list)
