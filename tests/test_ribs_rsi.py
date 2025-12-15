import pytest

pytest.importorskip("flask_mail")

import numpy as np
import pandas as pd
from app.services.ribs_optimizer import TradingRIBSOptimizer


def make_prices(n=30):
    # simple increasing price series
    return pd.Series([100 + i for i in range(n)])


def test_calculate_rsi_handles_invalid_periods():
    r = TradingRIBSOptimizer
    prices = make_prices(30)

    # valid integer
    s1 = r().calculate_rsi(prices, period=14)
    assert isinstance(s1, pd.Series)
    assert len(s1) == len(prices)

    # float period
    s2 = r().calculate_rsi(prices, period=14.0)
    assert isinstance(s2, pd.Series)

    # None -> fallback
    s3 = r().calculate_rsi(prices, period=None)
    assert isinstance(s3, pd.Series)

    # zero or negative -> fallback
    s4 = r().calculate_rsi(prices, period=0)
    assert isinstance(s4, pd.Series)

    # weird type (slice) -> fallback, should not raise
    s5 = r().calculate_rsi(prices, period=slice(0, 10))
    assert isinstance(s5, pd.Series)

    # check values are in expected range or neutral
    for s in (s1, s2, s3, s4, s5):
        assert all(0 <= v <= 100 for v in s.fillna(50).tolist())


def test_calculate_rsi_does_not_log_errors_for_malformed_period(caplog):
    from app.services.ribs_optimizer import TradingRIBSOptimizer

    prices = make_prices(30)
    caplog.set_level("WARNING")

    r = TradingRIBSOptimizer()
    # pass a malformed period (slice) which previously triggered error-level logs
    _ = r.calculate_rsi(prices, period=slice(0, 10))

    # No ERROR level logs mentioning RSI should be present
    assert not any(
        rec.levelname == "ERROR" and "RSI" in rec.message for rec in caplog.records
    )
