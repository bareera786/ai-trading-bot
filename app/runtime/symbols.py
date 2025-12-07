"""Trading-universe defaults and symbol state management for the runtime."""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from threading import Lock
from typing import Any, Callable, Iterable, MutableMapping, Sequence

from app.services.pathing import PROJECT_ROOT, resolve_profile_path

DashboardAccessor = Callable[[], MutableMapping[str, Any]]

DEFAULT_TOP_SYMBOLS: Sequence[str] = (
	'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
	'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'MATICUSDT',
	'LINKUSDT', 'LTCUSDT', 'BCHUSDT', 'XLMUSDT', 'ETCUSDT',
)

DEFAULT_FUTURES_SYMBOLS: Sequence[str] = (
	'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
	'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT',
)

DEFAULT_MARKET_CAP_WEIGHTS: dict[str, float] = {
	'BTCUSDT': 1.0,
	'ETHUSDT': 0.9,
	'BNBUSDT': 0.8,
	'ADAUSDT': 0.7,
	'XRPUSDT': 0.7,
	'SOLUSDT': 0.8,
	'DOTUSDT': 0.7,
	'DOGEUSDT': 0.6,
	'AVAXUSDT': 0.7,
	'MATICUSDT': 0.7,
	'LINKUSDT': 0.7,
	'LTCUSDT': 0.6,
	'BCHUSDT': 0.6,
	'XLMUSDT': 0.5,
	'ETCUSDT': 0.5,
}

DEFAULT_HEALTH_SYMBOLS: Sequence[str] = (
	'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT',
	'XRPUSDT', 'DOTUSDT', 'DOGEUSDT', 'MATICUSDT', 'AVAXUSDT',
)

DEFAULT_DISABLED_SYMBOLS: Sequence[str] = (
	'DOTUSDT', 'AVAXUSDT',
)


def parse_symbol_env(value: Any, fallback: Sequence[str]) -> list[str]:
	"""Parse a comma/space separated symbol string into normalized tickers."""

	if not value:
		return [item for item in fallback]
	if isinstance(value, (list, tuple, set)):
		raw_values = value
	else:
		raw_values = str(value).replace(',', ' ').split()
	normalized = []
	for item in raw_values:
		if isinstance(item, str):
			symbol = item.strip().upper()
			if symbol:
				normalized.append(symbol)
	return normalized or [item for item in fallback]


TOP_SYMBOLS: list[str] = list(DEFAULT_TOP_SYMBOLS)
FUTURES_SYMBOLS: list[str] = list(DEFAULT_FUTURES_SYMBOLS)
MARKET_CAP_WEIGHTS: dict[str, float] = dict(DEFAULT_MARKET_CAP_WEIGHTS)
DISABLED_SYMBOLS: set[str] = set(DEFAULT_DISABLED_SYMBOLS)

SYMBOL_STATE_LOCK = Lock()
_dashboard_accessor: DashboardAccessor | None = None


def attach_dashboard_accessor(accessor: DashboardAccessor) -> None:
	"""Register a callable that returns the live dashboard data mapping."""

	global _dashboard_accessor  # noqa: PLW0603  # module-level shared state
	_dashboard_accessor = accessor


def attach_dashboard_data(dashboard_data: MutableMapping[str, Any]) -> None:
	"""Register a static dashboard mapping as the refresh target."""

	attach_dashboard_accessor(lambda: dashboard_data)


def _get_dashboard_data() -> MutableMapping[str, Any] | None:
	if _dashboard_accessor is None:
		return None
	try:
		return _dashboard_accessor()
	except Exception:
		return None


def _symbol_state_path() -> str:
	try:
		config_dir = resolve_profile_path('config')
	except Exception:
		config_dir = os.path.join(PROJECT_ROOT, 'config')
		os.makedirs(config_dir, exist_ok=True)
	return os.path.join(config_dir, 'symbol_state.json')


def normalize_symbol(symbol: Any) -> str:
	if not symbol:
		return ''
	normalized = str(symbol).strip().upper()
	if normalized and not normalized.endswith('USDT'):
		normalized = f"{normalized}USDT"
	return normalized


def load_symbol_state() -> set[str]:
	"""Load disabled symbol state from persistent storage."""

	global DISABLED_SYMBOLS  # noqa: PLW0603  # module-level shared state

	path = _symbol_state_path()
	disabled: set[str] = set()

	if os.path.exists(path):
		try:
			with open(path, 'r', encoding='utf-8') as file_obj:
				payload = json.load(file_obj)
			raw_disabled = payload.get('disabled_symbols', [])
			if isinstance(raw_disabled, list):
				disabled = {normalize_symbol(sym) for sym in raw_disabled if isinstance(sym, str)}
		except Exception:
			disabled = set()

	with SYMBOL_STATE_LOCK:
		DISABLED_SYMBOLS = {sym for sym in disabled if sym}
		for symbol in list(TOP_SYMBOLS):
			if symbol in DISABLED_SYMBOLS:
				TOP_SYMBOLS.remove(symbol)

	refresh_symbol_counters()
	return DISABLED_SYMBOLS


