#!/usr/bin/env python3
"""Cleanup utility for `trade_data/comprehensive_trades.json`.

This tool makes a timestamped backup of the current comprehensive trade log and
rewrites it according to the selected mode:

- sanitize (default): drop obviously invalid records (missing prices, empty PnL,
  zero quantities) and keep the latest instance per (symbol, side, entry_price,
  status) tuple.
- reset-open: discard historical rows entirely and repopulate the log with the
  currently open positions stored in `bot_persistence/bot_state.json`.

Example usage:
    ./scripts/clean_trade_history.py --sanitize
    ./scripts/clean_trade_history.py --reset-open

The script is intentionally conservative: if anything goes wrong, the original
file remains available under a timestamped backup in the same directory.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRADE_LOG = PROJECT_ROOT / "trade_data" / "comprehensive_trades.json"
BOT_STATE = PROJECT_ROOT / "bot_persistence" / "bot_state.json"


def _make_backup(path: Path) -> Path:
    if not path.exists():
        return path.with_name(f"{path.stem}_backup_{datetime.utcnow():%Y%m%dT%H%M%S}Z{path.suffix}")
    backup_path = path.with_name(
        f"{path.stem}_backup_{datetime.utcnow():%Y%m%dT%H%M%S}Z{path.suffix}"
    )
    backup_path.write_text(path.read_text())
    return backup_path


def _to_float(value) -> float:
    try:
        if value in (None, ""):
            return 0.0
        return float(value)
    except Exception:
        return 0.0


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def sanitize_trades(trades: Iterable[Dict]) -> List[Dict]:
    """Return a cleaned list of trade records."""
    sanitized: List[Dict] = []
    seen: Dict[Tuple, Dict] = {}

    for trade in trades:
        status = str(trade.get("status", "")).upper()
        entry_price = _to_float(trade.get("entry_price", 0))
        exit_price = _to_float(trade.get("exit_price", 0))
        quantity = _to_float(trade.get("quantity", 0))
        pnl = _to_float(trade.get("pnl", 0))

        if status not in {"OPEN", "CLOSED"}:
            continue
        if entry_price <= 0 and exit_price <= 0:
            continue
        if status == "OPEN" and quantity <= 0:
            continue
        if status == "CLOSED" and exit_price <= 0 and pnl == 0:
            # No evidence the order ever closed successfully.
            continue

        key = (
            trade.get("symbol"),
            status,
            trade.get("side"),
            round(entry_price, 8),
            round(exit_price, 8),
        )
        current = seen.get(key)
        timestamp = trade.get("timestamp") or trade.get("exit_timestamp")
        if current:
            current_ts = current.get("timestamp") or current.get("exit_timestamp")
            if current_ts and timestamp and timestamp <= current_ts:
                continue
        seen[key] = dict(trade)

    sanitized = list(seen.values())
    sanitized.sort(key=lambda t: (t.get("timestamp") or t.get("exit_timestamp") or ""))
    for idx, trade in enumerate(sanitized, start=1):
        trade["trade_id"] = idx
    return sanitized


def rebuild_from_positions() -> List[Dict]:
    state = _load_json(BOT_STATE, {})
    positions = state.get("trader_state", {}).get("positions", {}) or {}
    rebuilt: List[Dict] = []

    for idx, (symbol, details) in enumerate(sorted(positions.items()), start=1):
        qty = _to_float(details.get("quantity", 0))
        avg_price = _to_float(details.get("avg_price", 0))
        if qty == 0 or avg_price == 0:
            continue
        rebuilt.append(
            {
                "trade_id": idx,
                "timestamp": details.get("entry_time") or datetime.utcnow().isoformat(),
                "symbol": symbol,
                "side": "BUY" if qty > 0 else "SELL",
                "action_type": "RESET_FROM_PERSISTENCE",
                "quantity": abs(qty),
                "entry_price": avg_price,
                "total_value": abs(qty) * avg_price,
                "exit_price": 0.0,
                "pnl": 0.0,
                "pnl_percent": 0.0,
                "signal": details.get("signal_strength", "UNKNOWN"),
                "confidence": 0.0,
                "strategy": "RESET_FROM_PERSISTENCE",
                "market_regime": "UNKNOWN",
                "risk_adjustment": 1.0,
                "market_stress": 0.0,
                "indicators_used": 0,
                "crt_signal": details.get("advanced_stops", {}),
                "advanced_stops_used": bool(details.get("advanced_stops")),
                "position_size_percent": 0.0,
                "holding_period_days": 0,
                "status": "OPEN",
                "execution_mode": "live",
                "real_order_id": None,
                "profile": "ultimate",
            }
        )
    return rebuilt


def _write_trades(trades: List[Dict]) -> None:
    TRADE_LOG.parent.mkdir(parents=True, exist_ok=True)
    TRADE_LOG.write_text(json.dumps(trades, indent=2))


def run(mode: str) -> int:
    if not TRADE_LOG.exists() and mode == "sanitize":
        print("Trade log missing; nothing to sanitize.")
        return 0

    backup_path = _make_backup(TRADE_LOG)
    print(f"📦 Backup stored at: {backup_path}")

    if mode == "sanitize":
        current = _load_json(TRADE_LOG, [])
        cleaned = sanitize_trades(current)
        _write_trades(cleaned)
        print(f"🧹 Sanitized trade entries: kept {len(cleaned)}/{len(current)} records")
    else:  # reset-open
        rebuilt = rebuild_from_positions()
        _write_trades(rebuilt)
        print(f"🆕 Rebuilt trade log from active positions: {len(rebuilt)} records")

    return 0


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["sanitize", "reset-open"],
        default="sanitize",
        help="Cleanup mode to run",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":  # pragma: no cover
    args = parse_args(sys.argv[1:])
    sys.exit(run(args.mode))
