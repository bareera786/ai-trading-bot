"""Sample trading bot strategy module.

This module provides two simple functions used by the tests:
- `calculate_risk(account_balance, position_size)` returns risk as a percentage
- `generate_signal(price_history)` returns a trade signal: BUY/SELL/HOLD

This is intentionally simple and easy to extend. The CI/AI workflow will
analyze test failures and suggest fixes when tests break.
"""

from typing import List, Iterable


def calculate_risk(account_balance: float, position_size: float) -> float:
    """Calculate risk as percent of account balance.

    Returns (position_size / account_balance) * 100
    """
    if account_balance <= 0:
        raise ValueError("account_balance must be > 0")
    return (position_size / account_balance) * 100


def generate_signal(a, b=None, c=None) -> str:
    """Generate a simple momentum signal.

    Accepts either a single iterable `a` of prices, or three numeric args
    (`a=short_sma, b=long_sma, c=price`). For the iterable form, behavior is:
    - If last price > first price: BUY
    - If last price < first price: SELL
    - Otherwise: HOLD

    This keeps the function compatible with tests that import both
    `bot.strategy` and `trading_bot.strategy`.
    """
    # Single iterable provided
    if b is None and c is None:
        prices = a
        if not isinstance(prices, Iterable) or not prices:
            return "HOLD"
        first, last = prices[0], prices[-1]
        if last > first:
            return "BUY"
        if last < first:
            return "SELL"
        return "HOLD"

    # Three numeric args (short_sma, long_sma, price)
    try:
        s = float(a)
        l = float(b)
    except Exception:
        return "HOLD"
    if s > l:
        return "BUY"
    if s < l:
        return "SELL"
    return "HOLD"
