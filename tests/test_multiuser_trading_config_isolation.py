import ai_ml_auto_bot_final as bot_module


def test_trading_config_isolated_per_trader_instance(monkeypatch):
    trader_a = bot_module.UltimateAIAutoTrader()
    trader_b = bot_module.UltimateAIAutoTrader()

    # Baseline: each trader starts with a copy of the current global config.
    initial_global_risk = bot_module.TRADING_CONFIG["risk_per_trade"]
    assert trader_a.trading_config["risk_per_trade"] == initial_global_risk
    assert trader_b.trading_config["risk_per_trade"] == initial_global_risk

    # Force trader_a to "learn" with a high success rate to trigger risk increase.
    winning_trades = [{"status": "CLOSED", "pnl": 1.0} for _ in range(20)]
    monkeypatch.setattr(trader_a.trade_history, "get_trade_history", lambda: list(winning_trades))

    trader_a.improve_bot_efficiency_ultimate()

    # Global config must not change.
    assert bot_module.TRADING_CONFIG["risk_per_trade"] == initial_global_risk

    # Trader A's per-instance config may change; Trader B must remain unchanged.
    assert trader_a.trading_config["risk_per_trade"] != initial_global_risk
    assert trader_b.trading_config["risk_per_trade"] == initial_global_risk
