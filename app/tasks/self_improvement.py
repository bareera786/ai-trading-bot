"""Self-improvement background worker."""
from __future__ import annotations

import threading
import time
from typing import Any, Optional


class SelfImprovementWorker:
    """Manage the periodic self-improvement cycle on a background thread."""

    def __init__(
        self,
        *,
        ultimate_trader: Any,
        optimized_trader: Any,
        ultimate_ml_system: Any,
        optimized_ml_system: Any,
        dashboard_data: dict[str, Any],
        trading_config: dict[str, Any],
        cycle_interval_seconds: float = 10800.0,
        logger: Optional[Any] = None,
    ) -> None:
        self.ultimate_trader = ultimate_trader
        self.optimized_trader = optimized_trader
        self.ultimate_ml_system = ultimate_ml_system
        self.optimized_ml_system = optimized_ml_system
        self.dashboard_data = dashboard_data
        self.trading_config = trading_config
        self.cycle_interval = max(60.0, float(cycle_interval_seconds))
        self.logger = logger

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.is_running:
            self._log("🤖 Self-improvement worker already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name='SelfImprovementWorker', daemon=True)
        self._thread.start()
        self._log("🤖 Self-improvement worker started")

    def stop(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=max(5.0, self.cycle_interval / 10))
        self._thread = None
        self._log("🤖 Self-improvement worker stopped")

    def _run_loop(self) -> None:
        # Wait before first run to match the legacy cadence (every 3 hours)
        while not self._stop_event.wait(self.cycle_interval):
            try:
                self._run_cycle()
            except Exception as exc:  # pragma: no cover - defensive logging
                self._log(f"❌ Self-improvement error: {exc}")

    def _run_cycle(self) -> None:
        self._log("\n🤖 ULTIMATE Self-Improvement Cycle Started...")

        success_rate = self.ultimate_trader.improve_bot_efficiency_ultimate()
        self._log(f"🤖 {self.ultimate_trader.profile_prefix} Learning: Success rate {success_rate:.1f}%")

        optimized_success_rate = self.optimized_trader.improve_bot_efficiency_ultimate()
        self._log(f"🤖 {self.optimized_trader.profile_prefix} Learning: Success rate {optimized_success_rate:.1f}%")

        if self.trading_config.get('periodic_rebuilding'):
            self.ultimate_ml_system.ensemble_system.periodic_ensemble_rebuilding(
                self.dashboard_data.get('ml_predictions', {}),
                self._extract_prices('ml_predictions'),
            )
            self.optimized_ml_system.ensemble_system.periodic_ensemble_rebuilding(
                self.dashboard_data.get('optimized_ml_predictions', {}),
                self._extract_prices('optimized_ml_predictions'),
            )

        self._log("🤖 Ultimate Self-Improvement Cycle Completed!")

    def _extract_prices(self, _profile_key: str) -> dict[str, float]:
        market_data = self.dashboard_data.get('market_data', {}) or {}
        prices = {}
        for symbol, data in market_data.items():
            try:
                prices[symbol] = float(data.get('price', 0) or data.get('close', 0) or 0)
            except Exception:
                prices[symbol] = 0.0
        return prices

    def _log(self, message: str) -> None:
        if self.logger:
            try:
                self.logger.info(message)
                return
            except Exception:
                pass
        print(message)
