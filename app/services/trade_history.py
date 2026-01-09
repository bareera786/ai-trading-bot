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
from .persistence import _atomic_write_json


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

    def record_exchange_execution(self, execution: Dict[str, Any]) -> Dict[str, Any] | None:
        """Append a confirmed exchange execution record.

        This is intentionally strict and append-only:
        - Never overwrites existing rows
        - Best-effort de-duplicates by (exchange, binance_order_id)
        - Writes atomically to avoid partial files
        """

        if not isinstance(execution, dict):
            return None

        exchange = execution.get("exchange")
        order_id = execution.get("binance_order_id")
        if not exchange or order_id in (None, ""):
            return None

        try:
            trades = self.load_trades() or []
            exchange_norm = str(exchange).strip().upper()
            order_norm = str(order_id).strip()

            for existing in trades:
                try:
                    if str(existing.get("exchange") or "").strip().upper() != exchange_norm:
                        continue
                    if str(existing.get("binance_order_id") or "").strip() == order_norm:
                        return existing
                except Exception:
                    continue

            trades.append(dict(execution))
            _atomic_write_json(self.trades_file, trades)
            return execution
        except Exception as exc:
            logging.getLogger(__name__).error("Error recording exchange execution: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Trade lifecycle
    # ------------------------------------------------------------------
    @staticmethod
    def _infer_status(trade_data: Dict[str, Any]) -> str:
        status = trade_data.get("status")
        if isinstance(status, str):
            normalized = status.strip().upper()
            if normalized in {"OPEN", "CLOSED"}:
                return normalized

        side = str(trade_data.get("side") or "").strip().upper()

        try:
            exit_price = float(trade_data.get("exit_price") or 0)
        except Exception:
            exit_price = 0.0

        # Treat as CLOSED only when an explicit exit price exists.
        # (pnl/pnl_percent can be unrealized for open positions.)
        if exit_price != 0.0:
            return "CLOSED"

        # Legacy heuristic: BUY opens, SELL closes.
        if side == "SELL":
            return "CLOSED"
        return "OPEN"

    @staticmethod
    def _normalize_exit_price(
        *,
        status: str,
        trade_data: Dict[str, Any],
    ) -> float | None:
        if status == "OPEN":
            return None

        # If exit_price is provided, prefer it.
        raw_exit = trade_data.get("exit_price")
        if raw_exit not in (None, ""):
            try:
                exit_price = float(raw_exit)
                if exit_price > 0:
                    return exit_price
            except Exception:
                pass

        # Otherwise, fall back to other known keys. In this codebase, many
        # CLOSED trade records store the close execution price in `price`.
        for key in ("close_price", "price", "fill_price", "entry_price"):
            raw_val = trade_data.get(key)
            if raw_val in (None, ""):
                continue
            try:
                val = float(raw_val)
                if val > 0:
                    return val
            except Exception:
                continue

        return None

    def add_trade(self, trade_data: Dict[str, Any]) -> dict[str, Any] | None:
        """Add a new trade entry with extended metadata."""
        try:
            trades = self.load_trades()
            status = self._infer_status(trade_data)
            trade_record = {
                "trade_id": len(trades) + 1,
                "timestamp": datetime.now().isoformat(),
                "symbol": trade_data.get("symbol", "UNKNOWN"),
                "side": trade_data.get("side", "UNKNOWN"),
                "action_type": trade_data.get("type", "MANUAL"),
                "quantity": float(trade_data.get("quantity", 0)),
                "entry_price": float(trade_data.get("price", 0)),
                "total_value": float(trade_data.get("total", 0)),
                "exit_price": self._normalize_exit_price(status=status, trade_data=trade_data),
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
                "status": status,
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
                    normalized_exit_price = self._normalize_exit_price(
                        status="CLOSED",
                        trade_data={
                            **exit_data,
                            # Allow fallback to the original entry_price if
                            # the close execution price isn't supplied.
                            "entry_price": trade.get("entry_price"),
                        },
                    )
                    trade.update(
                        {
                            "exit_price": normalized_exit_price,
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

            persisted_futures_order_ids: set[str] = set()
            for trade in trades:
                try:
                    if str(trade.get("exchange") or "").strip().upper() != "BINANCE_FUTURES":
                        continue
                    order_id = trade.get("binance_order_id")
                    if order_id is not None and str(order_id).strip():
                        persisted_futures_order_ids.add(str(order_id).strip())
                except Exception:
                    continue

            # Normalize legacy values for display/API consumers.
            for trade in trades:
                status = str(trade.get("status") or "").upper()
                try:
                    exit_price = float(trade.get("exit_price") or 0)
                except Exception:
                    exit_price = 0.0

                if status == "OPEN":
                    if exit_price == 0.0:
                        trade["exit_price"] = None
                elif status == "CLOSED":
                    if exit_price == 0.0:
                        # In many records, `entry_price` represents the close execution price.
                        try:
                            entry_price = float(trade.get("entry_price") or 0)
                        except Exception:
                            entry_price = 0.0
                        if entry_price > 0:
                            trade["exit_price"] = entry_price

            # Also include futures trades from journal
            futures_trades = []
            journal_events = self.get_journal_events(event_type="FUTURES_ORDER")
            for event in journal_events:
                payload = event.get("payload", {})
                if payload:
                    raw_resp = payload.get("raw_response") if isinstance(payload, dict) else None
                    order_id = None
                    if isinstance(raw_resp, dict):
                        order_id = raw_resp.get("orderId")
                    if order_id is not None and str(order_id).strip() in persisted_futures_order_ids:
                        continue

                    # Convert journal event to trade format
                    trade_record = {
                        "trade_id": f"futures_{event.get('id', len(futures_trades) + 1)}",
                        "timestamp": payload.get("timestamp", event.get("timestamp")),
                        "symbol": payload.get("symbol"),
                        "side": payload.get("side"),
                        "action_type": "FUTURES_ORDER",
                        "quantity": float(payload.get("quantity", 0)),
                        "entry_price": 0.0,  # Futures orders don't have entry price in journal
                        "total_value": 0.0,
                        "exit_price": 0.0,
                        "pnl": 0.0,  # P&L not tracked in journal for futures
                        "status": payload.get("status", "UNKNOWN"),
                        "execution_mode": "futures",
                        "leverage": payload.get("leverage", 1),
                        "reduce_only": payload.get("reduce_only", False),
                        "testnet": payload.get("testnet", True),
                    }
                    futures_trades.append(trade_record)

            # Combine regular trades with futures trades
            all_trades = trades + futures_trades

            if filters:
                if "symbol" in filters:
                    all_trades = [t for t in all_trades if t.get("symbol") == filters["symbol"]]
                if "side" in filters:
                    all_trades = [t for t in all_trades if t.get("side") == filters["side"]]
                if "status" in filters:
                    all_trades = [t for t in all_trades if t.get("status") == filters["status"]]
                if "days" in filters:
                    cutoff_date = datetime.now() - timedelta(days=filters["days"])
                    all_trades = [
                        t
                        for t in all_trades
                        if safe_parse_datetime(t.get("timestamp"))
                        and safe_parse_datetime(t.get("timestamp")) >= cutoff_date
                    ]
                if "execution_mode" in filters:
                    desired_mode = filters["execution_mode"]
                    if desired_mode == "futures":
                        all_trades = [t for t in all_trades if t.get("execution_mode") == "futures"]
                    elif desired_mode in ["real", "paper"]:
                        all_trades = [t for t in all_trades if t.get("execution_mode") == desired_mode]
                    # For "all", include all trades

            # Sort using parsed datetimes when available so mixed timestamp
            # formats (ISO strings, numeric epochs) order correctly.
            all_trades.sort(
                key=lambda x: (safe_parse_datetime(x.get("timestamp")) or datetime.min),
                reverse=True,
            )
            return all_trades
        except Exception as exc:
            logging.getLogger(__name__).error("Error getting trade history: %s", exc)
            return []

    def get_trade_statistics(self) -> Dict[str, Any]:
        try:
            trades = self.load_trades()
            if not trades:
                return self._get_empty_statistics()

            # This file can contain heterogeneous records (legacy lifecycle trades
            # plus exchange execution confirmations). Only lifecycle trades have
            # the fields required for statistics.
            lifecycle_trades: list[dict[str, Any]] = []
            for trade in trades:
                try:
                    status = str(trade.get("status") or "").strip().upper()
                    if status not in {"OPEN", "CLOSED"}:
                        continue
                    pnl = trade.get("pnl")
                    if not isinstance(pnl, (int, float)):
                        continue
                    lifecycle_trades.append(trade)
                except Exception:
                    continue

            if not lifecycle_trades:
                return self._get_empty_statistics()

            closed_trades = [t for t in lifecycle_trades if t.get("status") == "CLOSED"]
            open_trades = [t for t in lifecycle_trades if t.get("status") == "OPEN"]

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
