import time
from pathlib import Path

from app.tasks.self_improvement import SelfImprovementWorker


class DummyOptimizer:
    def __init__(self, backtest_result=None):
        self._backtest = backtest_result or {
            "total_return": 0.0,
            "sharpe_ratio": 0.0,
            "max_drawdown": 50.0,
            "win_rate": 0.0,
        }

    def decode_solution(self, sol):
        return {"rsi_period": 14}

    def run_backtest(self, params, market_data):
        return self._backtest


def make_worker(tmp_path, config_overrides=None):
    cfg = {
        "enable_ribs_optimization": True,
    }
    if config_overrides:
        cfg.update(config_overrides)

    dashboard_data = {}
    worker = SelfImprovementWorker(
        ultimate_trader=None,
        optimized_trader=None,
        ultimate_ml_system=None,
        optimized_ml_system=None,
        dashboard_data=dashboard_data,
        trading_config=cfg,
        logger=None,
        project_root=Path(tmp_path),
    )
    return worker


def test_deploy_strategy_rejected_by_backtest(tmp_path):
    worker = make_worker(tmp_path, {"ribs_deploy_min_return": 10.0})
    # optimizer returns low return
    worker.ribs_optimizer = DummyOptimizer(
        backtest_result={
            "total_return": 1.0,
            "sharpe_ratio": 0.1,
            "max_drawdown": 5.0,
            "win_rate": 0.1,
        }
    )
    res = worker.deploy_strategy([1, 2, 3], "ribs_test_1")
    assert isinstance(res, dict)
    assert res["success"] is False
    assert "total_return" in res["message"]


def test_deploy_strategy_success_saves_file(tmp_path):
    worker = make_worker(tmp_path, {"ribs_deploy_min_return": -100.0})
    worker.ribs_optimizer = DummyOptimizer(
        backtest_result={
            "total_return": 50.0,
            "sharpe_ratio": 1.2,
            "max_drawdown": 5.0,
            "win_rate": 0.6,
        }
    )
    res = worker.deploy_strategy([1, 2, 3], "ribs_test_2")
    assert isinstance(res, dict)
    assert res["success"] is True
    # File should exist
    strategies_dir = Path(tmp_path) / "strategies" / "ribs_generated"
    assert strategies_dir.exists()
    files = list(strategies_dir.glob("ribs_test_2.json"))
    assert len(files) == 1
