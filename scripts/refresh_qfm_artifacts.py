#!/usr/bin/env python3
"""Rebuild Quantum Fusion Momentum artifacts from existing datasets."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_ml_auto_bot_final import (  # type: ignore  # pylint: disable=wrong-import-position
    TOP_SYMBOLS,
    format_year_label,
    resolve_profile_path,
    ultimate_ml_system,
    _normalize_symbol,
)


def _prepare_symbol_list(symbols: Iterable[str] | None, limit: int | None) -> List[str]:
    if symbols:
        normalized: List[str] = []
        for raw in symbols:
            norm = _normalize_symbol(raw)
            if norm:
                normalized.append(norm)
        target = normalized
    else:
        universe = TOP_SYMBOLS
        target = list(universe)

    deduped: List[str] = []
    seen = set()
    for sym in target:
        if sym not in seen:
            deduped.append(sym)
            seen.add(sym)

    if limit:
        deduped = deduped[:limit]
    if not deduped:
        raise ValueError("No symbols selected for artifact refresh.")
    return deduped


def _dataset_path(dataset_root: Path, symbol: str, interval: str, years: float) -> Path:
    suffix = format_year_label(years)
    filename = f"{symbol}_{interval}_{suffix}.csv"
    return dataset_root / filename


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Specific symbols to refresh (default: TOP_SYMBOLS list)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit processing to the first N symbols",
    )
    parser.add_argument(
        "--years",
        type=float,
        default=1.0,
        help="Dataset span in years (default: 1)",
    )
    parser.add_argument(
        "--interval",
        default="1h",
        help="Dataset interval label (default: 1h)",
    )
    parser.add_argument(
        "--dataset-dir",
        default=os.path.join("datasets", "binance_klines"),
        help="Relative directory containing datasets (default: datasets/binance_klines)",
    )
    args = parser.parse_args()

    symbols = _prepare_symbol_list(args.symbols, args.limit)
    dataset_root = Path(resolve_profile_path(args.dataset_dir))
    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset directory {dataset_root} does not exist")

    results = []
    failures = 0
    print(f"🔁 Refreshing QFM artifacts for {len(symbols)} symbols from {dataset_root}")

    for idx, symbol in enumerate(symbols, start=1):
        dataset_file = _dataset_path(dataset_root, symbol, args.interval, args.years)
        print(f"[{idx}/{len(symbols)}] {symbol}:", end=" ")
        if not dataset_file.exists():
            failures += 1
            print(f"❌ missing dataset {dataset_file.name}")
            results.append({
                "symbol": symbol,
                "status": "missing_dataset",
                "dataset": str(dataset_file),
            })
            continue

        try:
            df = pd.read_csv(dataset_file)
            entry = ultimate_ml_system.build_qfm_artifact(
                symbol,
                df,
                interval=args.interval,
                years=args.years,
                dataset_path=str(dataset_file.relative_to(PROJECT_ROOT)),
            )
            if not entry:
                raise RuntimeError("artifact entry not returned")
            results.append({
                "symbol": symbol,
                "rows": entry.get("rows"),
                "feature_matrix": entry.get("feature_matrix"),
                "updated_at": entry.get("updated_at"),
            })
            print("✅ artifact refreshed")
        except Exception as exc:  # pylint: disable=broad-except
            failures += 1
            print(f"❌ failed ({exc})")
            results.append({
                "symbol": symbol,
                "status": "error",
                "error": str(exc),
            })

    summary_path = dataset_root / f"qfm_refresh_summary_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)

    print(f"📄 Summary saved to {summary_path}")
    print(json.dumps(results, indent=2))

    if failures:
        print(f"❌ Completed with {failures} failures", file=sys.stderr)
        return 1

    print("🎉 All artifacts refreshed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
