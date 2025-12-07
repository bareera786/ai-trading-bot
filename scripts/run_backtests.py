#!/usr/bin/env python3
"""Utility to run historical backtests using the bot's ML pipeline.

This script loads the Ultimate or Optimized ML training system from
`ai_ml_auto_bot_final.py`, fetches historical candles (real Binance data or
fallback synthetic data), trains the embedded supervised model, and evaluates
performance metrics such as total return, drawdown, Sharpe ratio, and win rate.

Usage examples:
    # Run ultimate backtests for all default symbols (1 year of daily candles)
    ./scripts/run_backtests.py

    # Run optimized backtests on a custom subset using fallback data only
    ./scripts/run_backtests.py --optimized --symbols BTCUSDT ETHUSDT --use-fallback-data

    # Persist JSON results under the bot persistence directory
    ./scripts/run_backtests.py --save-json --years 2 --interval 4h
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from statistics import mean
from typing import Dict, Iterable, List, Optional


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run supervised backtests for the Ultimate AI Trading Bot.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Symbols to backtest (e.g. BTCUSDT ETHUSDT). Defaults to the bot's active universe.",
    )
    parser.add_argument(
        "--years",
        type=float,
        default=1.5,
        help="Number of years of historical data to request per symbol.",
    )
    parser.add_argument(
        "--interval",
        default="1d",
        help="Binance kline interval (e.g. 1d, 4h, 1h).",
    )
    parser.add_argument(
        "--initial-balance",
        type=float,
        default=1000.0,
        help="Starting balance for the virtual portfolio in the backtest.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Optional BOT_PROFILE to run under (per-profile persistence).",
    )
    parser.add_argument(
        "--optimized",
        action="store_true",
        help="Use the optimized ML system instead of the ultimate ensemble.",
    )
    parser.add_argument(
        "--use-fallback-data",
        action="store_true",
        help="Skip live Binance downloads and rely on synthetic fallback candles.",
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Persist full backtest results to bot_persistence/backtests/.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Explicit JSON output path. Overrides --save-json destination if provided.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce console output to a minimal summary.",
    )
    return parser


def _normalize_symbols(raw_symbols: Optional[Iterable[str]], normalize_fn) -> List[str]:
    if not raw_symbols:
        return []
    normalized = []
    for sym in raw_symbols:
        if not sym:
            continue
        normalized.append(normalize_fn(sym))
    return normalized


def _summarize_result(result: Dict) -> Dict[str, float]:
    """Extract key numeric metrics from a backtest payload."""
    trades = result.get("trades") or []
    return {
        "total_return_pct": round(float(result.get("total_return", 0.0)) * 100, 2),
        "sharpe_ratio": round(float(result.get("sharpe_ratio", 0.0)), 4),
        "max_drawdown_pct": round(float(result.get("max_drawdown", 0.0)) * 100, 2),
        "win_rate_pct": round(float(result.get("win_rate", 0.0)), 2),
        "profit_factor": round(float(result.get("profit_factor", 0.0)), 3) if result.get("profit_factor") is not None else None,
        "trades": len(trades),
        "notes": result.get("notes", ""),
    }


def main(argv: Optional[List[str]] = None) -> int:
    from app import create_app
    from app.runtime.builder import build_runtime_context
    from app.runtime.symbols import TOP_SYMBOLS, normalize_symbol as _normalize_symbol
    from app.services.pathing import resolve_profile_path

    app = create_app()
    with app.app_context():
        context = build_runtime_context()

        parser = _build_arg_parser()
        args = parser.parse_args(argv)

        if args.profile:
            os.environ["BOT_PROFILE"] = args.profile

        system = context['optimized_ml_system'] if args.optimized else context['ultimate_ml_system']

        target_symbols = _normalize_symbols(args.symbols, _normalize_symbol)
        if not target_symbols:
            target_symbols = list(TOP_SYMBOLS)

        if not args.quiet:
            mode = "Optimized" if args.optimized else "Ultimate"
            print(f"🚀 Running {mode} backtests | symbols={len(target_symbols)} | years={args.years} | interval={args.interval}\n")

    summary: Dict[str, Dict[str, float]] = {}
    failures: Dict[str, str] = {}

    for symbol in target_symbols:
        if not args.quiet:
            print(f"=== {symbol} ===")
        try:
            result = system.comprehensive_backtest(
                symbol,
                years=args.years,
                interval=args.interval,
                initial_balance=args.initial_balance,
                use_real_data=not args.use_fallback_data,
            )
        except Exception as exc:  # pragma: no cover - defensive
            failures[symbol] = str(exc)
            if not args.quiet:
                print(f"❌ Backtest failed: {exc}\n")
            continue

        summary[symbol] = _summarize_result(result)
        if not args.quiet:
            symbol_summary = summary[symbol]
            print(
                f"Return: {symbol_summary['total_return_pct']:.2f}% | "
                f"Sharpe: {symbol_summary['sharpe_ratio']:.4f} | "
                f"MDD: {symbol_summary['max_drawdown_pct']:.2f}% | "
                f"Win Rate: {symbol_summary['win_rate_pct']:.2f}% | "
                f"Trades: {symbol_summary['trades']}"
            )
            if symbol_summary.get("profit_factor") is not None:
                print(f"Profit Factor: {symbol_summary['profit_factor']:.3f}")
            if symbol_summary.get("notes") and symbol_summary["notes"] != "success":
                print(f"Notes: {symbol_summary['notes']}")
            print()

    full_results = system.get_backtest_results()

    aggregate = {}
    if summary:
        aggregate = {
            "symbols": len(summary),
            "average_return_pct": round(mean(v["total_return_pct"] for v in summary.values()), 2),
            "average_sharpe": round(mean(v["sharpe_ratio"] for v in summary.values()), 4),
            "average_win_rate_pct": round(mean(v["win_rate_pct"] for v in summary.values()), 2),
        }
        if not args.quiet:
            print("=== Aggregate Summary ===")
            print(json.dumps(aggregate, indent=2))
            print()

    if args.save_json or args.output:
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        if args.output:
            output_path = os.path.abspath(args.output)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
        else:
            backtest_dir = resolve_profile_path(os.path.join("bot_persistence", "backtests"))
            output_filename = f"backtest_{'optimized' if args.optimized else 'ultimate'}_{timestamp}.json"
            output_path = os.path.join(backtest_dir, output_filename)

        payload = {
            "generated_at": timestamp,
            "profile": os.environ.get("BOT_PROFILE", "default"),
            "mode": "optimized" if args.optimized else "ultimate",
            "parameters": {
                "symbols": target_symbols,
                "years": args.years,
                "interval": args.interval,
                "initial_balance": args.initial_balance,
                "use_real_data": not args.use_fallback_data,
            },
            "aggregate_summary": aggregate,
            "symbol_summaries": summary,
            "results": full_results,
            "failures": failures,
        }

        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=str)

        if not args.quiet:
            print(f"💾 Saved backtest report to {output_path}\n")

    if failures and not args.quiet:
        print("⚠️ Backtests with issues:")
        for symbol, message in failures.items():
            print(f"  - {symbol}: {message}")
        print()

    if not summary:
        if not args.quiet:
            print("No backtests completed successfully.")
        return 1

    if not args.quiet:
        print("✅ Backtesting run finished.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
