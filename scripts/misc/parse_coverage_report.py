#!/usr/bin/env python3
"""Parse pytest-cov / coverage.py text output into a sorted table.

Usage:
  ./.venv/bin/python parse_coverage_report.py path/to/pytest_output.txt

Notes:
- Looks for lines matching the coverage table rows ("Name  Stmts  Miss  Cover  Missing").
- If the file contains multiple coverage tables (e.g., multiple phases), the
  last occurrence for each file wins.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class CoverageRow:
    filename: str
    coverage_pct: int
    missing: str


_ROW_RE = re.compile(
    r"^\s*(?P<name>.+?)\s+"
    r"(?P<stmts>\d+)\s+"
    r"(?P<miss>\d+)\s+"
    r"(?P<cover>\d+)%\s*"
    r"(?P<missing>.*)$"
)


def _iter_coverage_rows(lines: Iterable[str]) -> Iterable[CoverageRow]:
    """Yield CoverageRow parsed from any coverage report table in the text."""
    in_table = False

    for raw in lines:
        line = raw.rstrip("\n")

        if not in_table:
            # pytest-cov typically prints a header like:
            # "Name  Stmts  Miss  Cover  Missing"
            if re.search(r"\bName\b\s+\bStmts\b\s+\bMiss\b\s+\bCover\b", line):
                in_table = True
            continue

        # End of table heuristics
        if not line.strip():
            in_table = False
            continue
        if line.lstrip().startswith("----"):
            continue
        if line.lstrip().startswith("TOTAL"):
            in_table = False
            continue

        match = _ROW_RE.match(line)
        if not match:
            # If we can’t parse a row, just skip it.
            continue

        name = match.group("name").strip()
        if name == "TOTAL":
            in_table = False
            continue

        cover = int(match.group("cover"))
        missing = match.group("missing").strip()
        yield CoverageRow(filename=name, coverage_pct=cover, missing=missing)


def _format_table(rows: List[CoverageRow], *, low_threshold: int, color: bool) -> str:
    file_width = max(len("File"), *(len(r.filename) for r in rows)) if rows else len("File")
    cov_width = len("Coverage %")
    miss_width = len("Missing Lines")

    def maybe_color_cov(pct: int) -> str:
        text = f"{pct}%"
        if pct >= low_threshold:
            return text
        if not color:
            return f"{text} (LOW)"
        # ANSI red
        return f"\x1b[31m{text}\x1b[0m"

    lines: List[str] = []
    lines.append(f"{'File':<{file_width}}  {'Coverage %':>{cov_width}}  Missing Lines")
    lines.append(f"{'-' * file_width}  {'-' * cov_width}  {'-' * miss_width}")

    for row in rows:
        cov_str = maybe_color_cov(row.coverage_pct)
        lines.append(f"{row.filename:<{file_width}}  {cov_str:>{cov_width}}  {row.missing}")

    return "\n".join(lines)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse pytest coverage report text and print a sorted table.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a text file containing pytest output with a coverage table.",
    )
    parser.add_argument(
        "--low-threshold",
        type=int,
        default=20,
        help="Highlight files with coverage below this percentage (default: 20).",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color highlighting.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if not args.path.exists():
        print(f"ERROR: File not found: {args.path}", file=sys.stderr)
        return 2

    text = args.path.read_text(encoding="utf-8", errors="replace")
    rows = list(_iter_coverage_rows(text.splitlines()))

    # If the file contains multiple phases, keep the last row per filename.
    by_file: Dict[str, CoverageRow] = {}
    for row in rows:
        by_file[row.filename] = row

    unique_rows = sorted(
        by_file.values(),
        key=lambda r: (r.coverage_pct, r.filename.lower()),
    )

    color = (not args.no_color) and sys.stdout.isatty()

    print("Coverage Report Summary")
    print(f"Total files listed: {len(unique_rows)}")
    print()
    print(
        _format_table(
            unique_rows,
            low_threshold=args.low_threshold,
            color=color,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
