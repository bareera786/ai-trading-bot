"""Backtesting service helpers and job manager."""
from __future__ import annotations

import json
import os
import threading
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, Mapping, MutableMapping, Optional, Sequence

import statistics as statistics_lib


BacktestSummary = Dict[str, Any]


def summarize_backtest_result(result: Mapping[str, Any] | None) -> BacktestSummary:
    """Normalize backtest result metrics for dashboard consumption."""
    result = result or {}
    trades = result.get('trades') or []
    total_return = float(result.get('total_return', 0.0)) * 100
    max_drawdown = float(result.get('max_drawdown', 0.0)) * 100
    sharpe = float(result.get('sharpe_ratio', 0.0))
    win_rate = float(result.get('win_rate', 0.0))
    profit_factor = result.get('profit_factor')
    summary: BacktestSummary = {
        'total_return_pct': round(total_return, 2),
        'max_drawdown_pct': round(max_drawdown, 2),
        'sharpe_ratio': round(sharpe, 4),
        'win_rate_pct': round(win_rate, 2),
        'profits': float(result.get('final_balance', 0.0)),
        'trades': len(trades),
        'notes': result.get('notes', ''),
    }
    if profit_factor is not None and profit_factor != "inf":
        try:
            summary['profit_factor'] = round(float(profit_factor), 3)
        except Exception:
            summary['profit_factor'] = None
    else:
        summary['profit_factor'] = None
    return summary


def aggregate_backtest_summary(summary_map: Mapping[str, Optional[BacktestSummary]] | None) -> BacktestSummary:
    if not summary_map:
        return {}
    returns = [metrics['total_return_pct'] for metrics in summary_map.values() if metrics]
    sharpes = [metrics['sharpe_ratio'] for metrics in summary_map.values() if metrics]
    win_rates = [metrics['win_rate_pct'] for metrics in summary_map.values() if metrics]
    drawdowns = [metrics['max_drawdown_pct'] for metrics in summary_map.values() if metrics]
    aggregate = {
        'symbols': len(summary_map),
        'average_return_pct': round(statistics_lib.mean(returns), 2) if returns else 0.0,
        'average_sharpe': round(statistics_lib.mean(sharpes), 4) if sharpes else 0.0,
        'average_win_rate_pct': round(statistics_lib.mean(win_rates), 2) if win_rates else 0.0,
        'average_drawdown_pct': round(statistics_lib.mean(drawdowns), 2) if drawdowns else 0.0,
    }
    return aggregate


