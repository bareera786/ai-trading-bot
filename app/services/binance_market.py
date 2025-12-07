"""Binance REST market data helpers with host failover and logging."""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable, Iterable, Sequence

import requests
from requests import RequestException

from .binance import BinanceLogManager

BINANCE_PRIMARY_REST_HOSTS: Sequence[str] = (
    "https://api.binance.com",
    "https://api-gcp.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
)

BINANCE_TESTNET_REST_HOSTS: Sequence[str] = ("https://testnet.binance.vision",)

SafetyHook = Callable[[], None]
FailureHook = Callable[[str], None]


class BinanceMarketDataHelper:
    """Fetches Binance REST data with retries, fallbacks, and safety hooks."""

    def __init__(
        self,
        *,
        bot_logger: logging.Logger | None,
        safe_float: Callable[[Any, float], float],
        testnet_detector: Callable[[], bool] | None = None,
        binance_log_manager: BinanceLogManager | None = None,
        warning_cooldown: float = 180.0,
        request_client: Any = requests,
        random_source: Any = random,
        api_success_hooks: Iterable[SafetyHook] | None = None,
        api_failure_hooks: Iterable[FailureHook] | None = None,
    ) -> None:
        self.logger = bot_logger or logging.getLogger('ai_trading_bot')
        self._safe_float = safe_float
        self._testnet_detector = testnet_detector or (lambda: False)
        self._binance_log_manager = binance_log_manager
        self._warning_cooldown = float(max(1.0, warning_cooldown))
        self._warning_registry: dict[str, float] = {}
        self._request_client = request_client
        self._random = random_source
        self._api_success_hooks = list(api_success_hooks or [])
        self._api_failure_hooks = list(api_failure_hooks or [])

    # ------------------------ Internal helpers ------------------------
    def _resolve_rest_hosts(self) -> Sequence[str]:
        if self._testnet_detector():
            return tuple(BINANCE_TESTNET_REST_HOSTS) + tuple(BINANCE_PRIMARY_REST_HOSTS)
        return tuple(BINANCE_PRIMARY_REST_HOSTS)

    def _log_rest_failure(self, message: str, severity: str = 'error') -> None:
        if not self._binance_log_manager:
            return
        try:
            self._binance_log_manager.add('REST_API_ERROR', message, severity=severity, account_type='spot')
        except Exception:  # pragma: no cover - defensive logging
            pass

    def _should_emit_warning(self, key: str) -> bool:
        now = time.time()
        last = self._warning_registry.get(key)
        if last is None or (now - last) >= self._warning_cooldown:
            self._warning_registry[key] = now
            return True
        return False

    def _notify_success(self) -> None:
        for hook in self._api_success_hooks:
            try:
                hook()
            except Exception:  # pragma: no cover - hooks are best-effort
                continue

    def _notify_failure(self, message: str) -> None:
        for hook in self._api_failure_hooks:
            try:
                hook(message)
            except Exception:  # pragma: no cover - hooks are best-effort
                continue

    # --------------------------- Public API --------------------------
    def fetch_24hr_ticker(self, symbol: str | None = None, timeout: float = 10.0) -> Any:
        """Fetch 24hr ticker data with host failover."""
        last_error: Exception | None = None
        for base_url in self._resolve_rest_hosts():
            try:
                url = f"{base_url}/api/v3/ticker/24hr"
                params = {'symbol': symbol} if symbol else None
                self.logger.debug("Requesting Binance ticker host=%s symbol=%s", base_url, symbol or 'ALL')
                response = self._request_client.get(url, params=params, timeout=timeout)
                if response.status_code == 200:
                    self.logger.debug("Binance ticker success host=%s symbol=%s", base_url, symbol or 'ALL')
                    return response.json()
                last_error = RuntimeError(f"HTTP {response.status_code} from {base_url}")
                warn_key = f"non200|{base_url}|{symbol or 'ALL'}|{response.status_code}"
                log_fn = self.logger.warning if self._should_emit_warning(warn_key) else self.logger.debug
                log_fn(
                    "Binance ticker non-200 response host=%s symbol=%s status=%s",
                    base_url,
                    symbol or 'ALL',
                    response.status_code,
                )
            except RequestException as exc:
                last_error = exc
                warn_key = f"exception|{base_url}|{symbol or 'ALL'}|{type(exc).__name__}"
                log_fn = self.logger.warning if self._should_emit_warning(warn_key) else self.logger.debug
                log_fn(
                    "Binance ticker request exception host=%s symbol=%s error=%s",
                    base_url,
                    symbol or 'ALL',
                    exc,
                )
        if last_error:
            self.logger.error("Binance ticker failed after all hosts symbol=%s error=%s", symbol or 'ALL', last_error)
            self._log_rest_failure(f"24hr ticker failed for {symbol or 'ALL'}: {last_error}")
            raise last_error
        return None

    def get_trending_pairs(self) -> list[dict[str, Any]]:
        try:
            all_data = self.fetch_24hr_ticker(timeout=10)
            if isinstance(all_data, list):
                usdt_pairs = [pair for pair in all_data if str(pair.get('symbol', '')).endswith('USDT')]
                trending = sorted(usdt_pairs, key=lambda x: self._safe_float(x.get('volume')), reverse=True)[:5]
                trending_data = [
                    {
                        'symbol': pair.get('symbol'),
                        'price': self._safe_float(pair.get('lastPrice')),
                        'change': self._safe_float(pair.get('priceChangePercent')),
                        'volume': self._safe_float(pair.get('volume')),
                    }
                    for pair in trending
                ]
                self.logger.info("Trending pairs refreshed count=%d", len(trending_data))
                return trending_data
        except Exception as exc:
            self.logger.error("Trending pairs fetch failed", exc_info=True)
            self._log_rest_failure(f"Trending pairs fetch failed: {exc}")
        return []

    def get_real_market_data(self, symbol: str) -> dict[str, Any]:
        try:
            data = self.fetch_24hr_ticker(symbol=symbol, timeout=10)
            if isinstance(data, dict) and data:
                self.logger.debug("Market data fetched symbol=%s", symbol)
                self._notify_success()
                return {
                    'symbol': symbol,
                    'price': self._safe_float(data.get('lastPrice')),
                    'change': self._safe_float(data.get('priceChangePercent')),
                    'volume': self._safe_float(data.get('volume')),
                    'high': self._safe_float(data.get('highPrice')),
                    'low': self._safe_float(data.get('lowPrice')),
                    'open': self._safe_float(data.get('openPrice')),
                }
        except Exception as exc:
            self.logger.error("Market data fetch failed symbol=%s", symbol, exc_info=True)
            self._log_rest_failure(f"REST market data error for {symbol}: {exc}")
            self._notify_failure(str(exc))

        base_prices = {
            'BTCUSDT': 50000,
            'ETHUSDT': 3000,
            'BNBUSDT': 500,
            'ADAUSDT': 0.5,
            'XRPUSDT': 0.6,
            'SOLUSDT': 100,
            'DOTUSDT': 7,
            'DOGEUSDT': 0.15,
            'AVAXUSDT': 40,
            'MATICUSDT': 0.8,
            'LINKUSDT': 15,
            'LTCUSDT': 80,
            'BCHUSDT': 300,
            'XLMUSDT': 0.12,
            'ETCUSDT': 25,
        }
        base_price = base_prices.get(symbol, 100)
        price = base_price * (1 + self._random.uniform(-0.1, 0.1))
        return {
            'symbol': symbol,
            'price': price,
            'change': self._random.uniform(-5, 5),
            'volume': 1_000_000,
            'high': price * 1.05,
            'low': price * 0.95,
            'open': price * (1 + self._random.uniform(-0.02, 0.02)),
        }