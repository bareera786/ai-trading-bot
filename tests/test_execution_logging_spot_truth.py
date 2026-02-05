import json
import os
import tempfile
from types import SimpleNamespace
from typing import Any, cast


def test_spot_execution_has_no_futures_fields():
    import atexit

    original_register = atexit.register
    atexit.register = lambda *_args, **_kwargs: None
    try:
        import ai_ml_auto_bot_final as bot
    finally:
        atexit.register = original_register

    from app.services.trade_history import ComprehensiveTradeHistory

    class _SpotTrader:
        testnet = False
        last_error = None

        def place_real_order(self, _symbol, _side, _qty, price=None, order_type="MARKET"):
            # Binance spot acceptance response
            return {
                "orderId": 456,
                "clientOrderId": "spot_456",
                "symbol": "ETHUSDT",
                "side": "SELL",
                "status": "FILLED",
                "price": "2543.21",
                "origQty": "0.250000",
                "executedQty": "0.250000",
                "transactTime": 1700000000456,
            }

        def get_order(self, _symbol, order_id=None, client_order_id=None):
            assert order_id == 456
            assert client_order_id == "spot_456"
            return {"orderId": 456, "clientOrderId": "spot_456", "updateTime": 1700000000456}

        def is_ready(self):
            return True

        def _resolve_price(self, _symbol, _ref=None):
            return 2543.21

    dummy = cast(
        Any,
        SimpleNamespace(
            real_trading_enabled=True,
            real_trader=_SpotTrader(),
        ),
    )

    # Minimal helpers used by _submit_real_order
    dummy._resolve_market_price = lambda _symbol, _price=None: None
    dummy._get_symbol_min_notional = lambda _symbol: None
    dummy._prepare_sell_quantity = lambda _symbol, qty: qty
    dummy._record_skipped_real_order = lambda *_args, **_kwargs: {"status": "SKIPPED"}
    dummy._extract_filled_quantity = lambda *_args, **_kwargs: 0.25
    dummy._calculate_quote_spent = lambda *_args, **_kwargs: 0.0
    dummy._extract_commissions = lambda *_args, **_kwargs: {}

    with tempfile.TemporaryDirectory() as tmp:
        th = ComprehensiveTradeHistory(data_dir=tmp)
        dummy.trade_history = th
        dummy.last_real_order = None

        resp = bot.UltimateAIAutoTrader._submit_real_order(
            dummy, "ETHUSDT", "SELL", 0.25, price=None, order_type="MARKET"
        )
        assert isinstance(resp, dict)

        with open(os.path.join(tmp, "comprehensive_trades.json"), "r") as f:
            trades = json.load(f)

    assert len(trades) == 1
    trade = trades[0]

    assert trade["market_type"] == "SPOT"
    assert trade["exchange"] == "BINANCE_SPOT"
    assert trade["execution_mode"] == "real"
    assert trade["symbol"] == "ETHUSDT"
    assert trade["side"] == "SELL"
    assert trade["quantity"] == "0.250000"
    assert trade["price"] == "2543.21"
    assert trade["status"] == "FILLED"
    assert trade["binance_order_id"] == 456
    assert trade["client_order_id"] == "spot_456"

    # Futures-only fields must be explicitly absent/null.
    assert trade["margin_type"] is None
    assert trade["leverage"] is None
    assert trade["position_side"] is None
    assert trade["reduce_only"] is False
    assert trade["close_position"] is False
    assert trade["working_type"] is None
    assert trade["price_protect"] is None

    assert trade["binance_timestamp_ms"] == 1700000000456
    assert isinstance(trade["timestamp"], str) and trade["timestamp"].endswith("Z")
