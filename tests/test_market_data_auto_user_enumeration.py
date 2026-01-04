import logging

import pytest


class _DummyRedis:
    def __init__(self, *args, **kwargs):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def setex(self, key, ttl, value):
        self._store[key] = value


class _FakeEnsembleSystem:
    correlation_matrix = None
    market_regime = "NEUTRAL"

    def create_correlation_matrix(self, _preds):
        self.correlation_matrix = {}

    def get_ensemble_prediction(self, _preds, _market_data):
        return {"ensemble": "ok"}


class _FakeRiskManager:
    market_stress_indicator = 0.0
    current_risk_profile = "NORMAL"

    def get_risk_multiplier(self):
        return 1.0


class _FakeSafetyManager:
    def get_status_snapshot(self):
        return {"ok": True}


class _FakeTradeHistory:
    def get_journal_events(self, limit=50):
        return []

    def get_trade_statistics(self):
        return {"summary": {"trades": 0}}


class _FakeTrader:
    indicator_block_key = "ultimate_ensemble"

    def __init__(self, initial_balance=10000):
        self.initial_balance = initial_balance
        self.positions = {}
        self.trading_enabled = True
        self.paper_trading = True
        self.real_trading_enabled = False
        self.futures_trading_enabled = False
        self.futures_trader = None
        self.latest_market_data = {}
        self.ensemble_system = _FakeEnsembleSystem()
        self.risk_manager = _FakeRiskManager()
        self.safety_manager = _FakeSafetyManager()
        self.trade_history = _FakeTradeHistory()
        self.qfm_engine = None
        self.calls = {"execute": 0, "enable": 0}

    def enable_real_trading(self, api_key, api_secret, testnet=True):
        self.calls["enable"] += 1
        self.real_trading_enabled = True

    def execute_ultimate_trade(self, symbol, *_args, **_kwargs):
        self.calls["execute"] += 1
        self.positions[symbol] = self.positions.get(symbol, 0) + 1
        return True, f"BUY {symbol}"

    def update_auto_take_profit_orders(self, _market_data):
        return None

    def check_advanced_stop_loss(self, _current_prices):
        return []

    def get_portfolio_summary(self, _current_prices):
        return {"positions": dict(self.positions)}

    def get_trade_statistics(self):
        return {"summary": {"trades": self.calls["execute"]}}

    def get_real_trading_status(self):
        return {"real_trading_enabled": bool(self.real_trading_enabled)}


class _FakeMLSystem:
    def __init__(self):
        self.ensemble_system = _FakeEnsembleSystem()
        self.models = {}

    def predict_ultimate(self, _symbol, _snapshot):
        return {"ultimate_ensemble": {"indicators_total": 1, "data_source": "TEST"}}

    def predict_professional(self, _symbol, _snapshot):
        return {"ultimate_ensemble": {"indicators_total": 1, "data_source": "TEST"}}

    def generate_crt_signals(self, _symbol, _snapshot, _history):
        return {"signal": "HOLD", "confidence": 0.5}

    def get_backtest_results(self):
        return {}

    def get_ml_telemetry(self):
        return {}


class _FakeParallelEngine:
    def parallel_predict(self, _symbols, _market_data, _ml_system):
        return {}


class _FakeCredentialStore:
    def list_user_ids(self):
        return [999]

    def get_credentials(self, kind, user_id=None):
        assert kind == "spot"
        return {"api_key": "k", "api_secret": "s", "testnet": True}


class _FakeCredentialService:
    def __init__(self):
        self.credentials_store = _FakeCredentialStore()

    def get_status(self, *args, **kwargs):
        return {"ok": True}


@pytest.fixture(autouse=True)
def _patch_redis(monkeypatch):
    from app.services import market_data as market_data_module

    monkeypatch.setattr(market_data_module.redis, "Redis", _DummyRedis)


def test_auto_user_id_provider_takes_precedence_over_store():
    from app.services.market_data import MarketDataService

    dashboard_data = {
        "system_status": {"models_training": False},
        "optimized_system_status": {},
        "ml_telemetry": {"ultimate": {}, "optimized": {}},
    }

    service = MarketDataService(
        dashboard_data=dashboard_data,
        historical_data={"BTCUSDT": [100.0] * 25},
        trading_config={"parallel_processing": False},
        ultimate_trader=_FakeTrader(),
        optimized_trader=_FakeTrader(),
        ultimate_ml_system=_FakeMLSystem(),
        optimized_ml_system=_FakeMLSystem(),
        parallel_engine=_FakeParallelEngine(),
        futures_manual_settings={},
        binance_credential_service=_FakeCredentialService(),
        get_active_trading_universe=lambda: ["BTCUSDT"],
        get_real_market_data=lambda _symbol: {
            "price": 101.0,
            "change": 0.0,
            "volume": 1.0,
            "high": 101.5,
            "low": 99.5,
        },
        get_trending_pairs=lambda: ["BTCUSDT"],
        refresh_symbol_counters=lambda: None,
        refresh_indicator_dashboard_state=lambda: None,
        safe_float=lambda v, d=0.0: float(v) if v is not None else float(d),
        bot_logger=logging.getLogger("test"),
        auto_user_id_provider=lambda: [1, 2],
        persistence_manager=None,
        symbols_for_persistence=["BTCUSDT"],
        sleep_interval=5.0,
    )

    assert service._resolve_auto_user_ids() == [1, 2]
