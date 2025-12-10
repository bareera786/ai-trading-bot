#!/usr/bin/env python3
"""Runtime status diagnostics for the trading bot.

This command-line utility consumes the JSON payload exposed by
``/api/status`` (or a saved copy of that payload) and performs a series of
health checks:

* Track ensemble/model accuracy versus a configurable floor.
* Ensure models are retraining on schedule (no stale artifacts).
* Confirm a minimum indicator count so new features like SuperTrend are live.
* Verify trading remains enabled and that the system is generating activity.

The script prints a concise report with actionable warnings and returns a
non-zero exit code when checks fail, making it suitable for CI, cron-based
monitoring, or quick manual audits.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import requests
except Exception:  # pragma: no cover - optional dependency for local file usage
    requests = None  # type: ignore


StatusPayload = Dict[str, Any]


@dataclass(frozen=True)
class StatusThresholds:
    """Alerting thresholds for runtime diagnostics."""

    min_accuracy_percent: float = 50.0
    max_model_age_hours: float = 18.0
    min_indicator_count: int = 30
    min_total_trades: int = 1
    fail_on_warning: bool = False


@dataclass(frozen=True)
class StatusIssue:
    """A failure or warning discovered during diagnostics."""

    scope: str
    message: str
    severity: str = "warning"  # Either "warning" or "error"

    def __post_init__(self) -> None:
        if self.severity not in {"warning", "error"}:
            raise ValueError(f"Invalid severity: {self.severity}")


def looks_like_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def load_status_payload(source: str, *, timeout: float = 5.0) -> StatusPayload:
    """Load the bot status payload from a URL or local JSON file."""

    if looks_like_url(source):
        if requests is None:
            raise SystemExit(
                "requests is required to fetch status over HTTP. Install requests or provide a local JSON file."
            )
        try:
            response = requests.get(source, timeout=timeout)
            response.raise_for_status()
        except (
            Exception
        ) as exc:  # pragma: no cover - network errors are runtime concerns
            raise SystemExit(f"Failed to fetch status from {source}: {exc}") from exc
        try:
            return response.json()
        except (
            Exception
        ) as exc:  # pragma: no cover - payload issues are runtime concerns
            raise SystemExit(
                f"Response from {source} was not valid JSON: {exc}"
            ) from exc

    path = Path(source)
    if not path.exists():
        raise SystemExit(f"Status file not found: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Status file is not valid JSON: {path}\n{exc}") from exc


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def analyze_profile(
    name: str, profile: Dict[str, Any], thresholds: StatusThresholds
) -> List[StatusIssue]:
    issues: List[StatusIssue] = []
    summary = profile.get("summary") or {}

    avg_accuracy = _safe_float(summary.get("avg_accuracy_percent"))
    if avg_accuracy is None:
        avg_accuracy = _safe_float(summary.get("avg_accuracy"))
    if avg_accuracy is not None and avg_accuracy < thresholds.min_accuracy_percent:
        issues.append(
            StatusIssue(
                scope=name,
                message=(
                    f"Average accuracy {avg_accuracy:.2f}% below minimum {thresholds.min_accuracy_percent:.2f}%"
                ),
                severity="error",
            )
        )

    low_accuracy_models = _safe_int(summary.get("low_accuracy_models")) or 0
    if low_accuracy_models:
        threshold = summary.get("low_accuracy_threshold")
        threshold_str = (
            f"< {threshold}%" if threshold is not None else "below accuracy floor"
        )
        issues.append(
            StatusIssue(
                scope=name,
                message=f"{low_accuracy_models} models {threshold_str}",
                severity="error",
            )
        )

    stale_models = _safe_int(summary.get("stale_models")) or 0
    stale_threshold = _safe_float(summary.get("stale_threshold_hours"))
    if stale_models:
        limit = (
            stale_threshold
            if stale_threshold is not None
            else thresholds.max_model_age_hours
        )
        issues.append(
            StatusIssue(
                scope=name,
                message=f"{stale_models} models stale beyond {limit:.1f}h",
                severity="error",
            )
        )

    latest_age_hours = _safe_float(summary.get("latest_training_age_hours"))
    if latest_age_hours is None:
        latest_age_hours = _safe_float(summary.get("latest_training_age"))
    if (
        latest_age_hours is not None
        and latest_age_hours > thresholds.max_model_age_hours
    ):
        issues.append(
            StatusIssue(
                scope=name,
                message=(
                    f"Latest training age {latest_age_hours:.1f}h exceeds {thresholds.max_model_age_hours:.1f}h"
                ),
                severity="warning",
            )
        )

    model_count = _safe_int(summary.get("model_count"))
    if model_count is not None and model_count == 0:
        issues.append(
            StatusIssue(
                scope=name,
                message="No models loaded for profile",
                severity="error",
            )
        )

    return issues


def analyze_system(
    scope: str, system_status: Dict[str, Any], thresholds: StatusThresholds
) -> List[StatusIssue]:
    issues: List[StatusIssue] = []
    if not system_status:
        return [
            StatusIssue(scope=scope, message="System status missing", severity="error")
        ]

    if not system_status.get("trading_enabled", True):
        issues.append(
            StatusIssue(scope=scope, message="Trading disabled", severity="error")
        )

    if system_status.get("ml_system_available") is False:
        issues.append(
            StatusIssue(scope=scope, message="ML system unavailable", severity="error")
        )

    if not system_status.get("models_loaded", True):
        issues.append(
            StatusIssue(scope=scope, message="Models not loaded", severity="error")
        )

    if not system_status.get("ensemble_active", True):
        issues.append(
            StatusIssue(scope=scope, message="Ensemble inactive", severity="warning")
        )

    indicators_used = _safe_int(system_status.get("indicators_used"))
    if indicators_used is not None and indicators_used < thresholds.min_indicator_count:
        issues.append(
            StatusIssue(
                scope=scope,
                message=(
                    f"Only {indicators_used} indicators active (< {thresholds.min_indicator_count})"
                ),
                severity="error",
            )
        )

    last_trade = system_status.get("last_trade")
    if not last_trade:
        issues.append(
            StatusIssue(
                scope=scope,
                message="No trades recorded yet",
                severity="warning",
            )
        )

    return issues


def analyze_performance(
    scope: str, performance: Dict[str, Any], thresholds: StatusThresholds
) -> List[StatusIssue]:
    issues: List[StatusIssue] = []
    if not performance:
        return issues

    total_trades = _safe_int(performance.get("total_trades")) or 0
    if total_trades < thresholds.min_total_trades:
        issues.append(
            StatusIssue(
                scope=scope,
                message=(
                    f"Only {total_trades} trades executed (< {thresholds.min_total_trades})"
                ),
                severity="warning",
            )
        )

    win_rate = _safe_float(performance.get("win_rate"))
    if win_rate is not None and win_rate <= 0:
        issues.append(
            StatusIssue(
                scope=scope,
                message="Win rate is zero",
                severity="warning",
            )
        )

    return issues


def analyze_status(
    payload: StatusPayload, thresholds: StatusThresholds
) -> Tuple[List[StatusIssue], List[str]]:
    """Return a tuple of (issues, summary_lines)."""

    issues: List[StatusIssue] = []
    summaries: List[str] = []

    for profile_name in ("ultimate", "optimized"):
        profile = payload.get(profile_name)
        if not profile:
            continue
        profile_summary = profile.get("summary") or {}
        avg_acc = profile_summary.get("avg_accuracy_percent") or profile_summary.get(
            "avg_accuracy"
        )
        model_count = profile_summary.get("model_count")
        latest_training = profile_summary.get("latest_training_display")
        summaries.append(
            f"Profile {profile_name}: models={model_count}, avg_acc={avg_acc}, latest_training={latest_training}"
        )
        issues.extend(analyze_profile(profile_name, profile, thresholds))

    system_mappings = {
        "ultimate": payload.get("system_status"),
        "optimized": payload.get("optimized_system_status"),
    }
    for name, system_status in system_mappings.items():
        if system_status is None:
            if payload.get(name):
                issues.append(
                    StatusIssue(
                        scope=name, message="System status missing", severity="error"
                    )
                )
            continue

        summaries.append(
            f"System {name}: indicators={system_status.get('indicators_used')}, ensemble_active={system_status.get('ensemble_active')}"
        )
        issues.extend(analyze_system(name, system_status, thresholds))

    performance_sections = {
        "ultimate": payload.get("performance"),
        "optimized": payload.get("optimized_performance"),
    }
    for name, performance in performance_sections.items():
        if performance:
            summaries.append(
                f"Performance {name}: total_trades={performance.get('total_trades')}, win_rate={performance.get('win_rate')}"
            )
        issues.extend(analyze_performance(name, performance or {}, thresholds))

    return issues, summaries


def print_report(
    issues: List[StatusIssue], summaries: List[str], fail_on_warning: bool
) -> int:
    for line in summaries:
        print(line)

    if not issues:
        print("All diagnostics passed ✅")
        return 0

    print("Diagnostics identified the following issues:")
    for issue in issues:
        prefix = "[ERROR]" if issue.severity == "error" else "[WARN]"
        print(f"- {prefix} ({issue.scope}) {issue.message}")

    if any(issue.severity == "error" for issue in issues):
        return 1
    if fail_on_warning:
        return 1
    return 0


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose /api/status payload health checks."
    )
    parser.add_argument(
        "source",
        nargs="?",
        default=os.getenv("BOT_STATUS_SOURCE"),
        help="URL or JSON file path to the status payload. Defaults to BOT_STATUS_SOURCE environment variable.",
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=StatusThresholds.min_accuracy_percent,
        help="Minimum acceptable average accuracy percentage before alerting.",
    )
    parser.add_argument(
        "--max-model-age",
        type=float,
        default=StatusThresholds.max_model_age_hours,
        help="Maximum hours since the latest training run before alerting.",
    )
    parser.add_argument(
        "--min-indicators",
        type=int,
        default=StatusThresholds.min_indicator_count,
        help="Minimum indicator count expected in system status.",
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=StatusThresholds.min_total_trades,
        help="Minimum total trades expected in the performance snapshot.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="HTTP timeout when fetching a remote status URL (seconds).",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit with status 1 when any warnings are present (defaults to only failing on errors).",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    if not args.source:
        print(
            "No status source provided. Pass a URL/file or set BOT_STATUS_SOURCE.",
            file=sys.stderr,
        )
        return 2

    thresholds = StatusThresholds(
        min_accuracy_percent=args.min_accuracy,
        max_model_age_hours=args.max_model_age,
        min_indicator_count=args.min_indicators,
        min_total_trades=args.min_trades,
        fail_on_warning=args.fail_on_warnings,
    )

    payload = load_status_payload(args.source, timeout=args.timeout)
    issues, summaries = analyze_status(payload, thresholds)
    return print_report(issues, summaries, thresholds.fail_on_warning)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
