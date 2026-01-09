import logging
from types import SimpleNamespace
from typing import Any, cast

import pytest


class _DummyRedis:
    def __init__(self, *args, **kwargs):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def setex(self, key, ttl, value):
        self._store[key] = value


class _FakeFuturesTrader:
    def __init__(self):
        self.calls = []

    def ensure_leverage(self, symbol, leverage):
        self.calls.append(("ensure_leverage", symbol, leverage))

    def place_market_order(self, symbol, side, quantity, reduce_only=False):
        self.calls.append(("place_market_order", symbol, side, float(quantity), bool(reduce_only)))
        return {"orderId": "1", "symbol": symbol, "side": side, "executedQty": quantity}


class _BlockAllSafety:
    def should_allow_order(self, **kwargs):
        return False, "BLOCKED", {"kwargs": kwargs}


class _AllowAllSafety:
    def should_allow_order(self, **kwargs):
        return True, "OK", {"kwargs": kwargs}


class _FakeTradeHistory:
    def log_journal_event(self, *_args, **_kwargs):
        return None

    def get_trade_history(self):
        return []


class _FakeUltimateTrader:
    def __init__(self, initial_balance=10000, **_kwargs):
        self.initial_balance = initial_balance
        self.futures_trading_enabled = True
        self.futures_trader = _FakeFuturesTrader()
        self.trade_history = _FakeTradeHistory()
        self.last_futures_order = None
        self.futures_safety_service: Any = None

    def _submit_futures_order(self, symbol, side, quantity, leverage=None, reduce_only=False):
        # Minimal stand-in for the real choke-point behavior:
        if not self.futures_trading_enabled or not self.futures_trader:
            return None

        leverage_to_use = leverage or 3
        safety_service = getattr(self, "futures_safety_service", None)
        if safety_service and hasattr(safety_service, "should_allow_order"):
            allowed, _reason, _details = safety_service.should_allow_order(
                symbol=str(symbol).upper(),
                side=str(side).upper(),
                quantity=float(quantity),
                leverage=int(leverage_to_use),
                reduce_only=bool(reduce_only),
                trader=self,
            )
            if not allowed:
                return None

        self.futures_trader.ensure_leverage(symbol, leverage_to_use)
        return self.futures_trader.place_market_order(symbol, side, float(quantity), reduce_only=reduce_only)


class _DummyCredStore:
    def list_user_ids(self):
        return [1, 2]

    def get_credentials(self, *_args, **_kwargs):
        return {}


class _DummyCredSvc:
    def __init__(self):
        self.credentials_store = _DummyCredStore()


@pytest.fixture(autouse=True)
def _patch_redis(monkeypatch):
    from app.services import market_data as market_data_module

    monkeypatch.setattr(market_data_module.redis, "Redis", _DummyRedis)


def test_market_data_attaches_safety_to_user_traders():
    from app.services.market_data import MarketDataService

    safety = _AllowAllSafety()

    service = MarketDataService(
        dashboard_data={},
        historical_data={},
        trading_config={},
        ultimate_trader=_FakeUltimateTrader(),
        optimized_trader=_FakeUltimateTrader(),
        ultimate_ml_system=object(),
        optimized_ml_system=object(),
        parallel_engine=object(),
        futures_manual_settings={},
        binance_credential_service=_DummyCredSvc(),
        get_active_trading_universe=lambda: [],
        get_real_market_data=lambda _symbol: None,
        get_trending_pairs=lambda: [],
        refresh_symbol_counters=lambda: None,
        refresh_indicator_dashboard_state=lambda: None,
        safe_float=lambda v, d=0.0: float(v) if v is not None else d,
        bot_logger=logging.getLogger("test"),
        persistence_manager=None,
        symbols_for_persistence=[],
        futures_safety_service=safety,
        sleep_interval=5.0,
    )

    u1, _ = service._get_or_create_user_traders(1)
    u2, _ = service._get_or_create_user_traders(2)

    assert getattr(u1, "futures_safety_service", None) is safety
    assert getattr(u2, "futures_safety_service", None) is safety


def test_futures_order_is_blocked_when_safety_blocks():
    trader = _FakeUltimateTrader()
    trader.futures_safety_service = _BlockAllSafety()

    resp = trader._submit_futures_order("BTCUSDT", "BUY", 0.01, leverage=3)
    assert resp is None
    assert trader.futures_trader.calls == []


def test_futures_order_executes_when_safety_allows():
    trader = _FakeUltimateTrader()
    trader.futures_safety_service = _AllowAllSafety()

    resp = trader._submit_futures_order("BTCUSDT", "BUY", 0.01, leverage=3)
    assert isinstance(resp, dict)
    assert any(call[0] == "place_market_order" for call in trader.futures_trader.calls)


def test_manual_futures_fallback_cannot_bypass_safety(monkeypatch):
    from flask import Flask

    from app.services.trading import create_user_trader_resolver

    class _BlockAll:
        def should_allow_order(self, **_kwargs):
            return False, "BLOCKED", {}

    class _BoomMarketData:
        def _get_or_create_user_traders(self, _user_id):
            raise RuntimeError("force fallback")

    called = {"count": 0}

    class _FakeLegacyFutures:
        def execute_manual_futures_trade(self, *_args, **_kwargs):
            called["count"] += 1
            return {"success": True, "order": {"orderId": "1"}, "price": 1.0}

    app = Flask(__name__)
    app.config["TESTING"] = True

    ctx = {
        "market_data_service": _BoomMarketData(),
        "service_runtime": SimpleNamespace(futures_safety_service=_BlockAll()),
        "binance_credentials_store": object(),
    }

    with app.app_context():
        app.extensions = {"ai_bot_context": ctx}
        resolver = create_user_trader_resolver(
            cast(Any, SimpleNamespace(ultimate_trader=None, optimized_trader=None))
        )
        executor = resolver(user_id=1, profile="ultimate")
        executor._futures_client = lambda: _FakeLegacyFutures()

        resp = executor.execute_manual_futures_trade("BTCUSDT", "BUY", 0.01, leverage=3)

    assert resp["success"] is False
    assert "TRADE_BLOCKED" in (resp.get("error") or "")
    assert called["count"] == 0
