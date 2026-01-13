"""Pytest tests for the `bot.strategy` module.

These tests exercise the small example functions and are used by the CI to
demonstrate the AI-assisted self-healing flow when failures occur.
"""
from bot.strategy import calculate_risk, generate_signal
import pytest


def test_calculate_risk_normal():
    # 100 capital, 2% risk -> position size = 2.0 -> risk% = 2.0
    result = calculate_risk(100.0, 2.0)
    assert pytest.approx(result, rel=1e-6) == 2.0


def test_calculate_risk_invalid():
    # capital must be positive
    with pytest.raises(ValueError):
        calculate_risk(0.0, 1.0)


def test_generate_signal_buy():
    # short SMA above long SMA -> BUY
    assert generate_signal(105.0, 106.0, 100.0) == "BUY"


def test_generate_signal_sell():
    # short SMA below long SMA -> SELL
    assert generate_signal(95.0, 90.0, 100.0) == "SELL"


def test_generate_signal_hold():
    # no signal when SMAs equal
    assert generate_signal(100.0, 100.0, 100.0) == "HOLD"
"""Unit tests for `trading_bot.strategy`.

Includes one failing test to demonstrate how the AI agent reacts.
"""
import pytest

from trading_bot.strategy import calculate_risk, generate_signal


def test_calculate_risk():
    # 50 / 1000 = 0.05 -> 5.0%
    assert calculate_risk(1000.0, 50.0) == pytest.approx(5.0)


def test_generate_signal_buy():
    # price rises -> BUY
    assert generate_signal([100.0, 110.0]) == "BUY"


def test_generate_signal_sell():
    # price falls -> SELL (this test will fail if generate_signal is incorrect)
    assert generate_signal([120.0, 110.0]) == "SELL"
