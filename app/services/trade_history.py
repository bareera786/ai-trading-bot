"""Comprehensive trade history management service."""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, Optional

import numpy as np
import pandas as pd

from .pathing import resolve_profile_path, safe_parse_datetime


class ComprehensiveTradeHistory:
    """High-fidelity trade journal with statistics and journaling utilities."""

    def __init__(
        self,
        data_dir: Optional[str] = None,
        *,
        log_callback: Optional[
            Callable[[str, str, int, Dict[str, Any] | None], None]
        ] = None,
    ) -> None:
        if data_dir is None:
            resolved_dir = resolve_profile_path("trade_data")
        else:
            if not os.path.isabs(data_dir):
                resolved_dir = resolve_profile_path(data_dir, allow_legacy=True)
            else:
                resolved_dir = data_dir

        os.makedirs(resolved_dir, exist_ok=True)
        self.data_dir = resolved_dir
        self.trades_file = os.path.join(resolved_dir, "comprehensive_trades.json")
        self.crt_signals_file = os.path.join(resolved_dir, "crt_signals.json")
        self.journal_file = os.path.join(resolved_dir, "trading_journal.json")
        self._log_callback = log_callback

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _log_event(
        self,
        message: str,
        *,
        level: int = logging.INFO,
        details: Dict[str, Any] | None = None,
    ) -> None:
        if self._log_callback:
            try:
                self._log_callback(
                    "TRADE_HISTORY", message, level=level, details=details
                )
                return
            except Exception:  # pragma: no cover - logging should not break workflow
                logging.getLogger(__name__).exception(
                    "Trade history log callback failed"
                )
        logging.getLogger("ai_trading_bot").log(level, "TRADE_HISTORY: %s", message)

    def load_trades(self) -> list[dict[str, Any]]:
        """Load all trades from disk."""
        try:
            if os.path.exists(self.trades_file):
                with open(self.trades_file, "r") as f:
                    return json.load(f)
        except Exception as exc:
            logging.getLogger(__name__).warning("Error loading trades: %s", exc)
        return []

    def save_trades(self, trades: Iterable[dict[str, Any]]) -> None:
        """Persist trade list to disk."""
        try:
            with open(self.trades_file, "w") as f:
                json.dump(list(trades), f, indent=2, default=str)
        except Exception as exc:
            logging.getLogger(__name__).error("Error saving trades: %s", exc)

    # ------------------------------------------------------------------
    # Trade lifecycle
    # ------------------------------------------------------------------
    def add_trade(self, trade_data: Dict[str, Any]) -> dict[str, Any] | None:
        """Add a new trade entry with extended metadata."""
        try:
            trades = self.load_trades()
            trade_record = {
                "trade_id": len(trades) + 1,
                "timestamp": datetime.now().isoformat(),
                "symbol": trade_data.get("symbol", "UNKNOWN"),
                "side": trade_data.get("side", "UNKNOWN"),
                "action_type": trade_data.get("type", "MANUAL"),
                "quantity": float(trade_data.get("quantity", 0)),
                "entry_price": float(trade_data.get("price", 0)),
                "total_value": float(trade_data.get("total", 0)),
                "exit_price": float(trade_data.get("exit_price", 0)),
                "pnl": float(trade_data.get("pnl", 0)),
                "pnl_percent": float(trade_data.get("pnl_percent", 0)),
                "signal": trade_data.get("signal", "UNKNOWN"),
                "confidence": float(trade_data.get("confidence", 0)),
                "strategy": trade_data.get("strategy", "BASIC"),
                "market_regime": trade_data.get("market_regime", "NEUTRAL"),
                "risk_adjustment": float(trade_data.get("risk_adjustment", 1.0)),
                "market_stress": float(trade_data.get("market_stress", 0)),
                "indicators_used": int(trade_data.get("indicators_used", 0)),
                "crt_signal": trade_data.get("crt_signal", {}),
                "advanced_stops_used": trade_data.get("advanced_stops_used", False),
                "position_size_percent": float(
                    trade_data.get("position_size_percent", 0)
                ),
                "holding_period_days": 0,
                "status": "OPEN" if trade_data.get("side") == "BUY" else "CLOSED",
                "execution_mode": trade_data.get("execution_mode", "paper"),
                "real_order_id": trade_data.get("real_order_id"),
                "profile": trade_data.get("profile"),
                "cost_basis": float(trade_data.get("cost_basis", 0.0)),
                "realized_gains": float(trade_data.get("realized_gains", 0.0)),
                "holding_period": int(trade_data.get("holding_period", 0)),
                "tax_lot_id": trade_data.get("tax_lot_id"),
            }
            trades.append(trade_record)
            self.save_trades(trades)
            self._log_event(
                f"Comprehensive trade recorded: {trade_record['symbol']} {trade_record['side']} | Qty: {trade_record['quantity']:.4f} | P&L: {trade_record['pnl_percent']:+.2f}%",
                level=logging.INFO,
            )
            return trade_record
        except Exception as exc:
            logging.getLogger(__name__).error("Error adding trade: %s", exc)
            return None

    def update_trade_exit(self, trade_id: int, exit_data: Dict[str, Any]) -> bool:
        """Update trade with exit information."""
        try:
            trades = self.load_trades()
            for trade in trades:
                if trade["trade_id"] == trade_id and trade["status"] == "OPEN":
                    trade.update(
                        {
                            "exit_price": float(exit_data.get("exit_price", 0)),
                            "pnl": float(exit_data.get("pnl", 0)),
                            "pnl_percent": float(exit_data.get("pnl_percent", 0)),
                            "exit_timestamp": datetime.now().isoformat(),
                            "status": "CLOSED",
                            "holding_period_days": self.calculate_holding_period(
                                trade["timestamp"]
                            ),
                            "realized_gains": float(
                                exit_data.get(
                                    "realized_gains", trade.get("realized_gains", 0.0)
                                )
                            ),
                            "holding_period": self.calculate_holding_period(
                                trade["timestamp"]
                            ),
                        }
                    )
                    break
            self.save_trades(trades)
            self._log_event(
                f"Trade {trade_id} updated with exit data", level=logging.INFO
            )
            return True
        except Exception as exc:
            logging.getLogger(__name__).error("Error updating trade exit: %s", exc)
            return False

    def calculate_holding_period(self, entry_timestamp: str) -> int:
        try:
            entry_date = datetime.fromisoformat(entry_timestamp)
            current_date = datetime.now()
            return (current_date - entry_date).days
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------
    def get_trade_history(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> list[Dict[str, Any]]:
        try:
            trades = self.load_trades()
            if filters:
                if "symbol" in filters:
                    trades = [t for t in trades if t.get("symbol") == filters["symbol"]]
                if "side" in filters:
                    trades = [t for t in trades if t.get("side") == filters["side"]]
                if "status" in filters:
                    trades = [t for t in trades if t.get("status") == filters["status"]]
                if "days" in filters:
                    cutoff_date = datetime.now() - timedelta(days=filters["days"])
                    trades = [
                        t
                        for t in trades
                        if safe_parse_datetime(t.get("timestamp"))
                        and safe_parse_datetime(t.get("timestamp")) >= cutoff_date
                    ]
                if "execution_mode" in filters:
                    desired_mode = filters["execution_mode"]
                    trades = [
                        t
                        for t in trades
                        if t.get("execution_mode", "paper") == desired_mode
                    ]
            trades.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return trades
        except Exception as exc:
            logging.getLogger(__name__).error("Error getting trade history: %s", exc)
            return []

    def get_trade_statistics(self) -> Dict[str, Any]:
        try:
            trades = self.load_trades()
            if not trades:
                return self._get_empty_statistics()

            closed_trades = [t for t in trades if t["status"] == "CLOSED"]
            open_trades = [t for t in trades if t["status"] == "OPEN"]

            total_trades = len(closed_trades)
            winning_trades = len([t for t in closed_trades if t["pnl"] > 0])
            losing_trades = len([t for t in closed_trades if t["pnl"] < 0])
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            total_pnl = sum(t["pnl"] for t in closed_trades)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            avg_win = (
                np.mean([t["pnl"] for t in closed_trades if t["pnl"] > 0])
                if winning_trades > 0
                else 0
            )
            avg_loss = (
                np.mean([t["pnl"] for t in closed_trades if t["pnl"] < 0])
                if losing_trades > 0
                else 0
            )

            pnl_std = (
                np.std([t["pnl"] for t in closed_trades])
                if len(closed_trades) > 1
                else 0
            )
            sharpe_ratio = (avg_pnl / pnl_std * np.sqrt(365)) if pnl_std > 0 else 0

            strategy_performance: Dict[str, Dict[str, Any]] = {}
            for trade in closed_trades:
                strategy = trade.get("strategy", "UNKNOWN")
                bucket = strategy_performance.setdefault(
                    strategy, {"trades": 0, "total_pnl": 0, "winning_trades": 0}
                )
                bucket["trades"] += 1
                bucket["total_pnl"] += trade["pnl"]
                if trade["pnl"] > 0:
                    bucket["winning_trades"] += 1

            symbol_performance: Dict[str, Dict[str, Any]] = {}
            for trade in closed_trades:
                symbol = trade["symbol"]
                bucket = symbol_performance.setdefault(
                    symbol, {"trades": 0, "total_pnl": 0, "winning_trades": 0}
                )
                bucket["trades"] += 1
                bucket["total_pnl"] += trade["pnl"]
                if trade["pnl"] > 0:
                    bucket["winning_trades"] += 1

            return {
                "summary": {
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "win_rate": win_rate,
                    "total_pnl": total_pnl,
                    "avg_pnl": avg_pnl,
                    "avg_win": avg_win,
                    "avg_loss": avg_loss,
                    "sharpe_ratio": sharpe_ratio,
                    "open_positions": len(open_trades),
                },
                "strategy_performance": strategy_performance,
                "symbol_performance": symbol_performance,
                "recent_trades": closed_trades[:10],
            }
        except Exception as exc:
            logging.getLogger(__name__).error(
                "Error calculating trade statistics: %s", exc
            )
            return self._get_empty_statistics()

    def _get_empty_statistics(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_pnl": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "sharpe_ratio": 0,
                "open_positions": 0,
            },
            "strategy_performance": {},
            "symbol_performance": {},
            "recent_trades": [],
        }

    # ------------------------------------------------------------------
    # Maintenance and exports
    # ------------------------------------------------------------------
    def clear_history(self) -> bool:
        cleared = False
        try:
            if os.path.exists(self.trades_file):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = f"{self.trades_file}.backup_{timestamp}"
                shutil.move(self.trades_file, backup_file)
                cleared = True
            for extra_file in (self.crt_signals_file, self.journal_file):
                if extra_file and os.path.exists(extra_file):
                    os.remove(extra_file)
                    cleared = True
            if cleared:
                self._log_event(
                    "Comprehensive trade history cleared (backup created)",
                    level=logging.INFO,
                )
            return cleared
        except Exception as exc:
            logging.getLogger(__name__).error("Error clearing history: %s", exc)
            return False

    def export_to_csv(self) -> Optional[str]:
        try:
            trades = self.load_trades()
            if trades:
                df = pd.DataFrame(trades)
                filename = f"comprehensive_trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                filepath = os.path.join(self.data_dir, filename)
                df.to_csv(filepath, index=False)
                return filepath
        except Exception as exc:
            logging.getLogger(__name__).error("Export error: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Journal support
    # ------------------------------------------------------------------
    def log_journal_event(
        self, event_type: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "payload": payload or {},
        }
        try:
            events = self._load_journal()
            events.append(event)
            self._save_journal(events)
        except Exception as exc:
            logging.getLogger(__name__).error("Journal logging error: %s", exc)
        return event

    def get_journal_events(
        self,
        limit: int = 50,
        event_type: Optional[str] = None,
        symbol: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        try:
            events = self._load_journal()
            if event_type:
                normalized_event = str(event_type).strip().lower()
                events = [
                    ev
                    for ev in events
                    if str(ev.get("event_type", "")).strip().lower() == normalized_event
                ]
            if symbol:
                target_symbol = str(symbol).strip().upper()
                events = [
                    ev
                    for ev in events
                    if str(ev.get("payload", {}).get("symbol", "")).strip().upper()
                    == target_symbol
                ]
            if search:
                query = str(search).strip().lower()

                def _matches(ev: Dict[str, Any]) -> bool:
                    if not query:
                        return True
                    if query in str(ev.get("event_type", "")).lower():
                        return True
                    payload = ev.get("payload", {}) or {}
                    if isinstance(payload, dict):
                        for value in payload.values():
                            if isinstance(value, str) and query in value.lower():
                                return True
                            if (
                                isinstance(value, (int, float))
                                and query in f"{value}".lower()
                            ):
                                return True
                            if isinstance(value, (list, tuple)):
                                joined = " ".join(str(item) for item in value)
                                if query in joined.lower():
                                    return True
                            if isinstance(value, dict):
                                if query in json.dumps(value).lower():
                                    return True
                    return False

                events = [ev for ev in events if _matches(ev)]

            events.sort(key=lambda ev: ev.get("timestamp", ""), reverse=True)
            if limit and limit > 0:
                events = events[:limit]
            return events
        except Exception as exc:
            logging.getLogger(__name__).error("Journal retrieval error: %s", exc)
            return []

    def clear_journal(self) -> bool:
        try:
            if os.path.exists(self.journal_file):
                os.remove(self.journal_file)
                return True
        except Exception as exc:
            logging.getLogger(__name__).error("Journal clear error: %s", exc)
        return False

    def _load_journal(self) -> list[Dict[str, Any]]:
        try:
            if os.path.exists(self.journal_file):
                with open(self.journal_file, "r") as f:
                    return json.load(f)
        except Exception as exc:
            logging.getLogger(__name__).error("Journal load error: %s", exc)
        return []

    def _save_journal(self, events: Iterable[Dict[str, Any]]) -> None:
        try:
            with open(self.journal_file, "w") as f:
                json.dump(list(events)[-500:], f, indent=2, default=str)
        except Exception as exc:
            logging.getLogger(__name__).error("Journal save error: %s", exc)
