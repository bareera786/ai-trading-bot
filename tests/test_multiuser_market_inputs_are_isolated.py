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


class _MutatingTrader:
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
        self.calls = []

    def enable_real_trading(self, api_key, api_secret, testnet=True):
        self.real_trading_enabled = True

    def execute_ultimate_trade(self, symbol, _pred, market_data, historical_prices, _ensemble=None):
        # Intentionally mutate inputs to simulate a buggy strategy implementation.
        # Multi-user mode must prevent this from leaking across users.
        market_data["mutated_by"] = getattr(self, "user_id", None)
        historical_prices.append(getattr(self, "user_id", None))
        self.calls.append((symbol, market_data.get("mutated_by")))
        self.positions[symbol] = self.positions.get(symbol, 0) + 1
        return True, f"BUY {symbol}"

    def update_auto_take_profit_orders(self, _market_data):
        return None

    def check_advanced_stop_loss(self, _current_prices):
        return []

    def get_portfolio_summary(self, _current_prices):
        return {"positions": dict(self.positions)}

    def get_trade_statistics(self):
        return {"summary": {"trades": len(self.calls)}}

    def get_real_trading_status(self):
        return {"real_trading_enabled": bool(self.real_trading_enabled)}


class _MutatingPredictionTrader(_MutatingTrader):
    def execute_ultimate_trade(self, symbol, pred, market_data, historical_prices, ensemble=None):
        # Mutate prediction + ensemble objects to ensure MarketDataService protects
        # shared data structures in multi-user mode.
        self._last_pred_obj_id = id(pred)
        self._last_ensemble_obj_id = id(ensemble)
        if isinstance(pred, dict):
            pred["mutated_pred_by"] = getattr(self, "user_id", None)
        if isinstance(ensemble, dict):
            ensemble["mutated_ensemble_by"] = getattr(self, "user_id", None)
        return super().execute_ultimate_trade(symbol, pred, market_data, historical_prices, ensemble)


class _NestedMutatingPredictionTrader(_MutatingTrader):
    def execute_ultimate_trade(self, symbol, pred, market_data, historical_prices, ensemble=None):
        # Mutate nested sub-dicts to ensure deep-copy isolation (e.g., nested RIBS inputs).
        self.last_pred = pred
        self.last_ensemble = ensemble

        uid = getattr(self, "user_id", None)
        if isinstance(pred, dict):
            ue = pred.setdefault("ultimate_ensemble", {})
            if isinstance(ue, dict):
                ribs_payload = ue.setdefault("ribs", {})
                if isinstance(ribs_payload, dict):
                    ribs_payload["mutated_by"] = uid
                    self._last_pred_ribs_id = id(ribs_payload)

        if isinstance(ensemble, dict):
            ribs_payload = ensemble.setdefault("ribs", {})
            if isinstance(ribs_payload, dict):
                ribs_payload["mutated_by"] = uid
                self._last_ensemble_ribs_id = id(ribs_payload)

        return super().execute_ultimate_trade(symbol, pred, market_data, historical_prices, ensemble)


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
    def __init__(self):
        self._creds = {
            1: {"api_key": "k1", "api_secret": "s1", "testnet": True},
            2: {"api_key": "k2", "api_secret": "s2", "testnet": True},
        }

    def list_user_ids(self):
        return [1, 2]

    def get_credentials(self, kind, user_id=None):
        assert kind == "spot"
        if user_id is None:
            return {}
        return dict(self._creds.get(int(user_id), {}))


class _FakeCredentialService:
    def __init__(self):
        self.credentials_store = _FakeCredentialStore()

    def get_status(self, *args, **kwargs):
        return {"ok": True}


@pytest.fixture(autouse=True)
def _patch_redis(monkeypatch):
    from app.services import market_data as market_data_module

    monkeypatch.setattr(market_data_module.redis, "Redis", _DummyRedis)


def test_multiuser_auto_trade_inputs_are_isolated_per_user():
    from app.services.market_data import MarketDataService

    dashboard_data = {
        "system_status": {"models_training": False},
        "optimized_system_status": {},
        "ml_telemetry": {"ultimate": {}, "optimized": {}},
    }

    # Seed with enough history (>=20) to trigger auto execution.
    historical_data = {"BTCUSDT": [100.0] * 25}

    service = MarketDataService(
        dashboard_data=dashboard_data,
        historical_data=historical_data,
        trading_config={"parallel_processing": False},
        ultimate_trader=_MutatingTrader(),
        optimized_trader=_MutatingTrader(),
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
        persistence_manager=None,
        symbols_for_persistence=["BTCUSDT"],
        futures_safety_service=None,
        sleep_interval=5.0,
    )

    service.run_once()

    # Each user trader should have run once.
    assert set(service._user_traders.keys()) == {1, 2}

    # Critical: shared historical_data should only have the market-data append (+1),
    # not the per-user trader mutations (which would be +2 if shared).
    assert len(service.historical_data["BTCUSDT"]) == 26

    # Also ensure the shared market_data snapshot stored in dashboard is not polluted.
    assert "mutated_by" not in service.dashboard_data["market_data"]["BTCUSDT"]