def save_symbol_state() -> None:
	path = _symbol_state_path()
	with SYMBOL_STATE_LOCK:
		payload = {
			'disabled_symbols': sorted(DISABLED_SYMBOLS),
			'updated_at': datetime.utcnow().isoformat(),
		}

	fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(path), prefix='symbols_', suffix='.json')
	try:
		with os.fdopen(fd, 'w', encoding='utf-8') as temp_file:
			json.dump(payload, temp_file, indent=2)
		os.replace(temp_path, path)
	except Exception:
		try:
			os.unlink(temp_path)
		except OSError:
			pass
		raise


def get_disabled_symbols() -> list[str]:
	with SYMBOL_STATE_LOCK:
		return sorted(DISABLED_SYMBOLS)


def get_enabled_symbols() -> list[str]:
	with SYMBOL_STATE_LOCK:
		return [sym for sym in TOP_SYMBOLS if sym not in DISABLED_SYMBOLS]


def get_all_known_symbols() -> list[str]:
	with SYMBOL_STATE_LOCK:
		return sorted(set(TOP_SYMBOLS) | DISABLED_SYMBOLS)


def get_active_trading_universe() -> list[str]:
	with SYMBOL_STATE_LOCK:
		return [sym for sym in TOP_SYMBOLS if sym not in DISABLED_SYMBOLS]


def refresh_symbol_counters() -> None:
	dashboard_data = _get_dashboard_data()
	if not dashboard_data:
		return
	try:
		active = len(get_active_trading_universe())
		total = len(get_all_known_symbols())
		system_status = dashboard_data.setdefault('system_status', {})
		if isinstance(system_status, MutableMapping):
			system_status['active_symbols'] = active
			system_status['total_symbols'] = total
	except Exception:
		pass


def clear_symbol_from_dashboard(symbol: str) -> None:
	dashboard_data = _get_dashboard_data()
	if not dashboard_data:
		return

	normalized = normalize_symbol(symbol)
	if not normalized:
		return

	try:
		for key in [
			'market_data',
			'ml_predictions',
			'ai_signals',
			'crt_signals',
			'optimized_ml_predictions',
			'optimized_ai_signals',
			'optimized_crt_signals',
			'ensemble_predictions',
			'optimized_ensemble_predictions',
		]:
			mapping = dashboard_data.get(key)
			if isinstance(mapping, MutableMapping):
				mapping.pop(normalized, None)

		for portfolio_key in ['portfolio', 'optimized_portfolio']:
			portfolio = dashboard_data.get(portfolio_key)
			positions = portfolio.get('positions') if isinstance(portfolio, MutableMapping) else None
			if isinstance(positions, list):
				portfolio['positions'] = [pos for pos in positions if pos.get('symbol') != normalized]

		trending = dashboard_data.get('trending_pairs')
		if isinstance(trending, list):
			dashboard_data['trending_pairs'] = [pair for pair in trending if pair != normalized]
	except Exception:
		pass


def is_symbol_disabled(symbol: Any) -> bool:
	normalized = normalize_symbol(symbol)
	if not normalized:
		return False
	with SYMBOL_STATE_LOCK:
		return normalized in DISABLED_SYMBOLS


def disable_symbol(symbol: Any) -> bool:
	normalized = normalize_symbol(symbol)
	if not normalized:
		return False

	changed = False
	with SYMBOL_STATE_LOCK:
		if normalized in TOP_SYMBOLS:
			try:
				TOP_SYMBOLS.remove(normalized)
				changed = True
			except ValueError:
				pass
		if normalized not in DISABLED_SYMBOLS:
			DISABLED_SYMBOLS.add(normalized)
			changed = True

	if changed:
		save_symbol_state()
		refresh_symbol_counters()
		clear_symbol_from_dashboard(normalized)
	return changed


def enable_symbol(symbol: Any, *, ensure_listed: bool = True) -> bool:
	normalized = normalize_symbol(symbol)
	if not normalized:
		return False

	changed = False
	with SYMBOL_STATE_LOCK:
		if normalized in DISABLED_SYMBOLS:
			DISABLED_SYMBOLS.remove(normalized)
			changed = True
		if ensure_listed and normalized not in TOP_SYMBOLS:
			TOP_SYMBOLS.append(normalized)
			changed = True

	if changed:
		save_symbol_state()
		refresh_symbol_counters()
	return changed


# Load persisted symbol state on module import for immediate availability.
load_symbol_state()

__all__ = [
	'DEFAULT_TOP_SYMBOLS',
	'DEFAULT_FUTURES_SYMBOLS',
	'DEFAULT_MARKET_CAP_WEIGHTS',
	'DEFAULT_HEALTH_SYMBOLS',
	'DEFAULT_DISABLED_SYMBOLS',
	'DISABLED_SYMBOLS',
	'FUTURES_SYMBOLS',
	'MARKET_CAP_WEIGHTS',
	'SYMBOL_STATE_LOCK',
	'TOP_SYMBOLS',
	'attach_dashboard_accessor',
	'attach_dashboard_data',
	'clear_symbol_from_dashboard',
	'disable_symbol',
	'enable_symbol',
	'get_active_trading_universe',
	'get_all_known_symbols',
	'get_disabled_symbols',
	'get_enabled_symbols',
	'is_symbol_disabled',
	'load_symbol_state',
	'normalize_symbol',
	'parse_symbol_env',
	'refresh_symbol_counters',
	'save_symbol_state',
]

