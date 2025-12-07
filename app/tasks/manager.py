"""Centralized start/stop control for background services."""
from __future__ import annotations

from typing import Any, Mapping


class BackgroundTaskManager:
    """Provide explicit lifecycle hooks for background tasks/services."""

    def __init__(
        self,
        *,
        market_data_service: Any,
        futures_market_data_service: Any | None,
        realtime_update_service: Any | None,
        persistence_scheduler: Any | None,
        self_improvement_worker: Any | None,
        model_training_worker: Any | None,
        live_portfolio_scheduler: Any | None,
        trading_config: Mapping[str, Any],
        bot_logger: Any | None = None,
    ) -> None:
        self.market_data_service = market_data_service
        self.futures_market_data_service = futures_market_data_service
        self.realtime_update_service = realtime_update_service
        self.persistence_scheduler = persistence_scheduler
        self.self_improvement_worker = self_improvement_worker
        self.model_training_worker = model_training_worker
        self.live_portfolio_scheduler = live_portfolio_scheduler
        self.trading_config = dict(trading_config or {})
        self.bot_logger = bot_logger
        self._persistence_active = False

    # ------------------------------------------------------------------
    # Startup helpers
    # ------------------------------------------------------------------
    def start_background_tasks(
        self,
        *,
        start_ultimate_training: bool,
        start_optimized_training: bool,
    persistence_inputs: Mapping[str, Any] | None = None,
    ) -> None:
        """Start all long-running background services with consistent logging."""
        self._start_service(self.market_data_service, "Market data service")

        if self.trading_config.get('futures_enabled') and self.futures_market_data_service:
            self._start_service(self.futures_market_data_service, "Futures market data service")
        elif self.futures_market_data_service:
            self._log("ℹ️ Futures module ready. Enable futures trading from the dashboard when prepared.")

        if self.self_improvement_worker:
            try:
                self.self_improvement_worker.start()
                self._log("✅ Self-improvement worker started")
            except Exception as exc:  # pragma: no cover - defensive logging
                self._log(f"⚠️ Failed to start self-improvement worker: {exc}", warning=True)

        if start_ultimate_training and self.model_training_worker:
            try:
                self.model_training_worker.start_ultimate_startup_training()
                self._log("✅ Ultimate model training dispatched")
            except Exception as exc:  # pragma: no cover
                self._log(f"⚠️ Failed to dispatch ultimate model training: {exc}", warning=True)

        if start_optimized_training and self.model_training_worker:
            try:
                self.model_training_worker.start_optimized_startup_training()
                self._log("✅ Optimized model training dispatched")
            except Exception as exc:  # pragma: no cover
                self._log(f"⚠️ Failed to dispatch optimized model training: {exc}", warning=True)

        if persistence_inputs and self.persistence_scheduler:
            try:
                self.persistence_scheduler.start_automatic_saving(
                    persistence_inputs['trader'],
                    persistence_inputs['ml_system'],
                    persistence_inputs['config'],
                    persistence_inputs.get('symbols', []),
                    persistence_inputs.get('historical_data', {}),
                )
                self._persistence_active = True
            except Exception as exc:  # pragma: no cover
                self._log(f"⚠️ Failed to start automatic persistence: {exc}", warning=True)

        self._start_service(self.realtime_update_service, "Real-time update service")

    def start_live_portfolio_updates(self) -> None:
        if not self.live_portfolio_scheduler:
            return
        try:
            self.live_portfolio_scheduler.start_live_updates()
            self._log("✅ Live portfolio P&L scheduler started")
        except Exception as exc:  # pragma: no cover
            self._log(f"⚠️ Failed to start live portfolio scheduler: {exc}", warning=True)

    # ------------------------------------------------------------------
    # Shutdown helpers
    # ------------------------------------------------------------------
    def stop_background_tasks(self) -> None:
        self._stop_service(self.market_data_service, "Market data service")
        self._stop_service(self.futures_market_data_service, "Futures market data service")
        if self.self_improvement_worker:
            try:
                self.self_improvement_worker.stop()
                self._log("ℹ️ Self-improvement worker stopped")
            except Exception as exc:  # pragma: no cover
                self._log(f"⚠️ Failed to stop self-improvement worker: {exc}", warning=True)
        if self.realtime_update_service:
            try:
                self.realtime_update_service.stop()
                self._log("ℹ️ Real-time update service stopped")
            except Exception as exc:  # pragma: no cover
                self._log(f"⚠️ Failed to stop real-time service: {exc}", warning=True)
        if self._persistence_active and self.persistence_scheduler:
            try:
                self.persistence_scheduler.stop_automatic_saving()
            except Exception as exc:  # pragma: no cover
                self._log(f"⚠️ Failed to stop automatic persistence: {exc}", warning=True)
            finally:
                self._persistence_active = False

    def stop_live_portfolio_updates(self) -> None:
        if not self.live_portfolio_scheduler:
            return
        try:
            self.live_portfolio_scheduler.stop_live_updates()
            self._log("ℹ️ Live portfolio P&L scheduler stopped")
        except Exception as exc:  # pragma: no cover
            self._log(f"⚠️ Failed to stop live portfolio scheduler: {exc}", warning=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _start_service(self, service: Any | None, label: str) -> None:
        if not service:
            return
        try:
            service.start()
            self._log(f"✅ {label} started")
        except Exception as exc:  # pragma: no cover
            self._log(f"⚠️ Failed to start {label.lower()}: {exc}", warning=True)

    def _stop_service(self, service: Any | None, label: str) -> None:
        if not service:
            return
        try:
            service.stop()
            self._log(f"ℹ️ {label} stopped")
        except Exception as exc:  # pragma: no cover
            self._log(f"⚠️ Failed to stop {label.lower()}: {exc}", warning=True)

    def _log(self, message: str, *, warning: bool = False) -> None:
        if self.bot_logger:
            try:
                if warning:
                    self.bot_logger.warning(message)
                else:
                    self.bot_logger.info(message)
                return
            except Exception:
                pass
        print(message)
