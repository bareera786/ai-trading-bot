"""Trading service orchestration helpers."""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Union

import redis

from .binance import _coerce_bool
from .ml import MLServiceBundle


class CircuitBreaker:
    """Circuit breaker pattern implementation for trading operations."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,  # 5 minutes
        expected_exception: tuple = (Exception,),
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return datetime.now() - self.last_failure_time > timedelta(
            seconds=self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful operation."""
        with self._lock:
            self.failure_count = 0
            self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"

    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is open."""
        return self.state == "OPEN"


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""



class RealBinanceTrader:
    """Wrapper around python-binance client with safe defaults and journaling hooks."""

    TESTNET_API_URL = "https://testnet.binance.vision/api"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        *,
        testnet: bool = True,
        order_history_limit: int = 50,
        account_type: str = "spot",
        binance_client_cls: Optional[type] = None,
        api_exception_cls: Optional[Union[type, tuple[type, ...]]] = None,
        binance_log_manager: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
        coerce_bool: Optional[Callable[[Any, bool], bool]] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.private_key_path = os.getenv("BINANCE_PRIVATE_KEY_PATH")
        self.private_key_pass = os.getenv("BINANCE_PRIVATE_KEY_PASS")
        self.use_rsa = bool(self.private_key_path)
        self._coerce_bool = coerce_bool or _coerce_bool
        self.testnet = self._coerce_bool(testnet, default=True)
        self.client = None
        self.connected = False
        self.last_error = None
        self.account_status = {}
        self.order_history = deque(maxlen=order_history_limit)
        self._client_lock = threading.Lock()
        self.symbol_filters = {}
        self.min_notional_cache = {}
        self.price_tick_cache = {}
        self.binance_client_cls = binance_client_cls
        self.api_exception_cls = api_exception_cls or Exception
        account_label = str(account_type or "spot").strip().lower()
        self.account_type = (
            account_label if account_label in ("spot", "futures") else "spot"
        )
        self.binance_log_manager = binance_log_manager
        self.logger = logger or logging.getLogger("ai_trading_bot")
        self.redis_client = redis.Redis(
            host="localhost", port=6379, decode_responses=True
        )

        # Circuit breaker for trading operations
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,  # Open after 5 failures
            recovery_timeout=300,  # Try again after 5 minutes
            expected_exception=self.api_exception_cls,
        )

        if self.api_key and self.api_secret:
            self.connect()

    def _log_event(self, event_type, message, severity="info", details=None):
        if not self.binance_log_manager:
            return
        try:
            payload = {"testnet": self.testnet}
            if isinstance(details, dict):
                payload.update(details)
            elif details is not None:
                payload["details"] = details
            self.binance_log_manager.add(
                event_type,
                message,
                severity=severity,
                account_type=self.account_type,
                details=payload,
            )
        except Exception:
            pass

    def connect(self):
        """Create a Binance client session."""
        if not self.binance_client_cls:
            self.last_error = "python-binance package not installed"
            self.connected = False
            self._log_event("CONNECT", self.last_error, severity="error")
            self.logger.error(
                "Binance connect failed - library missing account_type=%s",
                self.account_type,
            )
            return False

        if not self.api_key or (not self.api_secret and not self.private_key_path):
            self.last_error = "Missing Binance API credentials"
            self.connected = False
            self._log_event("CONNECT", self.last_error, severity="error")
            self.logger.error(
                "Binance connect failed - missing credentials account_type=%s",
                self.account_type,
            )
            return False

        try:
            self.logger.info(
                "Connecting to Binance account_type=%s testnet=%s",
                self.account_type,
                self.testnet,
            )
            with self._client_lock:
                if self.use_rsa:
                    # If a filesystem path was provided, pass a Path object so
                    # the underlying binance client will open the file instead
                    # of treating the string as key material.
                    try:
                        from pathlib import Path

                        pk_arg = (
                            Path(self.private_key_path)
                            if self.private_key_path and Path(self.private_key_path).exists()
                            else self.private_key_path
                        )
                    except Exception:
                        pk_arg = self.private_key_path

                    self.client = self.binance_client_cls(
                        self.api_key,
                        private_key=pk_arg,
                        private_key_pass=self.private_key_pass,
                        testnet=self.testnet,
                    )
                else:
                    self.client = self.binance_client_cls(
                        self.api_key, self.api_secret, testnet=self.testnet
                    )
                if self.testnet:
                    self.client.API_URL = self.TESTNET_API_URL
                self.connected = True
                self.last_error = None
                self.symbol_filters.clear()
            self.refresh_account_status()
            self._log_event("CONNECT", "Connected to Binance API", severity="success")
            self.logger.info(
                "Binance connect successful account_type=%s testnet=%s",
                self.account_type,
                self.testnet,
            )
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self.connected = False
            self._log_event("CONNECT", self.last_error, severity="error")
            self.logger.exception(
                "Binance connect exception account_type=%s", self.account_type
            )
            return False

    def is_ready(self):
        return (
            self.connected
            and self.client is not None
            and not self.circuit_breaker.is_open
        )

    def get_circuit_breaker_status(self):
        """Get circuit breaker status for monitoring."""
        return {
            "state": self.circuit_breaker.state,
            "failure_count": self.circuit_breaker.failure_count,
            "last_failure_time": self.circuit_breaker.last_failure_time.isoformat()
            if self.circuit_breaker.last_failure_time
            else None,
            "is_open": self.circuit_breaker.is_open,
        }

    def set_credentials(self, api_key=None, api_secret=None, auto_connect=True):
        self.api_key = api_key or self.api_key
        self.api_secret = api_secret or self.api_secret
        self._log_event(
            "CREDENTIAL_UPDATE", "Updated API credentials in trader.", severity="info"
        )
        self.logger.info(
            "Binance credentials updated account_type=%s auto_connect=%s",
            self.account_type,
            auto_connect,
        )
        if auto_connect:
            return self.connect()
        return True

    def set_testnet(self, enabled=True):
        self.testnet = self._coerce_bool(enabled, default=self.testnet)
        self.logger.info(
            "Binance testnet toggled account_type=%s testnet=%s",
            self.account_type,
            self.testnet,
        )
        if self.client:
            self.connect()

    def refresh_account_status(self):
        if not self.is_ready():
            return None
        try:
            with self._client_lock:
                account = self.client.get_account()
            self.account_status = {
                "can_trade": account.get("canTrade", False),
                "balances": [
                    bal
                    for bal in account.get("balances", [])
                    if float(bal.get("free", 0)) > 0
                ],
                "update_time": datetime.utcnow().isoformat(),
            }
            self.logger.debug(
                "Account status refreshed account_type=%s balances=%d",
                self.account_type,
                len(self.account_status.get("balances", [])),
            )
            return self.account_status
        except Exception as exc:
            if isinstance(exc, self.api_exception_cls):
                self.last_error = str(exc)
                self._log_event(
                    "ACCOUNT_STATUS_ERROR", self.last_error, severity="error"
                )
                self.logger.warning(
                    "Account status error account_type=%s error=%s",
                    self.account_type,
                    exc,
                )
            else:
                self.last_error = str(exc)
                self._log_event(
                    "ACCOUNT_STATUS_ERROR", self.last_error, severity="error"
                )
                self.logger.exception(
                    "Account status exception account_type=%s", self.account_type
                )
        return None

    def sync_time(self):
        if not self.is_ready():
            return False
        try:
            with self._client_lock:
                server_time = self.client.get_server_time()
            self.logger.debug(
                "Synced Binance server time account_type=%s", self.account_type
            )
            return server_time
        except Exception as exc:
            self.last_error = str(exc)
            self._log_event("SYNC_TIME_ERROR", self.last_error, severity="error")
            self.logger.warning(
                "Sync time error account_type=%s error=%s", self.account_type, exc
            )
            return False

    def _get_symbol_filters(self, symbol):
        if not symbol:
            return []
        symbol_key = str(symbol).upper()
        cached = self.symbol_filters.get(symbol_key)
        if cached is not None:
            return cached

        if not self.is_ready():
            return []

        try:
            with self._client_lock:
                info = self.client.get_symbol_info(symbol_key)
            filters = info.get("filters", []) if isinstance(info, dict) else []
            self.symbol_filters[symbol_key] = filters
            return filters
        except Exception as exc:
            self.logger.warning(
                "Unable to fetch symbol filters symbol=%s error=%s", symbol_key, exc
            )
            self.symbol_filters[symbol_key] = []
            return []

    def _resolve_price(self, symbol, reference_price=None):
        try:
            if reference_price is not None and float(reference_price) > 0:
                return float(reference_price)
        except Exception:
            pass

        if not self.is_ready():
            return None

        try:
            with self._client_lock:
                ticker = self.client.get_symbol_ticker(symbol=str(symbol).upper())
            price = (
                float(ticker.get("price"))
                if isinstance(ticker, dict) and ticker.get("price")
                else None
            )
            return price
        except Exception as exc:
            self.logger.warning("Failed to resolve price for %s error=%s", symbol, exc)
            return None

    def get_min_notional(self, symbol):
        if not symbol:
            return None
        symbol_key = str(symbol).upper()
        if symbol_key in self.min_notional_cache:
            return self.min_notional_cache[symbol_key]

        filters = self._get_symbol_filters(symbol_key)
        min_notional = None
        for flt in filters:
            filter_type = flt.get("filterType")
            if filter_type in ("NOTIONAL", "MIN_NOTIONAL"):
                value = flt.get("minNotional") or flt.get("notional")
                if value is not None:
                    try:
                        min_notional = float(value)
                    except Exception:
                        min_notional = None
                break

        if min_notional is not None:
            self.min_notional_cache[symbol_key] = min_notional

        return min_notional

    def _normalize_order_quantity(self, symbol, quantity):
        try:
            filters = self._get_symbol_filters(symbol)
            lot_filter = next(
                (flt for flt in filters if flt.get("filterType") == "LOT_SIZE"), None
            )
            if not lot_filter:
                return float(quantity), None

            step_size = Decimal(str(lot_filter.get("stepSize", "0")))
            min_qty = Decimal(str(lot_filter.get("minQty", "0")))
            max_qty = Decimal(str(lot_filter.get("maxQty", "0")))

            qty = Decimal(str(quantity))
            original_qty = qty
            adjustment_note = None

            if step_size > 0:
                steps = (qty / step_size).to_integral_value(rounding=ROUND_DOWN)
                qty = steps * step_size
                if qty != original_qty:
                    adjustment_note = f"Adjusted to stepSize {step_size}"

            if max_qty > 0 and qty > max_qty:
                qty = max_qty
                adjustment_note = f"Clamped to maxQty {max_qty}"

            if qty <= 0:
                return None, "Quantity rounded down to zero"

            if qty < min_qty:
                return None, f"Quantity {qty} below minQty {min_qty}"

            return float(qty), adjustment_note
        except Exception as exc:
            self.logger.warning(
                "Failed to normalize quantity symbol=%s qty=%s error=%s",
                symbol,
                quantity,
                exc,
            )
            return float(quantity), None

    def get_price_tick_size(self, symbol):
        if not symbol:
            return None
        symbol_key = str(symbol).upper()
        cached = self.price_tick_cache.get(symbol_key)
        if cached is not None:
            return cached

        filters = self._get_symbol_filters(symbol_key)
        price_filter = next(
            (flt for flt in filters if flt.get("filterType") == "PRICE_FILTER"), None
        )
        tick_size = None
        if price_filter:
            tick_value = price_filter.get("tickSize")
            if tick_value is not None:
                try:
                    tick_size = float(tick_value)
                except Exception:
                    tick_size = None
        if tick_size is not None:
            self.price_tick_cache[symbol_key] = tick_size
        return tick_size

    def normalize_price(self, symbol, price):
        if price is None:
            return None
        tick_size = self.get_price_tick_size(symbol)
        if not tick_size:
            return float(price)
        try:
            tick = Decimal(str(tick_size))
            if tick <= 0:
                return float(price)
            price_dec = Decimal(str(price))
            steps = (price_dec / tick).to_integral_value(rounding=ROUND_DOWN)
            normalized = steps * tick
            return float(normalized)
        except Exception as exc:
            self.logger.warning(
                "Failed to normalize price symbol=%s price=%s error=%s",
                symbol,
                price,
                exc,
            )
            return float(price)

    def get_order_book(self, symbol, limit=5):
        if not self.is_ready():
            return None
        try:
            with self._client_lock:
                return self.client.get_order_book(
                    symbol=str(symbol).upper(), limit=limit
                )
        except Exception as exc:
            self.logger.warning(
                "Failed to fetch order book symbol=%s error=%s", symbol, exc
            )
            return None

    def place_limit_order(self, symbol, side, quantity, price, time_in_force="GTC"):
        normalized_price = self.normalize_price(symbol, price)
        return self.place_real_order(
            symbol,
            side,
            quantity,
            price=normalized_price,
            order_type="LIMIT",
            time_in_force=time_in_force,
        )

    def get_order(self, symbol, order_id=None, client_order_id=None):
        if not self.is_ready():
            return None
        if not order_id and not client_order_id:
            return None
        params = {"symbol": str(symbol).upper()}
        if order_id:
            params["orderId"] = int(order_id)
        if client_order_id:
            params["origClientOrderId"] = str(client_order_id)
        try:
            with self._client_lock:
                return self.client.get_order(**params)
        except Exception as exc:
            if isinstance(exc, self.api_exception_cls):
                self.last_error = str(exc)
                self.logger.warning(
                    "Failed to get order symbol=%s order_id=%s error=%s",
                    symbol,
                    order_id or client_order_id,
                    exc,
                )
            else:
                self.last_error = str(exc)
                self.logger.exception(
                    "Unexpected error getting order symbol=%s order_id=%s",
                    symbol,
                    order_id or client_order_id,
                )
        return None

    def cancel_order(self, symbol, order_id=None, client_order_id=None):
        if not self.is_ready():
            return None
        if not order_id and not client_order_id:
            return None
        params = {"symbol": str(symbol).upper()}
        if order_id:
            params["orderId"] = int(order_id)
        if client_order_id:
            params["origClientOrderId"] = str(client_order_id)
        try:
            with self._client_lock:
                response = self.client.cancel_order(**params)
            self._log_event(
                "ORDER_CANCELLED",
                f"Cancelled order for {symbol}",
                severity="info",
                details=params,
            )
            self.logger.info(
                "Order cancelled symbol=%s order_id=%s",
                symbol,
                order_id or client_order_id,
            )
            return response
        except Exception as exc:
            self.last_error = str(exc)
            severity = "warning"
            if isinstance(exc, self.api_exception_cls):
                self._log_event(
                    "ORDER_CANCEL_FAILED", str(exc), severity=severity, details=params
                )
                self.logger.warning(
                    "Failed to cancel order symbol=%s order_id=%s error=%s",
                    symbol,
                    order_id or client_order_id,
                    exc,
                )
            else:
                self._log_event(
                    "ORDER_CANCEL_FAILED", str(exc), severity=severity, details=params
                )
                self.logger.exception(
                    "Unexpected error cancelling order symbol=%s order_id=%s",
                    symbol,
                    order_id or client_order_id,
                )
        return None

    def place_real_order(
        self,
        symbol,
        side,
        quantity,
        price=None,
        order_type="MARKET",
        time_in_force=None,
    ):
        """Execute a market or limit order; uses test orders when testnet is enabled."""
        order_type = (order_type or "MARKET").upper()
        resolved_price = None
        if price is not None:
            try:
                resolved_price = float(price)
            except Exception:
                resolved_price = None
        if resolved_price is None:
            resolved_price = self._resolve_price(symbol, price)
        normalized_qty, qty_note = self._normalize_order_quantity(symbol, quantity)
        if normalized_qty is None:
            reason = qty_note or "Quantity rejected by exchange filters"
            failed_request = {
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "quantity": float(quantity),
            }
            if price and order_type != "MARKET":
                failed_request["price"] = float(price)
            self._record_order_event("FAILED", failed_request, error=reason)
            self._log_event(
                "ORDER_FILTER_REJECT",
                reason,
                severity="warning",
                details=failed_request,
            )
            self.logger.warning(
                "Order rejected pre-flight symbol=%s side=%s qty=%s reason=%s",
                symbol,
                side,
                quantity,
                reason,
            )
            self.last_error = reason
            return None

        min_notional = self.get_min_notional(symbol)
        if min_notional and resolved_price:
            try:
                order_notional = Decimal(str(normalized_qty)) * Decimal(
                    str(resolved_price)
                )
                if order_notional < Decimal(str(min_notional)):
                    reason = f"Order value {float(order_notional):.2f} below minNotional {min_notional}"
                    failed_request = {
                        "symbol": symbol,
                        "side": side,
                        "type": order_type,
                        "quantity": float(normalized_qty),
                        "resolved_price": float(resolved_price),
                    }
                    if price and order_type != "MARKET":
                        failed_request["price"] = float(price)
                    self._record_order_event("FAILED", failed_request, error=reason)
                    self._log_event(
                        "ORDER_FILTER_REJECT",
                        reason,
                        severity="warning",
                        details=failed_request,
                    )
                    self.logger.warning(
                        "Order rejected by notional filter symbol=%s side=%s qty=%s value=%s min=%s",
                        symbol,
                        side,
                        normalized_qty,
                        float(order_notional),
                        min_notional,
                    )
                    self.last_error = reason
                    return None
            except Exception as exc:
                self.logger.warning(
                    "Failed to evaluate min notional symbol=%s qty=%s price=%s error=%s",
                    symbol,
                    normalized_qty,
                    resolved_price,
                    exc,
                )

        order_request = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": float(normalized_qty),
        }
        if order_type != "MARKET":
            if resolved_price is None:
                reason = "Limit order requires valid price"
                self._record_order_event("FAILED", order_request, error=reason)
                self.last_error = reason
                return None
            order_request["price"] = float(resolved_price)
            tif = time_in_force or "GTC"
            order_request["timeInForce"] = tif

        if qty_note:
            self._log_event(
                "ORDER_QUANTITY_ADJUSTED",
                qty_note,
                severity="info",
                details={
                    "symbol": symbol,
                    "side": side,
                    "original_qty": float(quantity),
                    "normalized_qty": float(normalized_qty),
                    "testnet": self.testnet,
                },
            )
            self.logger.info(
                "Order quantity adjusted symbol=%s side=%s original=%s normalized=%s note=%s",
                symbol,
                side,
                quantity,
                normalized_qty,
                qty_note,
            )

        quantity = float(normalized_qty)

        if not self.is_ready():
            if not self.connect():
                self._record_order_event("FAILED", order_request, error=self.last_error)
                self.logger.error(
                    "Order rejected - unable to connect symbol=%s side=%s account_type=%s",
                    symbol,
                    side,
                    self.account_type,
                )
                return None

        # Check circuit breaker before attempting trade
        if self.circuit_breaker.is_open:
            reason = "Circuit breaker is OPEN - trading temporarily disabled due to recent failures"
            self._record_order_event("FAILED", order_request, error=reason)
            self._log_event(
                "CIRCUIT_BREAKER_OPEN",
                reason,
                severity="warning",
                details=order_request,
            )
            self.logger.warning(
                "Order rejected by circuit breaker symbol=%s side=%s",
                symbol,
                side,
            )
            self.last_error = reason
            return None

        try:
            # Execute order through circuit breaker
            def _execute_order():
                with self._client_lock:
                    if self.testnet:
                        response = self.client.create_test_order(**order_request)
                        status = "TEST_SUBMITTED"
                    else:
                        response = self.client.create_order(**order_request)
                        status = response.get("status", "SUBMITTED")
                return response, status

            response, status = self.circuit_breaker.call(_execute_order)

            self._record_order_event(status, order_request, response=response)
            self._log_event(
                "ORDER_SUBMITTED",
                f"Order {status} for {symbol}",
                severity="success",
                details={
                    "symbol": symbol,
                    "side": side,
                    "qty": float(quantity),
                    "testnet": self.testnet,
                },
            )
            self.logger.info(
                "Order submitted status=%s symbol=%s side=%s qty=%s testnet=%s",
                status,
                symbol,
                side,
                quantity,
                self.testnet,
            )
            return response
        except CircuitBreakerOpenException as exc:
            # Circuit breaker is open, already logged above
            self.last_error = str(exc)
            return None
        except Exception as exc:
            self.last_error = str(exc)
            self._record_order_event("FAILED", order_request, error=self.last_error)
            self._log_event(
                "ORDER_ERROR",
                self.last_error,
                severity="error",
                details={"symbol": symbol, "side": side, "qty": float(quantity)},
            )
            if isinstance(exc, self.api_exception_cls):
                self.logger.warning(
                    "Order API error symbol=%s side=%s qty=%s error=%s",
                    symbol,
                    side,
                    quantity,
                    exc,
                    exc_info=True,
                )
            else:
                self.logger.exception(
                    "Order unexpected exception symbol=%s side=%s qty=%s",
                    symbol,
                    side,
                    quantity,
                )
        return None

    def get_recent_orders(self, limit=10):
        items = list(self.order_history)
        if limit:
            return items[-limit:]
        return items

    def get_status(self):
        return {
            "connected": self.connected,
            "testnet": self.testnet,
            "last_error": self.last_error,
            "recent_orders": self.get_recent_orders(limit=10),
            "account_status": self.account_status,
        }

    def _record_order_event(self, status, request, response=None, error=None):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": status,
            "symbol": request.get("symbol"),
            "side": request.get("side"),
            "type": request.get("type"),
            "quantity": request.get("quantity"),
            "price": request.get("price"),
            "testnet": self.testnet,
            "response": response,
            "error": error,
        }
        self.order_history.append(event)
        if error:
            self._log_event(
                "ORDER_EVENT",
                f"Order {status}: {error}",
                severity="error",
                details=request,
            )
            self.logger.error(
                "Order event recorded status=%s error=%s symbol=%s",
                status,
                error,
                request.get("symbol"),
            )
        elif status and "FAIL" in status.upper():
            self._log_event(
                "ORDER_EVENT", f"Order {status}", severity="error", details=request
            )
            self.logger.error(
                "Order failure recorded status=%s symbol=%s",
                status,
                request.get("symbol"),
            )
        return event

    def execute_manual_trade(self, symbol, side, quantity, price=None):
        """Execute a manual spot trade."""
        try:
            order = self.place_real_order(
                symbol=symbol,
                side=side.upper(),
                quantity=quantity,
                price=price,
                order_type="MARKET" if price is None else "LIMIT",
            )
            if order:
                return {
                    "success": True,
                    "order": order,
                    "price": order.get("price") or price,
                }
            else:
                return {
                    "success": False,
                    "error": self.last_error or "Order failed",
                }
        except Exception as exc:
            self.logger.error(f"Manual trade execution failed: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }


class BinanceFuturesTrader:
    """Lightweight perpetual futures trader for Binance USDT-margined contracts."""

    TESTNET_BASE_URL = "https://testnet.binancefuture.com"

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        *,
        testnet: bool = True,
        binance_um_futures_cls: Optional[type] = None,
        binance_rest_client_cls: Optional[type] = None,
        binance_log_manager: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
        coerce_bool: Optional[Callable[[Any, bool], bool]] = None,
        safe_float: Optional[Callable[[Any, float], float]] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("BINANCE_FUTURES_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_FUTURES_API_SECRET")
        self._coerce_bool = coerce_bool or _coerce_bool
        self._safe_float = safe_float or self._default_safe_float
        self.testnet = self._coerce_bool(testnet, default=True)
        self.client = None
        self.connected = False
        self.last_error = None
        self.account_status: dict[str, Any] = {}
        self._client_lock = threading.Lock()
        self.leverage_cache: dict[str, int] = {}
        self.margin_type_cache: dict[str, Any] = {}
        self._open_interest_cache: dict[str, float] = {}
        self._client_type: Optional[str] = None
        self.binance_um_futures_cls = binance_um_futures_cls
        self.binance_rest_client_cls = binance_rest_client_cls
        self.binance_log_manager = binance_log_manager
        self.logger = logger or logging.getLogger("ai_trading_bot")

        if self.api_key and self.api_secret:
            self.connect()

    @staticmethod
    def _default_safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float(default)

    def _log_event(self, event_type, message, severity="info", details=None):
        if not self.binance_log_manager:
            return
        try:
            payload = {"testnet": self.testnet}
            if isinstance(details, dict):
                payload.update(details)
            elif details is not None:
                payload["details"] = details
            self.binance_log_manager.add(
                event_type,
                message,
                severity=severity,
                account_type="futures",
                details=payload,
            )
        except Exception:  # pragma: no cover - logging best effort
            pass

    def _configure_rest_client(self, client):
        if not client:
            return client

        tld = getattr(client, "tld", "com")
        futures_url = getattr(client, "FUTURES_URL", None)
        if futures_url and isinstance(futures_url, str) and "{" in futures_url:
            client.FUTURES_URL = futures_url.format(tld)
        futures_data_url = getattr(client, "FUTURES_DATA_URL", None)
        if (
            futures_data_url
            and isinstance(futures_data_url, str)
            and "{" in futures_data_url
        ):
            client.FUTURES_DATA_URL = futures_data_url.format(tld)

        if self.testnet:
            overrides = {
                "API_URL": getattr(client, "API_TESTNET_URL", None),
                "FUTURES_URL": getattr(client, "FUTURES_TESTNET_URL", None)
                or f"{self.TESTNET_BASE_URL}/fapi",
                "FUTURES_DATA_URL": getattr(client, "FUTURES_DATA_TESTNET_URL", None)
                or f"{self.TESTNET_BASE_URL}/futures/data",
                "FUTURES_COIN_URL": getattr(client, "FUTURES_COIN_TESTNET_URL", None),
                "FUTURES_COIN_DATA_URL": getattr(
                    client, "FUTURES_COIN_DATA_TESTNET_URL", None
                ),
                "WS_FUTURES_URL": getattr(client, "WS_FUTURES_TESTNET_URL", None),
            }
            for attr, value in overrides.items():
                if value:
                    setattr(client, attr, value)

        return client

    def connect(self) -> bool:
        if not self.api_key or not self.api_secret:
            self.last_error = "Missing futures API credentials"
            self.connected = False
            self._log_event("FUTURES_CONNECT", self.last_error, severity="error")
            return False

        errors: list[str] = []
        candidate = None
        client_type = None

        if self.binance_um_futures_cls:
            try:
                kwargs = {"key": self.api_key, "secret": self.api_secret}
                if self.testnet:
                    kwargs["base_url"] = self.TESTNET_BASE_URL
                candidate = self.binance_um_futures_cls(**kwargs)
                client_type = "um"
            except Exception as exc:
                errors.append(str(exc))

        if candidate is None and self.binance_rest_client_cls:
            try:
                rest_client = self.binance_rest_client_cls(
                    self.api_key,
                    self.api_secret,
                    testnet=self.testnet,
                )
                candidate = self._configure_rest_client(rest_client)
                client_type = "rest"
            except Exception as exc:
                errors.append(str(exc))

        if candidate is None:
            self.client = None
            self.connected = False
            self._client_type = None
            self.last_error = (
                errors[-1] if errors else "Binance futures client unavailable"
            )
            self._log_event("FUTURES_CONNECT", self.last_error, severity="error")
            if self.logger:
                self.logger.error("Binance futures connect failed: %s", self.last_error)
            return False

        with self._client_lock:
            self.client = candidate
        self._client_type = client_type
        self.connected = True
        self.last_error = None
        self._open_interest_cache.clear()

        if client_type == "rest":
            try:
                self.client.futures_ping()
            except Exception as exc:
                self._log_event(
                    "FUTURES_PING_WARN",
                    f"Futures ping warning: {exc}",
                    severity="warning",
                )

        self._log_event(
            "FUTURES_CONNECT",
            "Connected to Binance futures endpoint.",
            severity="success",
        )
        return True

    def is_ready(self) -> bool:
        return self.connected and self.client is not None

    def set_credentials(self, api_key=None, api_secret=None, auto_connect=True):
        self.api_key = api_key or self.api_key
        self.api_secret = api_secret or self.api_secret
        self.leverage_cache.clear()
        self.margin_type_cache.clear()
        self._open_interest_cache.clear()
        self._log_event(
            "FUTURES_CREDENTIAL_UPDATE",
            "Updated futures API credentials.",
            severity="info",
        )
        if auto_connect:
            return self.connect()
        return True

    def set_testnet(self, enabled=True):
        self.testnet = self._coerce_bool(enabled, default=self.testnet)
        self.leverage_cache.clear()
        self.margin_type_cache.clear()
        self._open_interest_cache.clear()
        self._log_event(
            "FUTURES_TESTNET",
            f"Futures testnet toggled -> {self.testnet}",
            severity="info",
        )
        if self.client:
            return self.connect()
        return True

    def get_market_metrics(self, symbol):
        if not self.is_ready() or not symbol:
            return None

        symbol_key = str(symbol).upper()
        metrics = {
            "funding_rate": 0.0,
            "open_interest": 0.0,
            "open_interest_change": 0.0,
            "long_liquidations": 0.0,
            "short_liquidations": 0.0,
            "basis": 0.0,
            "long_short_ratio": 1.0,
            "taker_buy_volume": 0.0,
            "estimated_liquidation_price": 0.0,
            "mark_price": None,
            "index_price": None,
            "timestamp": time.time(),
        }

        try:
            with self._client_lock:
                if self._client_type == "um":
                    mark_payload = self.client.mark_price(symbol=symbol_key)
                else:
                    mark_payload = self.client.futures_mark_price(symbol=symbol_key)
            if isinstance(mark_payload, dict):
                mark_price = self._safe_float(mark_payload.get("markPrice"))
                index_price = self._safe_float(
                    mark_payload.get("indexPrice"), mark_price
                )
                funding_rate = self._safe_float(mark_payload.get("lastFundingRate"))
                metrics["funding_rate"] = funding_rate
                metrics["mark_price"] = mark_price
                metrics["index_price"] = index_price
                if index_price:
                    try:
                        metrics["basis"] = (
                            (mark_price - index_price) / index_price
                            if index_price
                            else 0.0
                        )
                    except ZeroDivisionError:
                        metrics["basis"] = 0.0
        except Exception as exc:
            self._log_event(
                "FUTURES_MARK_DATA_ERROR",
                str(exc),
                severity="warning",
                details={"symbol": symbol_key},
            )

        try:
            with self._client_lock:
                if self._client_type == "um":
                    open_interest_payload = self.client.open_interest(symbol=symbol_key)
                else:
                    open_interest_payload = self.client.futures_open_interest(
                        symbol=symbol_key
                    )
            if isinstance(open_interest_payload, dict):
                open_interest = self._safe_float(
                    open_interest_payload.get("openInterest")
                )
                if open_interest:
                    previous = self._open_interest_cache.get(symbol_key)
                    metrics["open_interest"] = open_interest
                    if previous:
                        try:
                            metrics["open_interest_change"] = (
                                (open_interest - previous) / previous
                                if previous
                                else 0.0
                            )
                        except ZeroDivisionError:
                            metrics["open_interest_change"] = 0.0
                    self._open_interest_cache[symbol_key] = open_interest
        except Exception:
            pass

        try:
            with self._client_lock:
                if self._client_type == "um":
                    ticker_payload = self.client.ticker_24hr(symbol=symbol_key)
                else:
                    ticker_payload = self.client.futures_ticker(symbol=symbol_key)
            if isinstance(ticker_payload, dict):
                metrics["taker_buy_volume"] = self._safe_float(
                    ticker_payload.get("takerBuyVolume")
                )
        except Exception:
            pass

        try:
            with self._client_lock:
                if self._client_type == "um" and hasattr(
                    self.client, "top_long_short_account_ratio"
                ):
                    ratio_payload = self.client.top_long_short_account_ratio(
                        symbol=symbol_key, period="5m", limit=1
                    )
                elif hasattr(self.client, "futures_top_long_short_account_ratio"):
                    ratio_payload = self.client.futures_top_long_short_account_ratio(
                        symbol=symbol_key, period="5m", limit=1
                    )
                else:
                    ratio_payload = None
            if isinstance(ratio_payload, list) and ratio_payload:
                metrics["long_short_ratio"] = self._safe_float(
                    ratio_payload[0].get("longShortRatio"), metrics["long_short_ratio"]
                )
        except Exception:
            pass

        try:
            position = self.get_position(symbol_key)
            if isinstance(position, dict):
                metrics["estimated_liquidation_price"] = self._safe_float(
                    position.get("liquidationPrice")
                )
        except Exception:
            pass

        return metrics

    def ensure_leverage(self, symbol, leverage):
        if not self.is_ready():
            return False
        symbol_key = str(symbol).upper()
        leverage_int = max(1, int(float(leverage)))
        cached = self.leverage_cache.get(symbol_key)
        if cached == leverage_int:
            return True
        try:
            with self._client_lock:
                if self._client_type == "um":
                    self.client.change_leverage(
                        symbol=symbol_key, leverage=leverage_int
                    )
                else:
                    self.client.futures_change_leverage(
                        symbol=symbol_key, leverage=leverage_int
                    )
            self.leverage_cache[symbol_key] = leverage_int
            self._log_event(
                "FUTURES_LEVERAGE",
                f"Leverage set to {leverage_int} for {symbol_key}",
                details={
                    "symbol": symbol_key,
                    "leverage": leverage_int,
                    "client_type": self._client_type,
                },
            )
            return True
        except Exception as exc:
            self.last_error = str(exc)
            self._log_event(
                "FUTURES_LEVERAGE_ERROR",
                self.last_error,
                severity="error",
                details={"symbol": symbol_key, "client_type": self._client_type},
            )
            return False

    def get_position(self, symbol):
        if not self.is_ready():
            return None
        symbol_key = str(symbol).upper()
        try:
            with self._client_lock:
                if self._client_type == "um":
                    positions = self.client.get_position_risk(symbol=symbol_key)
                else:
                    positions = self.client.futures_position_information(
                        symbol=symbol_key
                    )
            if isinstance(positions, list) and positions:
                return positions[0]
            return None
        except Exception as exc:
            self.last_error = str(exc)
            self._log_event(
                "FUTURES_POSITION_ERROR",
                self.last_error,
                severity="warning",
                details={"symbol": symbol_key, "client_type": self._client_type},
            )
            return None

    def place_market_order(self, symbol, side, quantity, reduce_only=False):
        if not self.is_ready():
            return None
        try:
            params = {
                "symbol": str(symbol).upper(),
                "side": str(side).upper(),
                "type": "MARKET",
                "quantity": float(quantity),
            }
            if reduce_only:
                params["reduceOnly"] = "true" if self._client_type == "rest" else True
            with self._client_lock:
                if self._client_type == "um":
                    response = self.client.new_order(**params)
                else:
                    response = self.client.futures_create_order(**params)
            self._log_event(
                "FUTURES_ORDER",
                f"{params['side']} {params['quantity']} {params['symbol']} (reduceOnly={reduce_only})",
                severity="success",
                details={"client_type": self._client_type},
            )
            return response
        except Exception as exc:
            self.last_error = str(exc)
            self._log_event(
                "FUTURES_ORDER_ERROR",
                self.last_error,
                severity="error",
                details={
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "reduce_only": reduce_only,
                    "client_type": self._client_type,
                },
            )
            if self.logger:
                self.logger.warning(
                    "Futures order failed symbol=%s side=%s error=%s", symbol, side, exc
                )
            return None

    def close_position(self, symbol):
        position = self.get_position(symbol)
        if not position:
            return None
        raw_amt = position.get("positionAmt") if isinstance(position, dict) else None
        qty = abs(float(raw_amt or 0))
        if qty <= 0:
            return None
        side = "SELL" if float(raw_amt or 0) > 0 else "BUY"
        return self.place_market_order(symbol, side, qty, reduce_only=True)

    def get_account_overview(self):
        if not self.is_ready():
            return None
        try:
            with self._client_lock:
                if self._client_type == "um":
                    balances = self.client.balance()
                else:
                    balances = self.client.futures_account_balance()
            if isinstance(balances, list):
                return next(
                    (bal for bal in balances if bal.get("asset") == "USDT"),
                    balances[0] if balances else None,
                )
            return None
        except Exception as exc:
            self.last_error = str(exc)
            self._log_event(
                "FUTURES_BALANCE_ERROR",
                self.last_error,
                severity="warning",
                details={"client_type": self._client_type},
            )
            return None

    def get_status(self):
        return {
            "connected": self.connected,
            "testnet": self.testnet,
            "last_error": self.last_error,
            "client_type": self._client_type,
            "account": self.get_account_overview(),
        }

    def execute_manual_futures_trade(
        self, symbol, side, quantity, leverage=1, price=None
    ):
        """Execute a manual futures trade."""
        try:
            # Set leverage first
            self.set_leverage(symbol, leverage)

            order = self.place_market_order(
                symbol=symbol,
                side=side.upper(),
                quantity=quantity,
            )
            if order:
                return {
                    "success": True,
                    "order": order,
                    "price": order.get("price") or price,
                }
            else:
                return {
                    "success": False,
                    "error": self.last_error or "Futures order failed",
                }
        except Exception as exc:
            self.logger.error(f"Manual futures trade execution failed: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }


@dataclass
class TradingServiceBundle:
    """Container for trader instances and supporting utilities."""

    trade_history: Any
    ultimate_trader: Any
    optimized_trader: Any
    parallel_engine: Any


def create_trading_services(
    *,
    trade_history_factory: Callable[[], Any],
    ultimate_trader_factory: Callable[[], Any],
    optimized_trader_factory: Callable[[], Any],
    parallel_engine_factory: Callable[[], Any],
) -> TradingServiceBundle:
    """Instantiate the trading-facing objects (traders, history, parallel engine)."""

    trade_history = trade_history_factory()
    ultimate_trader = ultimate_trader_factory()
    optimized_trader = optimized_trader_factory()
    parallel_engine = parallel_engine_factory()

    return TradingServiceBundle(
        trade_history=trade_history,
        ultimate_trader=ultimate_trader,
        optimized_trader=optimized_trader,
        parallel_engine=parallel_engine,
    )


def attach_trading_ml_dependencies(
    trading_bundle: TradingServiceBundle,
    ml_bundle: MLServiceBundle,
) -> None:
    """Wire ML systems into the trader instances (QFM + futures hooks)."""

    ultimate_ml = ml_bundle.ultimate_ml_system
    optimized_ml = ml_bundle.optimized_ml_system
    futures_ml = ml_bundle.futures_ml_system

    ultimate_trader = trading_bundle.ultimate_trader
    optimized_trader = trading_bundle.optimized_trader

    # Share QFM engines between ML systems and traders
    if hasattr(ultimate_trader, "qfm_engine"):
        ultimate_trader.qfm_engine = getattr(ultimate_ml, "qfm_engine", None)
    if hasattr(optimized_trader, "qfm_engine"):
        optimized_trader.qfm_engine = getattr(optimized_ml, "qfm_engine", None)

    # Wire futures module references (if present)
    futures_module = getattr(futures_ml, "futures_module", None)
    if futures_module is not None:
        setattr(ultimate_ml, "futures_module", futures_module)
        setattr(optimized_ml, "futures_module", futures_module)

    setattr(ultimate_ml, "futures_integration", futures_ml)
    setattr(optimized_ml, "futures_integration", futures_ml)
    setattr(futures_ml, "futures_integration", futures_ml)

    if hasattr(ultimate_trader, "futures_ml_system"):
        ultimate_trader.futures_ml_system = futures_ml
    if hasattr(optimized_trader, "futures_ml_system"):
        optimized_trader.futures_ml_system = futures_ml


# Backwards-compatible alias: some tests and older code import
# `_default_safe_float` from the module directly. Keep an alias here
# so imports like `from app.services.trading import _default_safe_float`
# continue to work.
_default_safe_float = BinanceFuturesTrader._default_safe_float


def create_user_trader_resolver(
    trading_bundle: TradingServiceBundle,
    *,
    optimized_aliases: Optional[Iterable[str]] = None,
):
    """Return a helper that maps profile names to trader instances."""

    aliases = {
        alias.lower()
        for alias in (optimized_aliases or ("optimized", "professional", "pro"))
    }
    ultimate = trading_bundle.ultimate_trader
    optimized = trading_bundle.optimized_trader

    def _resolver(user_id=None, profile="ultimate"):
        profile_normalized = str(profile or "ultimate").strip().lower()
        if profile_normalized in aliases:
            return optimized
        return ultimate

    return _resolver


def record_user_trade(
    user_id: int,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    trade_type: str = "manual",
    signal_source: str = "manual",
    confidence_score: float = 1.0,
    leverage: int = 1,
) -> None:
    """Record a user trade in the database."""
    from app.extensions import db
    from app.models import UserTrade

    try:
        trade = UserTrade(
            user_id=user_id,
            symbol=symbol,
            trade_type=trade_type,
            side=side,
            quantity=quantity,
            entry_price=price,
            signal_source=signal_source,
            confidence_score=confidence_score,
            leverage=leverage,
        )
        db.session.add(trade)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"Failed to record user trade: {exc}")
        raise
