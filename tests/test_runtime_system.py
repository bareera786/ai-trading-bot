"""Behavioral tests for app.runtime.system.initialize_runtime_from_context."""
from __future__ import annotations

import signal
from typing import Dict, List, Sequence

from app.runtime import system as runtime_system


class DummyTradeHistory:
    def __init__(self, trades: Sequence[dict]):
        self._trades = list(trades)
        self.calls = 0

    def load_trades(self):
        self.calls += 1
        return list(self._trades)


class DummyPersistenceManager:
    def __init__(self, *, return_value: bool):
        self.return_value = return_value
        self.calls: List[tuple] = []

    def load_complete_state(self, trader, ml_system):
        self.calls.append((trader, ml_system))
        return self.return_value


class DummyTrader:
    def __init__(self, *, enabled: bool = True):
        self.trading_enabled = enabled
        self.portfolio_summary_calls: List[Dict[str, float]] = []

    def get_portfolio_summary(self, prices: Dict[str, float]):
        self.portfolio_summary_calls.append(prices)
        return {"value": sum(prices.values())}


class DummyMLSystem:
    def __init__(self, models=None):
        self.models = models
        self.continuous_calls = 0

    def start_continuous_training_cycle(self):
        self.continuous_calls += 1


class DummyBackgroundTaskManager:
    def __init__(self):
        self.calls: List[dict] = []

    def start_background_tasks(self, **kwargs):
        self.calls.append(kwargs)


class DummyHealthReportService:
    def __init__(self):
        self.refresh_calls: List[bool] = []
        self.periodic_started = False

    def refresh(self, *, run_backtest: bool):
        self.refresh_calls.append(run_backtest)

    def start_periodic_refresh(self):
        self.periodic_started = True


def test_initialize_runtime_full_context_triggers_services(monkeypatch):
    dashboard_data = {"bootstrap": {}}
    background_manager = DummyBackgroundTaskManager()
    trade_history = DummyTradeHistory([{"symbol": "BTCUSDT"}])
    persistence_manager = DummyPersistenceManager(return_value=True)
    ultimate_trader = DummyTrader()
    optimized_trader = DummyTrader()
    ultimate_ml = DummyMLSystem(models={"ultimate": object()})
    optimized_ml = DummyMLSystem(models={"optimized": object()})
    health_service = DummyHealthReportService()

    captured_signals = []

    def fake_signal(sig, handler):
        captured_signals.append((sig, handler))

    monkeypatch.setattr(runtime_system.signal, "signal", fake_signal)

    handler = lambda *args, **kwargs: None

    context = {
        "dashboard_data": dashboard_data,
        "trade_history": trade_history,
        "persistence_manager": persistence_manager,
        "ultimate_trader": ultimate_trader,
        "optimized_trader": optimized_trader,
        "ultimate_ml_system": ultimate_ml,
        "optimized_ml_system": optimized_ml,
        "background_task_manager": background_manager,
        "trading_config": {"continuous_training": True},
        "historical_data": {"prices": []},
        "top_symbols": ["BTCUSDT"],
        "get_active_trading_universe": lambda: ["BTCUSDT"],
        "get_real_market_data": lambda symbol: {"price": 50},
        "health_report_service": health_service,
        "signal_handler": handler,
    }

    runtime_system.initialize_runtime_from_context(context)

    dashboard_data = context["dashboard_data"]
    assert trade_history.calls == 1
    assert persistence_manager.calls == [(ultimate_trader, ultimate_ml)]
    assert ultimate_trader.portfolio_summary_calls == [{"BTCUSDT": 50}]
    assert dashboard_data["portfolio"] == {"value": 50}

    assert len(background_manager.calls) == 1
    task_call = background_manager.calls[0]
    assert task_call["start_ultimate_training"] is False
    assert task_call["start_optimized_training"] is False
    assert task_call["persistence_inputs"]["symbols"] == ["BTCUSDT"]

    assert ultimate_ml.continuous_calls == 1
    assert optimized_ml.continuous_calls == 1
    assert health_service.refresh_calls == [False]
    assert health_service.periodic_started is True
    assert captured_signals == [
        (signal.SIGINT, handler),
        (signal.SIGTERM, handler),
    ]

    assert dashboard_data["system_status"]["models_loaded"] is True
    assert dashboard_data["optimized_system_status"]["models_loaded"] is True
    assert (
        dashboard_data["optimized_system_status"]["trading_enabled"]
        is optimized_trader.trading_enabled
    )


def test_initialize_runtime_handles_sparse_context():
    dashboard_data = {"existing": {}}
    ultimate_trader = DummyTrader()
    optimized_trader = DummyTrader(enabled=False)
    ultimate_ml = DummyMLSystem()
    optimized_ml = DummyMLSystem()

    runtime_system.initialize_runtime_from_context(
        {
            "dashboard_data": dashboard_data,
            "ultimate_trader": ultimate_trader,
            "optimized_trader": optimized_trader,
            "ultimate_ml_system": ultimate_ml,
            "optimized_ml_system": optimized_ml,
        }
    )

    assert "portfolio" not in dashboard_data
    assert dashboard_data["system_status"] == {}
    assert dashboard_data["optimized_system_status"]["trading_enabled"] is False