class BacktestManager:
    """Manage asynchronous backtesting jobs and store recent results."""

    def __init__(
        self,
        *,
        symbol_normalizer: Callable[[str], Optional[str]],
        active_universe_provider: Callable[[], Iterable[str]],
        top_symbols_provider: Callable[[], Sequence[str]],
        resolve_profile_path: Callable[[str], str],
        ultimate_system_factory: Callable[[], Any],
        optimized_system_factory: Callable[[], Any],
        ultimate_live_system: Any,
        optimized_live_system: Any,
        history_limit: int = 20,
    ) -> None:
        self._symbol_normalizer = symbol_normalizer
        self._active_universe_provider = active_universe_provider
        self._top_symbols_provider = top_symbols_provider
        self._resolve_profile_path = resolve_profile_path
        self._ultimate_system_factory = ultimate_system_factory
        self._optimized_system_factory = optimized_system_factory
        self._ultimate_live_system = ultimate_live_system
        self._optimized_live_system = optimized_live_system

        self._lock = threading.RLock()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._history: deque[Dict[str, Any]] = deque(maxlen=history_limit)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._active_job_id: Optional[str] = None

    def submit(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        job_id = uuid.uuid4().hex
        job = {
            'id': job_id,
            'status': 'queued',
            'submitted_at': datetime.utcnow().isoformat(),
            'started_at': None,
            'finished_at': None,
            'progress': 0,
            'current_symbol': None,
            'mode': payload.get('mode', 'ultimate'),
            'parameters': self._sanitize_parameters(payload),
            'summary': {},
            'aggregate': {},
            'report_path': None,
            'failures': {},
            'promotion': None,
            'error': None,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._active_job_id = job_id
        self._executor.submit(self._run_job, job_id, payload)
        return dict(job)

    def list_jobs(self) -> list[Dict[str, Any]]:
        with self._lock:
            return [self._serialize_job(job) for job in self._jobs.values()]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return self._serialize_job(job) if job else None

    def get_active_job(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._active_job_id:
                return None
            job = self._jobs.get(self._active_job_id)
            return self._serialize_job(job)

    def get_history(self) -> list[Dict[str, Any]]:
        with self._lock:
            return [self._serialize_job(job) for job in self._history]

    # Internal helpers ---------------------------------------------------------------------

    def _run_job(self, job_id: str, payload: Mapping[str, Any]) -> None:
        self._update_job(job_id, status='running', started_at=datetime.utcnow().isoformat(), progress=1)
        try:
            result = self._execute_backtest(job_id, payload)
            self._update_job(
                job_id,
                status='completed',
                finished_at=datetime.utcnow().isoformat(),
                progress=100,
                summary=result.get('summary', {}),
                aggregate=result.get('aggregate', {}),
                report_path=result.get('report_path'),
                failures=result.get('failures', {}),
                promotion=result.get('promotion'),
            )
        except Exception as exc:  # pragma: no cover - defensive log path
            self._update_job(
                job_id,
                status='failed',
                finished_at=datetime.utcnow().isoformat(),
                error=str(exc),
            )
            print(f"❌ Backtest job {job_id} failed: {exc}")
        finally:
            with self._lock:
                job_snapshot = deepcopy(self._jobs.get(job_id))
                if job_snapshot:
                    self._history.appendleft(job_snapshot)
                if self._active_job_id == job_id:
                    self._active_job_id = None

    def _execute_backtest(self, job_id: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        symbols = payload.get('symbols') or []
        normalized_symbols = self._normalize_symbols(symbols)
        if not normalized_symbols:
            normalized_symbols = list(self._active_universe_provider()) or list(self._top_symbols_provider())

        mode = (payload.get('mode') or 'ultimate').lower()
        use_optimized = mode == 'optimized'
        years = float(payload.get('years', 1.0) or 1.0)
        interval = str(payload.get('interval') or '1d')
        initial_balance = float(payload.get('initial_balance', 1000.0) or 1000.0)
        use_real_data = not bool(payload.get('use_fallback_data', False))
        save_report = payload.get('save_report', True)
        profile_override = payload.get('profile')
        promote_on_success = bool(payload.get('promote_on_success', False))
        min_return = float(payload.get('min_return_pct', 5.0) or 0.0)
        min_sharpe = float(payload.get('min_sharpe', 0.5) or 0.0)

        original_profile = os.environ.get('BOT_PROFILE')
        if profile_override:
            os.environ['BOT_PROFILE'] = str(profile_override).strip()

        system_factory = self._optimized_system_factory if use_optimized else self._ultimate_system_factory
        system = system_factory()

        summary: Dict[str, Optional[BacktestSummary]] = {}
        failures: Dict[str, str] = {}
        progress_step = 80 / max(1, len(normalized_symbols))
        current_progress = 5

        for symbol in normalized_symbols:
            self._update_job(job_id, current_symbol=symbol, progress=min(95, int(current_progress)))
            try:
                result = system.comprehensive_backtest(
                    symbol,
                    years=years,
                    interval=interval,
                    initial_balance=initial_balance,
                    use_real_data=use_real_data,
                )
                summary[symbol] = summarize_backtest_result(result)
            except Exception as exc:  # pragma: no cover - defensive path
                failures[symbol] = str(exc)
                summary[symbol] = None
            current_progress += progress_step

        aggregate = aggregate_backtest_summary({k: v for k, v in summary.items() if v})
        report_path = None

        if save_report and summary:
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            report_dir = self._resolve_profile_path(os.path.join('bot_persistence', 'backtests'))
            os.makedirs(report_dir, exist_ok=True)
            filename = f"backtest_{mode}_{timestamp}.json"
            report_path = os.path.join(report_dir, filename)
            payload_dump = {
                'generated_at': timestamp,
                'profile': os.environ.get('BOT_PROFILE', original_profile or 'default'),
                'mode': mode,
                'parameters': {
                    'symbols': normalized_symbols,
                    'years': years,
                    'interval': interval,
                    'initial_balance': initial_balance,
                    'use_real_data': use_real_data,
                },
                'aggregate_summary': aggregate,
                'symbol_summaries': summary,
                'results': system.get_backtest_results(),
                'failures': failures,
            }
            with open(report_path, 'w', encoding='utf-8') as handle:
                json.dump(payload_dump, handle, indent=2, default=str)

        promotion_result = None
        if promote_on_success and aggregate:
            meets_return = aggregate.get('average_return_pct', 0) >= min_return
            meets_sharpe = aggregate.get('average_sharpe', 0) >= min_sharpe
            if meets_return and meets_sharpe:
                promotion_result = self._promote_models(normalized_symbols, use_optimized, use_real_data)
            else:
                promotion_result = {
                    'promoted': False,
                    'reason': f"Performance thresholds not met (return≥{min_return}, sharpe≥{min_sharpe})",
                }

        if profile_override is not None:
            if original_profile is None:
                os.environ.pop('BOT_PROFILE', None)
            else:
                os.environ['BOT_PROFILE'] = original_profile

        return {
            'summary': summary,
            'aggregate': aggregate,
            'report_path': report_path,
            'failures': failures,
            'promotion': promotion_result,
        }

    def _promote_models(self, symbols: Iterable[str], use_optimized: bool, use_real_data: bool) -> Dict[str, Any]:
        promoted: list[str] = []
        failed: Dict[str, str] = {}
        system = self._optimized_live_system if use_optimized else self._ultimate_live_system
        for symbol in symbols:
            try:
                trained = system.train_ultimate_model(symbol, use_real_data=use_real_data)
                if trained:
                    promoted.append(symbol)
                else:
                    failed[symbol] = 'Training skipped or failed'
            except Exception as exc:  # pragma: no cover - defensive path
                failed[symbol] = str(exc)
        return {
            'promoted': bool(promoted),
            'symbols': promoted,
            'failed': failed,
        }

    def _sanitize_parameters(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        allowed = {
            'symbols',
            'mode',
            'years',
            'interval',
            'initial_balance',
            'use_fallback_data',
            'profile',
            'promote_on_success',
            'min_return_pct',
            'min_sharpe',
            'save_report',
        }
        sanitized: Dict[str, Any] = {}
        for key in allowed:
            if key in payload:
                sanitized[key] = payload[key]
        return sanitized

    def _normalize_symbols(self, symbols: Iterable[str] | None) -> list[str]:
        normalized: list[str] = []
        for symbol in symbols or []:
            normalized_symbol = self._symbol_normalizer(symbol)
            if normalized_symbol and normalized_symbol not in normalized:
                normalized.append(normalized_symbol)
        return normalized

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.update({k: v for k, v in updates.items() if v is not None or k in job})

    def _serialize_job(self, job: MutableMapping[str, Any] | None) -> Optional[Dict[str, Any]]:
        if not job:
            return None
        safe_job = dict(job)
        safe_job.pop('future', None)
        return safe_job