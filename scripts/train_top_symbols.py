#!/usr/bin/env python3
"""Download Binance candles for top symbols and retrain local ultimate models."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from ai_ml_auto_bot_final import (  # type: ignore  # pylint: disable=wrong-import-position
    TOP_SYMBOLS,
    resolve_profile_path,
    ultimate_ml_system,
    get_active_trading_universe,
    _normalize_symbol,
)


def _prepare_symbol_list(symbols: Iterable[str] | None, limit: int | None) -> List[str]:
    if symbols:
        normalized = []
        for raw in symbols:
            norm = _normalize_symbol(raw)
            if norm:
                normalized.append(norm)
        if not normalized:
            raise ValueError("No valid symbols were provided.")
        target = normalized
    else:
        universe = get_active_trading_universe()
        if not universe:
            universe = list(TOP_SYMBOLS)
        target = universe

    seen = set()
    deduped: List[str] = []
    for sym in target:
        if sym not in seen:
            deduped.append(sym)
            seen.add(sym)

    if limit:
        deduped = deduped[:limit]
    if not deduped:
        raise ValueError("No symbols selected after applying limit.")
    return deduped


def _format_year_label(years: float) -> str:
    if years.is_integer():
        return f"{int(years)}y"
    return f"{years:.1f}y"


def _save_dataset(df: pd.DataFrame, out_dir: str, symbol: str, interval: str, years: float) -> str:
    os.makedirs(out_dir, exist_ok=True)
    suffix = _format_year_label(years)
    filename = f"{symbol}_{interval}_{suffix}.csv"
    out_path = os.path.join(out_dir, filename)
    df.to_csv(out_path, index=False)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Specific symbols to retrain (default: top active trading universe)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Restrict processing to the first N symbols (default: 10)",
    )
    parser.add_argument(
        "--years",
        type=float,
        default=1.0,
        help="Number of years of candles to fetch per symbol (default: 1)",
    )
    parser.add_argument(
        "--interval",
        default="1h",
        help="Binance kline interval (default: 1h)",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join("datasets", "binance_klines"),
        help="Relative directory for saving downloaded candles (default: datasets/binance_klines)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip downloading if a CSV already exists for the symbol/interval/years tuple",
    )
    parser.add_argument(
        "--min-rows",
        type=int,
        default=200,
        help="Fail if fewer than this many rows are returned (default: 200)",
    )
    parser.add_argument(
        "--no-save",
        dest="save_csv",
        action="store_false",
        help="Do not persist datasets to disk",
    )
    parser.set_defaults(save_csv=True)

    args = parser.parse_args()

    try:
        symbols = _prepare_symbol_list(args.symbols, args.limit)
    except ValueError as exc:
        parser.error(str(exc))

    dataset_root = resolve_profile_path(args.output_dir)
    summary = []
    failures = 0

    print(
        f"📈 Starting download/training for {len(symbols)} symbols | interval={args.interval} | years={args.years}"
    )

    for idx, symbol in enumerate(symbols, start=1):
        print(f"\n[{idx}/{len(symbols)}] ⚙️ Processing {symbol}…")
        csv_path = None
        try:
            suffix = _format_year_label(args.years)
            candidate_path = os.path.join(dataset_root, f"{symbol}_{args.interval}_{suffix}.csv")
            if args.skip_existing and args.save_csv and os.path.exists(candidate_path):
                print(f"   ⏩ Skipping download for {symbol}; found existing {candidate_path}")
                df = pd.read_csv(candidate_path)
            else:
                df = ultimate_ml_system.get_real_historical_data(
                    symbol, years=args.years, interval=args.interval
                )

            if df is None or df.empty:
                raise RuntimeError("No data returned")
            if len(df) < args.min_rows:
                raise RuntimeError(f"Only {len(df)} rows fetched (< {args.min_rows})")

            if args.save_csv:
                csv_path = _save_dataset(df, dataset_root, symbol, args.interval, args.years)
                print(f"   💾 Saved dataset to {csv_path}")

            success = ultimate_ml_system.train_ultimate_model(
                symbol,
                data=df,
                use_real_data=True,
                interval=args.interval,
                years=args.years,
                dataset_path=csv_path,
            )
            if not success:
                raise RuntimeError("Model training returned False")

            summary.append({
                "symbol": symbol,
                "rows": len(df),
                "csv": csv_path,
                "trained_at": datetime.utcnow().isoformat(timespec="seconds"),
            })
            print(f"   ✅ Training complete for {symbol} ({len(df)} rows)")
        except Exception as exc:  # pylint: disable=broad-except
            failures += 1
            summary.append({
                "symbol": symbol,
                "error": str(exc),
                "csv": csv_path,
                "failed_at": datetime.utcnow().isoformat(timespec="seconds"),
            })
            print(f"   ❌ Failed for {symbol}: {exc}")

    print("\n📊 Run summary:")
    print(json.dumps(summary, indent=2))

    if failures:
        print(f"❌ Completed with {failures} failures", file=sys.stderr)
        return 1

    print("🎉 All symbols processed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
