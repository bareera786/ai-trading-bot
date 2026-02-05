import types
import pytest

import ai_ml_auto_bot_final as core


def test_extract_filled_quantity_prefers_executedQty():
    resp = {"executedQty": "0.5", "fills": [{"qty": "0.1"}]}
    val = core.UltimateAIAutoTrader._extract_filled_quantity(None, resp, 0.0)
    assert pytest.approx(val, rel=1e-6) == 0.5


def test_extract_filled_quantity_sums_fills_when_no_executed():
    resp = {"fills": [{"qty": "0.2"}, {"qty": "0.3"}]}
    val = core.UltimateAIAutoTrader._extract_filled_quantity(None, resp, 0.0)
    assert pytest.approx(val, rel=1e-6) == 0.5


def test_calculate_quote_spent_uses_cumulative_quote_qty():
    resp = {"cummulativeQuoteQty": "12.34", "fills": [{"price": "10", "qty": "1"}]}
    val = core.UltimateAIAutoTrader._calculate_quote_spent(None, resp, 1.0, 0)
    assert pytest.approx(val, rel=1e-6) == 12.34


def test_calculate_quote_spent_sums_fill_price_qty():
    resp = {"fills": [{"price": "2.5", "qty": "2"}, {"price": "3", "qty": "1"}]}
    val = core.UltimateAIAutoTrader._calculate_quote_spent(None, resp, 3.0, 0)
    assert pytest.approx(val, rel=1e-6) == (2.5 * 2 + 3 * 1)


def test_extract_commissions_aggregates_by_asset():
    resp = {"fills": [
        {"commission": "0.001", "commissionAsset": "USDT"},
        {"commission": "0.002", "commissionAsset": "USDT"},
        {"commission": "0.0001", "commissionAsset": "BTC"},
    ]}
    comm = core.UltimateAIAutoTrader._extract_commissions(None, resp)
    assert comm.get("USDT") == pytest.approx(0.001 + 0.002, rel=1e-9)
    assert comm.get("BTC") == pytest.approx(0.0001, rel=1e-9)


def test_get_portfolio_summary_reflects_positions_and_balance():
    # Build a minimal fake 'self' with the attributes used by get_portfolio_summary
    fake = types.SimpleNamespace()
    fake.positions = {
        "FOOUSDT": {
            "quantity": 2.0,
            "avg_price": 10.0,
            "entry_time": "2020-01-01T00:00:00",
        }
    }
    fake.balance = 100.0
    fake.initial_balance = 50.0
    fake.trade_history = types.SimpleNamespace(get_trade_history=lambda: [])
    # Minimal placeholders used by the method
    fake.bot_efficiency = {
        "total_trades": 0,
        "successful_trades": 0,
        "total_profit": 0,
        "learning_cycles": 0,
        "last_improvement": None,
    }
    fake.risk_manager = types.SimpleNamespace(
        get_risk_multiplier=lambda: 1.0, market_stress_indicator=0.0, current_risk_profile="default"
    )
    fake.ensemble_system = types.SimpleNamespace(market_regime="neutral")
    fake.max_drawdown = 0
    fake.trading_enabled = True
    # Minimal helper used by get_portfolio_summary
    fake.calculate_portfolio_health = lambda: 1.0
    fake._get_real_account_snapshot = lambda prices: None

    # Call method with current price for FOOUSDT
    summary = core.UltimateAIAutoTrader.get_portfolio_summary(fake, {"FOOUSDT": 12.0})
    # invested = 2 * 10 = 20; current = 2 * 12 = 24; paper_total_value = balance + current = 124
    assert summary["total_invested"] == pytest.approx(20)
    assert summary["total_current_value"] == pytest.approx(24)
    assert summary["paper_total_value"] == pytest.approx(124)
