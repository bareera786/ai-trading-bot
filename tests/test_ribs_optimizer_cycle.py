import pytest

pytest.importorskip("flask_mail")

import pandas as pd
import numpy as np

from app.services.ribs_optimizer import TradingRIBSOptimizer


def make_ohlcv(n=100):
    # Create a simple increasing close price series with OHLCV columns
    closes = [100 + i * 0.1 for i in range(n)]
    df = pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.05 for c in closes],
            "low": [c - 0.05 for c in closes],
            "close": closes,
            "volume": [1000 + i for i in range(n)],
        }
    )
    return {"ohlcv": df}


def test_ribs_run_optimization_cycle_short():
    optimizer = TradingRIBSOptimizer()
    market_data = make_ohlcv(120)

    # Run a tiny optimization cycle (iterations small so it runs quickly)
    elites = optimizer.run_optimization_cycle(market_data, iterations=2)

    # Should return a list (possibly empty) and not raise
    assert isinstance(elites, list)
