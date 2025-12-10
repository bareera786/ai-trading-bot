"""Health report management services."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, Mapping, Tuple

from prometheus_client import Counter, Gauge, Histogram


class HealthReportService:
    """Encapsulates periodic health report refresh with optional backtests."""

    def __init__(
        self,
        *,
        config: Mapping[str, Any],
        project_root: str,
        dashboard_data: Dict[str, Any],
        summary_evaluator: Callable[
            [Mapping[str, Any], Mapping[str, Any]], Dict[str, Any]
        ],
        lock: threading.Lock | None = None,
    ) -> None:
        self._config = dict(config)
        self._project_root = project_root
        self._dashboard_data = dashboard_data
        self._summary_evaluator = summary_evaluator
        self._lock = lock or threading.Lock()

        # Prometheus metrics
        self.health_check_counter = Counter('health_checks_total', 'Total number of health checks')
        self.health_check_duration = Histogram('health_check_duration_seconds', 'Time spent on health checks')
        self.system_health_gauge = Gauge('system_health_status', 'Current system health status (1=healthy, 0=unhealthy)')
        
        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge('circuit_breaker_state', 'Circuit breaker state (0=closed, 1=open, 2=half_open)')
        self.circuit_breaker_failures = Gauge('circuit_breaker_failures_total', 'Total circuit breaker failures')

    def refresh(self, *, run_backtest: bool) -> Dict[str, Any]:
        with self.health_check_duration.time():
            errors = []
            payload = None

            if run_backtest:
                backtest_error = self._run_health_backtests_if_enabled()
                if backtest_error:
                    errors.append(backtest_error)

            payload, load_error = self._load_health_report_payload(
            self._config["report_path"]
        )
        if load_error:
            errors.append(load_error)

        if payload:
            health_summary = self._summary_evaluator(payload, self._config)
            health_summary["generated_at"] = payload.get("generated_at")
            health_summary["source"] = self._config["report_path"]
        else:
            health_summary = self._empty_summary()

        health_summary["errors"] = errors
        health_summary["last_refresh"] = datetime.utcnow().isoformat()

        # Update Prometheus metrics
        self.health_check_counter.inc()
        self.system_health_gauge.set(1 if not errors else 0)
        
        # Update circuit breaker metrics
        circuit_breaker_data = self._dashboard_data.get("system_status", {}).get("circuit_breaker", {})
        if circuit_breaker_data:
            state_value = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}.get(circuit_breaker_data.get("state", "CLOSED"), 0)
            self.circuit_breaker_state.set(state_value)
            self.circuit_breaker_failures.set(circuit_breaker_data.get("failure_count", 0))

        with self._lock:
            self._dashboard_data.setdefault("health_report", {})
            self._dashboard_data["health_report"] = health_summary
            return health_summary

    def start_periodic_refresh(self) -> threading.Thread:
        interval = max(300, int(self._config.get("refresh_seconds", 3600)))
        thread = threading.Thread(
            target=self._refresh_loop, args=(interval,), daemon=True
        )
        thread.start()
        return thread

    # Internal helpers ------------------------------------------------------------------

    def _run_health_backtests_if_enabled(self) -> str | None:
        if not self._config.get("auto_run_backtests"):
            return None
        script_path = os.path.join(self._project_root, "scripts", "run_backtests.py")
        if not os.path.exists(script_path):
            return f"Backtest script missing at {script_path}"

        command = [
            sys.executable,
            script_path,
            "--years",
            str(self._config.get("backtest_years", 1)),
            "--interval",
            str(self._config.get("backtest_interval", "1d")),
            "--output",
            self._config["report_path"],
        ]

        symbols = self._config.get("symbols") or []
        if symbols:
            command.append("--symbols")
            command.extend(list(symbols))

        try:
            result = subprocess.run(
                command,
                cwd=self._project_root,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:  # pragma: no cover - defensive
            return f"Failed to execute backtest script: {exc}"

        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            return f"Backtest script failed (code {result.returncode}): {stderr[:4000]}"
        return None

    def _load_health_report_payload(
        self, path: str
    ) -> Tuple[Dict[str, Any] | None, str | None]:
        if not os.path.exists(path):
            return None, f"Report not found at {path}"
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle), None
        except json.JSONDecodeError as exc:
            return None, f"Report JSON decode error: {exc}"
        except Exception as exc:
            return None, f"Unable to read report: {exc}"

    def _empty_summary(self) -> Dict[str, Any]:
        return {
            "status": "unknown",
            "thresholds": {
                "min_total_return_pct": self._config["min_total_return_pct"],
                "min_sharpe_ratio": self._config["min_sharpe_ratio"],
                "max_drawdown_pct": self._config["max_drawdown_pct"],
            },
            "aggregate": {},
            "symbols": [],
            "breaches": [],
            "top_by_return": [],
            "top_by_sharpe": [],
            "errors": [],
            "source": self._config["report_path"],
        }

    def _refresh_loop(self, interval: int) -> None:
        while True:
            try:
                self.refresh(run_backtest=bool(self._config.get("auto_run_backtests")))
            except Exception as exc:  # pragma: no cover - defensive
                with self._lock:
                    self._dashboard_data.setdefault("health_report", {})
                    self._dashboard_data["health_report"]["errors"] = [
                        f"Health refresh failure: {exc}"
                    ]
                    self._dashboard_data["health_report"]["status"] = "unknown"
                    self._dashboard_data["health_report"][
                        "last_refresh"
                    ] = datetime.utcnow().isoformat()
            time.sleep(interval)


def evaluate_health_payload(
    payload: Mapping[str, Any], config: Mapping[str, Any]
) -> Dict[str, Any]:
    thresholds = {
        "min_total_return_pct": config["min_total_return_pct"],
        "min_sharpe_ratio": config["min_sharpe_ratio"],
        "max_drawdown_pct": config["max_drawdown_pct"],
    }

    symbol_summaries = payload.get("symbol_summaries", {}) or {}
    aggregate = payload.get("aggregate_summary", {}) or {}

    breaches = []
    evaluated_symbols = []

    for symbol in config.get("symbols", []):
        summary = symbol_summaries.get(symbol)
        if not summary:
            breaches.append(
                {
                    "symbol": symbol,
                    "metric": "missing",
                    "observed": None,
                    "expected": "present in report",
                }
            )
            continue

        total_return = float(summary.get("total_return_pct", 0.0))
        sharpe = float(summary.get("sharpe_ratio", 0.0))
        drawdown = float(summary.get("max_drawdown_pct", 0.0))

        evaluated_symbols.append(
            {
                "symbol": symbol,
                "total_return_pct": total_return,
                "sharpe_ratio": sharpe,
                "max_drawdown_pct": drawdown,
                "win_rate_pct": summary.get("win_rate_pct"),
                "profit_factor": summary.get("profit_factor"),
                "trades": summary.get("trades"),
            }
        )

        if total_return < thresholds["min_total_return_pct"]:
            breaches.append(
                {
                    "symbol": symbol,
                    "metric": "total_return_pct",
                    "observed": total_return,
                    "expected": f">= {thresholds['min_total_return_pct']}",
                }
            )
        if sharpe < thresholds["min_sharpe_ratio"]:
            breaches.append(
                {
                    "symbol": symbol,
                    "metric": "sharpe_ratio",
                    "observed": sharpe,
                    "expected": f">= {thresholds['min_sharpe_ratio']}",
                }
            )
        if drawdown > thresholds["max_drawdown_pct"]:
            breaches.append(
                {
                    "symbol": symbol,
                    "metric": "max_drawdown_pct",
                    "observed": drawdown,
                    "expected": f"<= {thresholds['max_drawdown_pct']}",
                }
            )

    ranked_by_return = sorted(
        evaluated_symbols, key=lambda item: item["total_return_pct"], reverse=True
    )
    ranked_by_sharpe = sorted(
        evaluated_symbols, key=lambda item: item["sharpe_ratio"], reverse=True
    )

    status = "healthy" if not breaches else "attention"

    return {
        "status": status,
        "thresholds": thresholds,
        "aggregate": aggregate,
        "symbols": evaluated_symbols,
        "breaches": breaches,
        "top_by_return": ranked_by_return[:3],
        "top_by_sharpe": ranked_by_sharpe[:3],
    }
