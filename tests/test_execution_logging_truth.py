import json
import os
import tempfile
from types import SimpleNamespace
from typing import Any, cast

import pytest


def test_futures_execution_persists_full_metadata():
    import atexit

    original_register = atexit.register
    atexit.register = lambda *_args, **_kwargs: None
    try:
        import ai_ml_auto_bot_final as bot
    finally:
        atexit.register = original_register
    from app.services.trade_history import ComprehensiveTradeHistory

    class _FuturesTrader:
        testnet = True

        def ensure_leverage(self, _symbol, _leverage):
            return True

        def place_market_order(self, _symbol, _side, _qty, reduce_only=False):
            # Initial acceptance response (Binance)
            return {
                "orderId": 123,
                "clientOrderId": "abc123",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "status": "NEW",
                "price": "0",
                "avgPrice": "27123.45",
                "origQty": "0.010",
                "executedQty": "0.000",
                "reduceOnly": bool(reduce_only),
                "closePosition": False,
                "workingType": "CONTRACT_PRICE",
                "priceProtect": False,
                "positionSide": "LONG",
            }

        def get_order(self, _symbol, order_id=None, client_order_id=None):
            assert order_id == 123
            assert client_order_id == "abc123"
            return {
                "orderId": 123,
                "clientOrderId": "abc123",
                "updateTime": 1700000000123,
            }

        def get_position(self, _symbol):
            # Position snapshot values from Binance
            return {
                "marginType": "isolated",
                "leverage": "7",
                "positionSide": "LONG",
            }

    dummy = cast(
        Any,
        SimpleNamespace(
            futures_trading_enabled=True,
            futures_trader=_FuturesTrader(),
            futures_safety_service=None,
        ),
    )

    with tempfile.TemporaryDirectory() as tmp:
        th = ComprehensiveTradeHistory(data_dir=tmp)
        dummy.trade_history = th

        dummy.trade_history = th

        resp = bot.UltimateAIAutoTrader._submit_futures_order(
            dummy, "BTCUSDT", "BUY", 0.01, leverage=20, reduce_only=False
        )
        assert isinstance(resp, dict)

        with open(os.path.join(tmp, "comprehensive_trades.json"), "r") as f:
            trades = json.load(f)

    assert len(trades) == 1
    trade = trades[0]

    # Required fields
    assert trade["market_type"] == "FUTURES"
    assert trade["exchange"] == "BINANCE_FUTURES"
    assert trade["execution_mode"] == "futures"
    assert trade["symbol"] == "BTCUSDT"
    assert trade["side"] == "BUY"
    assert trade["quantity"] == "0.010"
    assert trade["price"] == "27123.45"
    assert trade["status"] == "NEW"
    assert trade["binance_order_id"] == 123
    assert trade["client_order_id"] == "abc123"

    # Futures-specific metadata (must be persisted)
    assert trade["margin_type"] == "isolated"
    assert trade["leverage"] == "7"
    assert trade["position_side"] == "LONG"
    assert trade["reduce_only"] is False
    assert trade["close_position"] is False
    assert trade["working_type"] == "CONTRACT_PRICE"
    assert trade["price_protect"] is False

    # Timestamp must be derived from Binance-provided ms value
    assert trade["binance_timestamp_ms"] == 1700000000123
    assert isinstance(trade["timestamp"], str) and trade["timestamp"].endswith("Z")
