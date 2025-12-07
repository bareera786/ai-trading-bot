"""Live portfolio P&L scheduler service."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable


class LivePortfolioScheduler:
    """Manage periodic live portfolio P&L updates inside an app context."""

    def __init__(
        self,
        *,
        app: Any | None,
        update_callback: Callable[[], dict[str, Any]] | None = None,
        update_interval_seconds: float = 30.0,
        tick_interval_seconds: float = 10.0,
        logger: Any | None = None,
    ) -> None:
        self.app = app
        self.update_callback = update_callback
        self.update_interval = max(5.0, float(update_interval_seconds))
        self.tick_interval = max(1.0, float(tick_interval_seconds))
        self.logger = logger

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_update_time = 0.0

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start_live_updates(self) -> None:
        if self.is_running:
            self._log("💰 Live portfolio P&L updates already running")
            return

        if not self.update_callback:
            self._log("⚠️ Live portfolio scheduler has no update callback configured")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name='LivePortfolioScheduler', daemon=True)
        self._thread.start()
        self._log(f"💰 Live portfolio P&L updates started (every {self.update_interval:.0f} seconds)")

    def stop_live_updates(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=max(self.tick_interval, 5.0))
        self._thread = None
        self._log("💰 Live portfolio P&L updates stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                current_time = time.time()
                if current_time - self._last_update_time >= self.update_interval:
                    self._perform_update()
                    self._last_update_time = current_time
            except Exception as exc:  # pragma: no cover - defensive logging
                self._log(f"❌ Live portfolio update error: {exc}")
            finally:
                self._stop_event.wait(self.tick_interval)

    def _perform_update(self) -> None:
        callback = self.update_callback
        if not callback:
            return

        def _run_callback() -> dict[str, Any]:
            return callback()

        if self.app is None:
            result = _run_callback()
        else:
            with self.app.app_context():
                result = _run_callback()

        if isinstance(result, dict):
            if result.get('success'):
                updated_count = result.get('updated_users', 0)
                if updated_count:
                    self._log(f"💰 Updated live P&L for {updated_count} users")
            else:
                self._log(f"❌ Live P&L update failed: {result.get('error')}")

    def _log(self, message: str) -> None:
        if self.logger:
            try:
                self.logger.info(message)
                return
            except Exception:
                pass
        print(message)
