import importlib
import math
import sys

import pytest


@pytest.fixture(scope="session")
def ai_module():
    """Import ai_ml_auto_bot_final without registering shutdown hooks."""

    import atexit

    mp = pytest.MonkeyPatch()
    mp.setattr(atexit, "register", lambda *args, **kwargs: None)
    sys.modules.pop("ai_ml_auto_bot_final", None)
    module = importlib.import_module("ai_ml_auto_bot_final")
    yield module
    mp.undo()


def _make_trader(ai_module):
    trader = ai_module.UltimateAIAutoTrader()
    # Minimal config to keep the decision path deterministic for the test.
    trader.trading_config = {
        "max_positions": 50,
        "confidence_threshold": 0.10,
        "min_confidence_diff": 0.0,
        "dynamic_threshold_floor": 0.0,
        "dynamic_threshold_ceiling": 1.0,
        "use_ensemble": True,
        "ensemble_min_agreement": 0.0,
        "ensemble_confidence_max_jump": 0.35,
    }
    return trader


def _call_should_trade(trader, ensemble_confidence):
    ensemble_signal = {
        "signal": "BUY",
        "confidence": ensemble_confidence,
        "buy_ratio": 1.0,
        "weighted_consensus": 0.2,
    }
    dashboard_copy = ensemble_signal  # simulate dashboard holding same dict reference
    before = dict(dashboard_copy)

    should_trade, reason = trader.should_execute_ultimate_trade(
        "BTCUSDT",
        ml_predictions={"m": {"signal": "BUY", "confidence": 0.9}},
        technical_signals=[],
        current_positions={},
        market_regime="NEUTRAL",
        ensemble_signal=ensemble_signal,
        market_stress=0.0,
        market_data=None,
        historical_prices=None,
    )

    assert dict(dashboard_copy) == before, "Input ensemble_signal dict must not be mutated"
    assert isinstance(should_trade, bool)
    assert isinstance(reason, str)
    return getattr(trader, "_last_ensemble_confidence", None)


def test_multiuser_confidence_smoothing_is_user_scoped_and_non_mutating(ai_module):
    trader_a = _make_trader(ai_module)
    trader_b = _make_trader(ai_module)

    assert getattr(trader_a, "_last_ensemble_confidence", None) is None
    assert getattr(trader_b, "_last_ensemble_confidence", None) is None

    # User A: establish baseline then apply an extreme jump.
    a1 = _call_should_trade(trader_a, 0.10)
    a2 = _call_should_trade(trader_a, 0.95)

    # User B: independent baseline + jump in opposite direction.
    b1 = _call_should_trade(trader_b, 0.90)
    b2 = _call_should_trade(trader_b, 0.05)

    # Ensure each trader keeps its own state.
    assert a1 != b1
    assert a2 != b2

    # Ensure the stabilizer rate-limits extreme single-tick jumps.
    assert pytest.approx(a1, abs=1e-9) == 0.10
    assert a2 <= 0.10 + trader_a.trading_config["ensemble_confidence_max_jump"] + 1e-9
    assert pytest.approx(b1, abs=1e-9) == 0.90
    assert b2 >= 0.90 - trader_b.trading_config["ensemble_confidence_max_jump"] - 1e-9


def test_ensemble_confidence_nonfinite_falls_back_per_trader(ai_module):
    trader = _make_trader(ai_module)

    baseline = _call_should_trade(trader, 0.62)
    assert pytest.approx(baseline, abs=1e-9) == 0.62

    after_nan = _call_should_trade(trader, float("nan"))
    assert math.isfinite(after_nan)
    assert pytest.approx(after_nan, abs=1e-9) == 0.62

    after_bad = _call_should_trade(trader, "not-a-number")
    assert math.isfinite(after_bad)
    assert pytest.approx(after_bad, abs=1e-9) == 0.62
