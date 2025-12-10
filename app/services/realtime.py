"""Background realtime update service for Socket.IO broadcasts."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable

from flask_socketio import SocketIO


class RealtimeUpdateService:
    """Emit dashboard updates over Socket.IO on a fixed cadence."""

    def __init__(
        self,
        socketio: SocketIO,
        dashboard_data: dict[str, Any],
        get_active_trading_universe: Callable[[], list[str]] | None = None,
    ) -> None:
        self._socketio = socketio
        self._dashboard_data = dashboard_data
        self._get_active_trading_universe = get_active_trading_universe or (lambda: [])
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="RealtimeUpdateService", daemon=True
        )
        self._thread.start()
        print("✅ Real-time update service started")

    def stop(self) -> None:
        if not self._thread:
            return
        self._stop_event.set()
        self._thread.join(timeout=2)
        self._thread = None
        print("ℹ️ Real-time update service stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._emit_portfolio_update()
                self._emit_pnl_update()
                self._emit_performance_update()
                self._emit_market_data_update()
                time.sleep(5)
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Error in real-time update service: {exc}")
                time.sleep(10)

    def _emit_portfolio_update(self) -> None:
        payload = {
            "portfolio": self._dashboard_data.get("portfolio", {}),
            "timestamp": time.time(),
        }
        self._socketio.emit("portfolio_update", payload)

    def _emit_pnl_update(self) -> None:
        portfolio = self._dashboard_data.get("portfolio", {}) or {}
        positions = portfolio.get("positions") or []
        pnl_payload = {
            "total_pnl": portfolio.get("total_pnl", 0),
            "daily_pnl": portfolio.get("daily_pnl", 0),
            "open_positions_pnl": sum(
                pos.get("pnl", 0) for pos in positions if isinstance(pos, dict)
            ),
            "timestamp": time.time(),
        }
        self._socketio.emit("pnl_update", pnl_payload)

    def _emit_performance_update(self) -> None:
        payload = {
            "performance": self._dashboard_data.get("performance", {}),
            "timestamp": time.time(),
        }
        self._socketio.emit("performance_update", payload)

    def _emit_market_data_update(self) -> None:
        active_symbols = self._get_active_trading_universe() or []
        dashboard_market_data = self._dashboard_data.get("market_data", {}) or {}
        market_data = {}
        for symbol in active_symbols[:10]:
            if symbol in dashboard_market_data:
                market_data[symbol] = dashboard_market_data[symbol]
        if market_data:
            self._socketio.emit(
                "market_data_update",
                {
                    "market_data": market_data,
                    "timestamp": time.time(),
                },
            )
