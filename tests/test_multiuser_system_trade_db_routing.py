import importlib


def test_system_trade_recording_routes_to_trader_user_id(monkeypatch):
    mod = importlib.import_module("ai_ml_auto_bot_final")

    # Enable DB recording, but set a fallback user id that should be ignored
    # when the trader has a user_id.
    monkeypatch.setitem(mod.TRADING_CONFIG, "record_system_trades_to_db", True)
    monkeypatch.setitem(mod.TRADING_CONFIG, "system_trade_user_id", 999)

    calls = []

    def _fake_record_user_trade(user_id, symbol, side, quantity, price, **kwargs):
        calls.append(
            {
                "user_id": int(user_id),
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "kwargs": kwargs,
            }
        )
        return True

    monkeypatch.setattr(mod, "record_user_trade", _fake_record_user_trade)

    t1 = mod.UltimateAIAutoTrader(initial_balance=1000)
    t2 = mod.UltimateAIAutoTrader(initial_balance=1000)
    t1.user_id = 1
    t2.user_id = 2

    trade = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "quantity": 0.01,
        "price": 50000,
        "type": "system",
        "signal": "BUY",
        "confidence": 0.9,
    }

    t1._maybe_record_system_trade(dict(trade))
    t2._maybe_record_system_trade(dict(trade))

    assert [c["user_id"] for c in calls] == [1, 2]


def test_system_trade_recording_trade_record_overrides_trader_user_id(monkeypatch):
    mod = importlib.import_module("ai_ml_auto_bot_final")

    monkeypatch.setitem(mod.TRADING_CONFIG, "record_system_trades_to_db", True)
    monkeypatch.setitem(mod.TRADING_CONFIG, "system_trade_user_id", 999)

    calls = []

    def _fake_record_user_trade(user_id, *_args, **_kwargs):
        calls.append(int(user_id))
        return True

    monkeypatch.setattr(mod, "record_user_trade", _fake_record_user_trade)

    t = mod.UltimateAIAutoTrader(initial_balance=1000)
    t.user_id = 1

    t._maybe_record_system_trade(
        {
            "user_id": 123,
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "price": 50000,
        }
    )

    assert calls == [123]


def test_system_trade_recording_falls_back_to_config_user_id(monkeypatch):
    mod = importlib.import_module("ai_ml_auto_bot_final")

    monkeypatch.setitem(mod.TRADING_CONFIG, "record_system_trades_to_db", True)
    monkeypatch.setitem(mod.TRADING_CONFIG, "system_trade_user_id", 77)

    calls = []

    def _fake_record_user_trade(user_id, *_args, **_kwargs):
        calls.append(int(user_id))
        return True

    monkeypatch.setattr(mod, "record_user_trade", _fake_record_user_trade)

    t = mod.UltimateAIAutoTrader(initial_balance=1000)
    # No t.user_id

    t._maybe_record_system_trade(
        {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.01,
            "price": 50000,
        }
    )

    assert calls == [77]
