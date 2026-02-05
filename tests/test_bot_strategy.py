"""Pytest tests for the example `bot.strategy` module.

These tests are intentionally small and demonstrate unit and regression
test execution in CI.
"""
from bot.strategy import calculate_risk, generate_signal
import pytest


def test_calculate_risk_basic():
    assert calculate_risk(1000.0, 50.0) == pytest.approx(5.0)


def test_calculate_risk_invalid_balance():
    with pytest.raises(ValueError):
        calculate_risk(0.0, 10.0)


def test_generate_signal_buy():
    assert generate_signal([100.0, 110.0, 120.0]) == "BUY"


def test_generate_signal_sell():
    assert generate_signal([120.0, 115.0, 110.0]) == "SELL"