def test_multiuser_predictions_and_ensemble_are_isolated_per_user():
    from app.services.market_data import MarketDataService

    dashboard_data = {
        "system_status": {"models_training": False},
        "optimized_system_status": {},
        "ml_telemetry": {"ultimate": {}, "optimized": {}},
    }

    historical_data = {"BTCUSDT": [100.0] * 25}

    service = MarketDataService(
        dashboard_data=dashboard_data,
        historical_data=historical_data,
        trading_config={"parallel_processing": False},
        ultimate_trader=_MutatingPredictionTrader(),
        optimized_trader=_MutatingPredictionTrader(),
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
        persistence_manager=None,
        symbols_for_persistence=["BTCUSDT"],
        futures_safety_service=None,
        sleep_interval=5.0,
    )

    service.run_once()

    # Ensure multi-user traders executed.
    assert set(service._user_traders.keys()) == {1, 2}

    u1_ultimate, u1_optimized = service._user_traders[1]
    u2_ultimate, u2_optimized = service._user_traders[2]

    # Each user's call should have seen its own mutated prediction value.
    assert u1_ultimate.calls == [("BTCUSDT", 1)]
    assert u2_ultimate.calls == [("BTCUSDT", 2)]
    assert u1_optimized.calls == [("BTCUSDT", 1)]
    assert u2_optimized.calls == [("BTCUSDT", 2)]

    # Prediction/ensemble dict objects must be distinct across user calls.
    assert getattr(u1_ultimate, "_last_pred_obj_id", None) != getattr(u2_ultimate, "_last_pred_obj_id", None)
    assert getattr(u1_ultimate, "_last_ensemble_obj_id", None) != getattr(u2_ultimate, "_last_ensemble_obj_id", None)
    assert getattr(u1_optimized, "_last_pred_obj_id", None) != getattr(u2_optimized, "_last_pred_obj_id", None)
    assert getattr(u1_optimized, "_last_ensemble_obj_id", None) != getattr(u2_optimized, "_last_ensemble_obj_id", None)

    # Critical: dashboard-visible predictions must not be polluted by per-user mutations.
    assert "mutated_pred_by" not in service.dashboard_data["ml_predictions"]["BTCUSDT"]
    assert "mutated_pred_by" not in service.dashboard_data["optimized_ml_predictions"]["BTCUSDT"]
    assert "mutated_ensemble_by" not in service.dashboard_data["ensemble_predictions"]
    assert "mutated_ensemble_by" not in service.dashboard_data["optimized_ensemble_predictions"]


def test_multiuser_nested_prediction_payloads_are_isolated_per_user():
    from app.services.market_data import MarketDataService

    class _FakeNestedMLSystem(_FakeMLSystem):
        def predict_ultimate(self, _symbol, _snapshot):
            return {
                "ultimate_ensemble": {
                    "indicators_total": 1,
                    "data_source": "TEST",
                    "ribs": {"seed": "shared"},
                }
            }

        def predict_professional(self, _symbol, _snapshot):
            return {
                "ultimate_ensemble": {
                    "indicators_total": 1,
                    "data_source": "TEST",
                    "ribs": {"seed": "shared"},
                }
            }

    dashboard_data = {
        "system_status": {"models_training": False},
        "optimized_system_status": {},
        "ml_telemetry": {"ultimate": {}, "optimized": {}},
    }

    historical_data = {"BTCUSDT": [100.0] * 25}

    service = MarketDataService(
        dashboard_data=dashboard_data,
        historical_data=historical_data,
        trading_config={"parallel_processing": False},
        ultimate_trader=_NestedMutatingPredictionTrader(),
        optimized_trader=_NestedMutatingPredictionTrader(),
        ultimate_ml_system=_FakeNestedMLSystem(),
        optimized_ml_system=_FakeNestedMLSystem(),
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
        persistence_manager=None,
        symbols_for_persistence=["BTCUSDT"],
        futures_safety_service=None,
        sleep_interval=5.0,
    )

    service.run_once()

    assert set(service._user_traders.keys()) == {1, 2}

    u1_ultimate, u1_optimized = service._user_traders[1]
    u2_ultimate, u2_optimized = service._user_traders[2]

    # Nested ribs sub-dicts must be distinct across user calls.
    assert getattr(u1_ultimate, "_last_pred_ribs_id", None) != getattr(u2_ultimate, "_last_pred_ribs_id", None)
    assert getattr(u1_ultimate, "_last_ensemble_ribs_id", None) != getattr(u2_ultimate, "_last_ensemble_ribs_id", None)
    assert getattr(u1_optimized, "_last_pred_ribs_id", None) != getattr(u2_optimized, "_last_pred_ribs_id", None)
    assert getattr(u1_optimized, "_last_ensemble_ribs_id", None) != getattr(u2_optimized, "_last_ensemble_ribs_id", None)

    # Dashboard-visible prediction structures must not be polluted by nested mutations.
    assert "mutated_by" not in service.dashboard_data["ml_predictions"]["BTCUSDT"]["ultimate_ensemble"]["ribs"]
    assert "mutated_by" not in service.dashboard_data["optimized_ml_predictions"]["BTCUSDT"]["ultimate_ensemble"]["ribs"]
    assert "mutated_by" not in service.dashboard_data["ensemble_predictions"].get("ribs", {})
    assert "mutated_by" not in service.dashboard_data["optimized_ensemble_predictions"].get("ribs", {})
