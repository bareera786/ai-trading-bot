import numpy as np
from app.services.ribs_optimizer import TradingRIBSOptimizer


def test_decode_solution_sanitizes_values():
    opt = TradingRIBSOptimizer()
    # Build a pathological solution vector with extreme values that would
    # produce negative/invalid take_profit or tiny position sizes
    sol = np.array([10.0, 10.0, -10.0, 10.0, 10.0, 100.0, -10.0, -10.0, -10.0, -10.0])
    params = opt.decode_solution(sol)

    # All relevant numeric params should be within sensible ranges
    assert params["take_profit"] >= 0.1
    assert params["stop_loss"] >= 0.1
    assert 0.001 <= params["position_size"] <= 1.0
    assert params["max_positions"] >= 1
    assert params["risk_multiplier"] >= 0.01
