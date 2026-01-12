"""
Minimal strategy helpers used by tests.

This file provides two small functions expected by the unit
tests: `calculate_risk` and `generate_signal`.

Rules (minimal, safe):
- `calculate_risk(capital, risk)` returns the risk as a percentage
  computed by (risk / capital) * 100. Raises ValueError for non-positive capital.
- `generate_signal(...)` accepts either:
  - a single list/iterable of prices -> returns "BUY" if prices rise, "SELL" if fall, "HOLD" otherwise
  - three numeric args (short_sma, long_sma, price) -> returns "BUY" if short_sma>long_sma,
	"SELL" if short_sma<long_sma, else "HOLD".

Keep this file minimal and do not change other codepaths.
"""

from typing import Iterable, Union


def calculate_risk(capital: float, risk: float) -> float:
	"""Return the risk expressed as percentage.

	Examples:
	- calculate_risk(1000.0, 50.0) -> 5.0
	- calculate_risk(100.0, 2.0) -> 2.0
	"""
	try:
		capital = float(capital)
		risk = float(risk)
	except Exception:
		raise ValueError("Invalid numeric inputs for calculate_risk")
	if capital <= 0:
		raise ValueError("capital must be positive")
	return (risk / capital) * 100.0


def generate_signal(a, b=None, c=None) -> str:
	"""Generate a simple BUY/SELL/HOLD signal.

	This function accepts either:
	- a single iterable of prices as the first argument (`a`), or
	- three numeric positional arguments (`a=short_sma, b=long_sma, c=price`).

	The behavior matches the minimal expectations of the unit tests.
	"""
	# Single iterable argument provided
	if b is None and c is None:
		prices = a
		if not isinstance(prices, Iterable):
			return "HOLD"
		prices_list = list(prices)
		if len(prices_list) < 2:
			return "HOLD"
		if prices_list[-1] > prices_list[0]:
			return "BUY"
		if prices_list[-1] < prices_list[0]:
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
