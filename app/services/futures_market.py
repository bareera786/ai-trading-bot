"""Futures market data background service."""
from __future__ import annotations

import random
import threading
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np


class FuturesMarketDataService:
    """Encapsulates the futures dashboard refresh loop."""

    def __init__(
        self,
        *,
        dashboard_data: dict[str, Any],
        futures_dashboard_state: dict[str, Any],
        trading_config: dict[str, Any],
        futures_ml_system: Any,
        ultimate_trader: Any,
        futures_symbols: Sequence[str],
        futures_data_lock: threading.Lock,
        manual_trade_handler: Callable[
            [str, Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], None
        ],
        bot_logger: Any | None = None,
    ) -> None:
        self.dashboard_data = dashboard_data
        self.futures_dashboard_state = futures_dashboard_state
        self.trading_config = trading_config
        self.futures_ml_system = futures_ml_system
        self.ultimate_trader = ultimate_trader
        self.futures_symbols = list(futures_symbols or [])
        self.futures_data_lock = futures_data_lock
        self.manual_trade_handler = manual_trade_handler
        self.logger = bot_logger

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True
        if not self.trading_config.get("futures_enabled", False):
            self._log("ℹ️ Futures system not enabled in config")
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="FuturesMarketDataLoop", daemon=True
        )
        self._thread.start()
        self._log("✅ Futures market data system started")
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(5.0, self._get_interval()))
        self._thread = None
        self._set_disabled_state()
        self._log("🛑 Futures market data system stopped")

    def run_once(self) -> None:
        if not self.trading_config.get("futures_enabled", False):
            self._set_disabled_state()
            return

        market_snapshots: dict[str, Any] = {}
        predictions: dict[str, Any] = {}
        signals: dict[str, Any] = {}
        leverage_map: dict[str, Any] = {}
        sizing_map: dict[str, Any] = {}
        funding_rates: list[float] = []
        high_risk_symbols: list[str] = []
        funding_alerts: list[str] = []

        account_overview = None
        portfolio = self.futures_dashboard_state.get("portfolio", {})
        futures_balance = portfolio.get("balance", 0.0)
        futures_available = portfolio.get("available_margin", futures_balance)
        futures_unrealized = portfolio.get("unrealized_pnl", 0.0)

        try:
            trader = getattr(self.ultimate_trader, "futures_trader", None)
            if trader and trader.is_ready():
                account_overview = trader.get_account_overview()
                if isinstance(account_overview, dict):

                    def _maybe_float(value: Any) -> float | None:
                        try:
                            return float(value)
                        except (TypeError, ValueError):
                            return None

                    balance_candidates = [
                        account_overview.get("balance"),
                        account_overview.get("walletBalance"),
                        account_overview.get("crossWalletBalance"),
                        account_overview.get("totalWalletBalance"),
                    ]
                    available_candidates = [
                        account_overview.get("availableBalance"),
                        account_overview.get("availableMargin"),
                        account_overview.get("crossAvailableBalance"),
                        account_overview.get("maxWithdrawAmount"),
                    ]
                    unrealized_candidates = [
                        account_overview.get("crossUnPnl"),
                        account_overview.get("unrealizedProfit"),
                        account_overview.get("unrealizedPnl"),
                        account_overview.get("unrealizedPnL"),
                    ]

                    parsed_balance = next(
                        (
                            _maybe_float(candidate)
                            for candidate in balance_candidates
                            if candidate is not None
                        ),
                        None,
                    )
                    parsed_available = next(
                        (
                            _maybe_float(candidate)
                            for candidate in available_candidates
                            if candidate is not None
                        ),
                        None,
                    )
                    parsed_unrealized = next(
                        (
                            _maybe_float(candidate)
                            for candidate in unrealized_candidates
                            if candidate is not None
                        ),
                        None,
                    )

                    if parsed_balance is not None:
                        futures_balance = parsed_balance
                    if parsed_available is not None:
                        futures_available = parsed_available
                    if parsed_unrealized is not None:
                        futures_unrealized = parsed_unrealized
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"⚠️ Futures account overview fetch failed: {exc}")

        market_regime = self.dashboard_data.get("system_status", {}).get(
            "market_regime", "NEUTRAL"
        )

        for symbol in self.futures_symbols:
            market_data = self.futures_ml_system.get_futures_market_data(symbol) or {}
            market_snapshots[symbol] = market_data

            prediction = (
                self.futures_ml_system.predict_futures(symbol, market_data) or {}
            )
            predictions[symbol] = prediction

            confidence = float(
                prediction.get("ultimate_ensemble", {}).get("confidence", 0.55) or 0.55
            )
            signal_name = (
                prediction.get("ultimate_ensemble", {}).get("signal") or "HOLD"
            ).upper()
            change_pct = market_data.get("change", 0)
            volatility = abs(float(change_pct or 0)) / 100.0
            if volatility <= 0:
                volatility = random.uniform(0.015, 0.06)

            leverage = self.futures_ml_system.futures_module.calculate_futures_leverage(
                symbol,
                volatility,
                confidence,
                market_regime,
            )
            leverage_map[symbol] = leverage

            entry_price = (
                float(market_data.get("price") or market_data.get("close") or 0) or 0
            )
            if entry_price <= 0:
                entry_price = 1.0

            if "SELL" in signal_name:
                stop_loss_price = entry_price * 1.02
                trade_side = "SHORT"
            else:
                stop_loss_price = entry_price * 0.98
                trade_side = "LONG"

            (
                quantity,
                margin_required,
                notional_value,
            ) = self.futures_ml_system.futures_module.calculate_futures_position_size(
                symbol,
                futures_balance,
                leverage,
                entry_price,
                stop_loss_price,
            )

            sizing_map[symbol] = {
                "quantity": quantity,
                "margin_required": margin_required,
                "notional_value": notional_value,
                "side": trade_side,
                "entry_price": entry_price,
                "stop_loss_price": stop_loss_price,
            }

            futures_signals = prediction.get("futures_signals", [])
            signals[symbol] = futures_signals

            funding_rate = market_data.get("funding_rate", 0) or 0
            funding_rates.append(float(funding_rate))
            if abs(funding_rate) > 0.0005:
                high_risk_symbols.append(symbol)
                funding_alerts.append(f"{symbol} funding {float(funding_rate):+.4%}")
            if self.futures_ml_system.futures_module.should_avoid_funding_period(
                symbol
            ):
                funding_alerts.append(f"Avoid funding window for {symbol}")

            self.manual_trade_handler(
                symbol, market_data, prediction, sizing_map.get(symbol, {})
            )

        total_margin = sum(item["margin_required"] for item in sizing_map.values())
        average_funding = float(np.mean(funding_rates)) if funding_rates else 0.0

        with self.futures_data_lock:
            state_portfolio = self.futures_dashboard_state.setdefault("portfolio", {})
            self.futures_dashboard_state["enabled"] = True
            self.futures_dashboard_state["last_update"] = time.time()
            self.futures_dashboard_state["market_data"] = market_snapshots
            self.futures_dashboard_state["predictions"] = predictions
            self.futures_dashboard_state["signals"] = signals
            self.futures_dashboard_state["recommended_leverage"] = leverage_map
            self.futures_dashboard_state["position_sizing"] = sizing_map
            self.futures_dashboard_state["metrics"] = {
                "average_funding_rate": average_funding,
                "high_risk_symbols": list(set(high_risk_symbols)),
                "funding_alerts": funding_alerts,
            }
            self.futures_dashboard_state["config"] = dict(
                self.futures_ml_system.futures_module.futures_config
            )

            state_portfolio["balance"] = float(futures_balance)
            state_portfolio["unrealized_pnl"] = float(futures_unrealized)
            state_portfolio["used_margin"] = float(total_margin)
            if account_overview:
                state_portfolio["available_margin"] = float(max(0.0, futures_available))
                state_portfolio["account_overview"] = account_overview
            else:
                state_portfolio["available_margin"] = float(
                    max(0.0, state_portfolio.get("balance", 0.0) - total_margin)
                )
                state_portfolio.pop("account_overview", None)
            state_portfolio["equity"] = float(
                state_portfolio["balance"] + state_portfolio.get("unrealized_pnl", 0.0)
            )
            positions = getattr(self.futures_ml_system.futures_module, "positions", {})
            state_portfolio["positions"] = list(positions.values()) if positions else []

        self.dashboard_data["system_status"]["futures_enabled"] = True
        self.dashboard_data["futures_dashboard"] = self.futures_dashboard_state

        summary = (
            f"📈 Futures update: {len(self.futures_symbols)} symbols | "
            f"Avg funding {average_funding:+.4%} | Margin used ${total_margin:.2f}"
        )
        self._log(summary)

    def _run_loop(self) -> None:
        self._log("🔁 Futures market data loop initializing...")
        while not self._stop_event.is_set():
            try:
                self.run_once()
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"❌ Futures market update error: {exc}")
            self._stop_event.wait(self._get_interval())

    def _get_interval(self) -> float:
        default_interval = max(
            10.0, float(self.trading_config.get("futures_update_interval", 30))
        )
        return max(
            10.0,
            float(self.trading_config.get("futures_update_interval", default_interval)),
        )

    def _set_disabled_state(self) -> None:
        with self.futures_data_lock:
            self.futures_dashboard_state["enabled"] = False
            self.futures_dashboard_state["last_update"] = time.time()
            self.futures_dashboard_state["market_data"] = {}
            self.futures_dashboard_state["predictions"] = {}
            self.futures_dashboard_state["signals"] = {}
            self.futures_dashboard_state["recommended_leverage"] = {}
            self.futures_dashboard_state["position_sizing"] = {}
            self.futures_dashboard_state["metrics"] = {
                "average_funding_rate": 0.0,
                "high_risk_symbols": [],
                "funding_alerts": [],
            }
        self.dashboard_data["system_status"]["futures_enabled"] = False

    def _log(self, message: str) -> None:
        if self.logger:
            try:
                self.logger.info(message)
            except Exception:  # pragma: no cover - logger best-effort
                print(message)
        else:
            print(message)
