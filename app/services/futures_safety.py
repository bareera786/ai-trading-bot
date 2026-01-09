"""Futures safety gates (VPS-only) for launch-safe trading.

This module adds a conservative, non-blocking safety layer for futures entries:
- VPS-only rolling 24h backtest eligibility per symbol
- Market regime gate using ATR% and ADX
- Symbol hard-stops (max trades/day, max daily loss, max consecutive losses)
- Persistence across restarts and UTC midnight reset

It does not alter strategy/ML entry logic; it only blocks unsafe entries.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, MutableMapping, Optional

import pandas as pd

from app.services.backtest import summarize_backtest_result
from app.services.pathing import resolve_profile_path


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_day_key(ts: Optional[datetime] = None) -> str:
    ts = ts or _utc_now()
    return ts.strftime("%Y-%m-%d")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


@dataclass(frozen=True)
class FuturesSafetyConfig:
    enabled: bool = True
    vps_only: bool = True

    backtest_interval: str = "5m"
    backtest_window_days: float = 1.0
    backtest_refresh_minutes: int = 45
    min_backtest_trades: int = 5
    min_win_rate_pct: float = 52.0
    min_profit_factor: float = 1.05

    indicator_interval: str = "5m"
    indicator_lookback_days: float = 2.0
    atr_period: int = 14
    adx_period: int = 14
    min_atr_pct: float = 0.35
    min_adx: float = 18.0
    indicator_cache_seconds: int = 300

    max_trades_per_day: int = 6
    max_daily_loss_usdt: float = 25.0
    max_consecutive_losses: int = 3


class FuturesSafetyService:
    """Background evaluator + synchronous gate used by futures order submission."""

    def __init__(
        self,
        *,
        ultimate_trader: Any,
        trading_config: Mapping[str, Any],
        futures_symbols: list[str],
        bot_logger: Any | None = None,
        backtest_function: Any | None = None,
    ) -> None:
        self.ultimate_trader = ultimate_trader
        self.trading_config = dict(trading_config or {})
        self.futures_symbols = [str(s).upper() for s in (futures_symbols or [])]
        self.logger = bot_logger
        self.backtest_function = backtest_function  # Can be passed at init time

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

        # Resolve the profile-aware persistence directory first, then write
        # a single JSON file within it.
        self._state_path = os.path.join(
            resolve_profile_path("bot_persistence"), "futures_safety_state.json"
        )

        # Runtime state
        self.backtest: dict[str, dict[str, Any]] = {}
        self.indicators: dict[str, dict[str, Any]] = {}
        self.symbol_limits: dict[str, dict[str, Any]] = {}
        self.meta: dict[str, Any] = {"last_backtest": None, "last_save": None}

        self._load_state()
        self._reset_daily_if_needed()

        # Ensure the state file exists early (best-effort) so restarts don't
        # lose symbol limits/backtest eligibility due to missing persistence.
        if not os.path.exists(self._state_path):
            self._save_state_best_effort()

    # ------------------------- lifecycle -------------------------

    def start(self) -> bool:
        if self._thread and self._thread.is_alive():
            return True

        if not self._is_enabled_environment():
            self._log("ℹ️ FuturesSafetyService not started (non-production/local)")
            return False

        if not self._effective_config().enabled:
            self._log("ℹ️ FuturesSafetyService disabled by config")
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="FuturesSafetyLoop", daemon=True
        )
        self._thread.start()
        self._log("✅ FuturesSafetyService started")
        return True

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._thread = None
        self._log("🛑 FuturesSafetyService stopped")

    # ------------------------- gate API -------------------------

    def should_allow_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int,
        reduce_only: bool,
        trader: Any | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        symbol_u = str(symbol).upper()
        cfg = self._effective_config()

        active_trader = trader or self.ultimate_trader

        if not cfg.enabled:
            return True, "disabled", {}

        # Always allow reduce-only orders so we can exit/flatten risk.
        if reduce_only:
            return True, "reduce_only", {}

        self._reset_daily_if_needed()

        # Hard-stop: symbol disabled until UTC reset.
        with self._lock:
            limits = self.symbol_limits.get(symbol_u) or {}
            disabled_until = limits.get("disabled_until_utc_day")
            if disabled_until and disabled_until == _utc_day_key():
                return False, "SYMBOL_DISABLED_UNTIL_UTC_RESET", {
                    "symbol": symbol_u,
                    "disabled_until_utc_day": disabled_until,
                }

        # Backtest eligibility.
        allow_bt, bt_reason, bt_details = self._check_backtest(symbol_u, cfg)
        if not allow_bt:
            return False, bt_reason, bt_details

        # Regime gate (ATR/ADX).
        ok_regime, regime_reason, regime_details = self._check_regime(
            symbol_u, cfg, trader=active_trader
        )
        if not ok_regime:
            return False, regime_reason, regime_details

        # Risk limits from Binance realized PnL + local order counts.
        ok_risk, risk_reason, risk_details = self._check_risk_limits(
            symbol_u, cfg, trader=active_trader
        )
        if not ok_risk:
            return False, risk_reason, risk_details

        return True, "OK", {
            "symbol": symbol_u,
            "side": str(side).upper(),
            "quantity": quantity,
            "leverage": leverage,
        }

    def record_successful_entry(self, symbol: str) -> None:
        """Increment per-day trade counts for symbols when we actually place an entry."""
        symbol_u = str(symbol).upper()
        day = _utc_day_key()
        with self._lock:
            limits = self.symbol_limits.setdefault(symbol_u, {})
            if limits.get("utc_day") != day:
                limits["utc_day"] = day
                limits["trades_today"] = 0
                limits["consecutive_losses"] = 0
                limits["daily_realized_pnl_usdt"] = 0.0
                limits.pop("disabled_until_utc_day", None)
            limits["trades_today"] = _coerce_int(limits.get("trades_today"), 0) + 1
        self._save_state_best_effort()

    # ------------------------- checks -------------------------

    def _check_backtest(
        self, symbol: str, cfg: FuturesSafetyConfig
    ) -> tuple[bool, str, dict[str, Any]]:
        with self._lock:
            snapshot = self.backtest.get(symbol) or {}

        allowed = bool(snapshot.get("eligible", False))
        if allowed:
            return True, "BACKTEST_OK", {"symbol": symbol, **snapshot}

        # If no backtest yet, be conservative: block until computed.
        if not snapshot:
            return False, "TRADE_BLOCKED: BACKTEST_NOT_READY", {"symbol": symbol}

        return False, "TRADE_BLOCKED: BACKTEST_FAILED", {"symbol": symbol, **snapshot}

    def _check_regime(
        self, symbol: str, cfg: FuturesSafetyConfig, *, trader: Any
    ) -> tuple[bool, str, dict[str, Any]]:
        metrics = self._get_indicator_metrics(symbol, cfg, trader=trader)
        if not metrics:
            return False, "TRADE_BLOCKED: INDICATORS_UNAVAILABLE", {"symbol": symbol}

        atr_pct = _safe_float(metrics.get("atr_pct"), 0.0)
        adx = _safe_float(metrics.get("adx"), 0.0)

        if atr_pct < cfg.min_atr_pct:
            return (
                False,
                "TRADE_BLOCKED: ATR_TOO_LOW",
                {
                    "symbol": symbol,
                    "atr_pct": atr_pct,
                    "min_atr_pct": cfg.min_atr_pct,
                    "adx": adx,
                },
            )
        if adx < cfg.min_adx:
            return (
                False,
                "TRADE_BLOCKED: ADX_TOO_LOW",
                {
                    "symbol": symbol,
                    "adx": adx,
                    "min_adx": cfg.min_adx,
                    "atr_pct": atr_pct,
                },
            )

        return True, "REGIME_OK", {"symbol": symbol, "atr_pct": atr_pct, "adx": adx}

    def _check_risk_limits(
        self, symbol: str, cfg: FuturesSafetyConfig, *, trader: Any
    ) -> tuple[bool, str, dict[str, Any]]:
        self._refresh_realized_pnl_best_effort(symbol, trader=trader)

        with self._lock:
            limits = self.symbol_limits.get(symbol) or {}
            trades_today = _coerce_int(limits.get("trades_today"), 0)
            daily_pnl = _safe_float(limits.get("daily_realized_pnl_usdt"), 0.0)
            streak = _coerce_int(limits.get("consecutive_losses"), 0)

        if trades_today >= cfg.max_trades_per_day:
            self._disable_symbol_until_utc_reset(symbol)
            return (
                False,
                "TRADE_BLOCKED: MAX_TRADES_PER_DAY",
                {
                    "symbol": symbol,
                    "trades_today": trades_today,
                    "max_trades_per_day": cfg.max_trades_per_day,
                },
            )

        if daily_pnl <= -abs(cfg.max_daily_loss_usdt):
            self._disable_symbol_until_utc_reset(symbol)
            return (
                False,
                "TRADE_BLOCKED: MAX_DAILY_LOSS",
                {
                    "symbol": symbol,
                    "daily_realized_pnl_usdt": daily_pnl,
                    "max_daily_loss_usdt": cfg.max_daily_loss_usdt,
                },
            )

        if streak >= cfg.max_consecutive_losses:
            self._disable_symbol_until_utc_reset(symbol)
            return (
                False,
                "TRADE_BLOCKED: MAX_CONSECUTIVE_LOSSES",
                {
                    "symbol": symbol,
                    "consecutive_losses": streak,
                    "max_consecutive_losses": cfg.max_consecutive_losses,
                },
            )

        return True, "RISK_OK", {
            "symbol": symbol,
            "trades_today": trades_today,
            "daily_realized_pnl_usdt": daily_pnl,
            "consecutive_losses": streak,
        }

    # ------------------------- indicators -------------------------

    def _get_indicator_metrics(
        self, symbol: str, cfg: FuturesSafetyConfig
        , *, trader: Any
    ) -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            cached = self.indicators.get(symbol)
            if cached and _safe_float(cached.get("ts"), 0) + cfg.indicator_cache_seconds > now:
                return dict(cached)

        df = self._fetch_recent_candles(symbol, cfg, trader=trader)
        if df is None or df.empty:
            return None

        metrics = self._calculate_atr_adx(df, cfg)
        if not metrics:
            return None

        metrics["ts"] = now
        with self._lock:
            self.indicators[symbol] = dict(metrics)
        self._save_state_best_effort()
        return dict(metrics)

    def _fetch_recent_candles(
        self, symbol: str, cfg: FuturesSafetyConfig
        , *, trader: Any
    ) -> pd.DataFrame | None:
        # Use the legacy system's Binance fetching to avoid coupling.
        getter = getattr(trader, "get_real_historical_data", None)
        if not callable(getter):
            return None

        years = float(cfg.indicator_lookback_days) / 365.0
        try:
            data = getter(symbol, years=years, interval=cfg.indicator_interval)
        except Exception:
            return None
        if data is None:
            return None
        if not isinstance(data, pd.DataFrame):
            try:
                data = pd.DataFrame(data)
            except Exception:
                return None

        # Normalize columns.
        cols = {c.lower(): c for c in data.columns}
        for needed in ("high", "low", "close"):
            if needed not in cols:
                return None
        df: pd.DataFrame = data.copy()
        df.rename(
            columns={cols["high"]: "high", cols["low"]: "low", cols["close"]: "close"},
            inplace=True,
        )
        df = pd.DataFrame(df[["high", "low", "close"]].dropna())
        return df

    def _calculate_atr_adx(
        self, df: pd.DataFrame, cfg: FuturesSafetyConfig
    ) -> dict[str, Any] | None:
        if df is None or df.empty:
            return None

        n_atr = max(2, int(cfg.atr_period))
        n_adx = max(2, int(cfg.adx_period))

        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)
        prev_close = close.shift(1)

        tr = pd.concat(
            [
                (high - low).abs(),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
        tr = pd.Series(tr)

        atr = tr.ewm(alpha=1 / n_atr, adjust=False).mean()
        atr_pct = (atr / close.replace(0, pd.NA)) * 100

        up_move = high.diff()
        down_move = (-low.diff())

        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        tr_smoothed = tr.ewm(alpha=1 / n_adx, adjust=False).mean()
        plus_dm_smoothed = plus_dm.ewm(alpha=1 / n_adx, adjust=False).mean()
        minus_dm_smoothed = minus_dm.ewm(alpha=1 / n_adx, adjust=False).mean()

        plus_di = 100 * (plus_dm_smoothed / tr_smoothed.replace(0, pd.NA))
        minus_di = 100 * (minus_dm_smoothed / tr_smoothed.replace(0, pd.NA))
        dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, pd.NA))
        adx = dx.ewm(alpha=1 / n_adx, adjust=False).mean()

        last_atr_pct = float(atr_pct.dropna().iloc[-1]) if not atr_pct.dropna().empty else 0.0
        last_adx = float(adx.dropna().iloc[-1]) if not adx.dropna().empty else 0.0

        return {
            "atr_pct": round(last_atr_pct, 4),
            "adx": round(last_adx, 4),
        }

    # ------------------------- realized pnl -------------------------

    def _refresh_realized_pnl_best_effort(self, symbol: str, *, trader: Any) -> None:
        """Update per-day realized PnL + consecutive loss streak from Binance income history."""
        futures_trader = getattr(trader, "futures_trader", None)
        if futures_trader is None:
            return

        income_fn = getattr(futures_trader, "get_realized_pnl_income", None)
        if not callable(income_fn):
            return

        day = _utc_day_key()
        start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = start + timedelta(days=1)

        incomes: Any
        try:
            incomes = income_fn(symbol=symbol, start_time=start, end_time=end)
        except Exception:
            return

        # incomes: list[dict] with fields including time, income
        total = 0.0
        streak = 0
        last_was_loss = True

        if not isinstance(incomes, list):
            incomes = []

        entries = [i for i in incomes if isinstance(i, Mapping)]
        entries.sort(key=lambda x: _safe_float(x.get("time"), 0.0))

        for item in entries:
            inc = _safe_float(item.get("income"), 0.0)
            total += inc

        # consecutive losses: from end backwards
        for item in reversed(entries):
            inc = _safe_float(item.get("income"), 0.0)
            if inc < 0:
                streak += 1
                last_was_loss = True
                continue
            if inc > 0:
                last_was_loss = False
            break

        with self._lock:
            limits = self.symbol_limits.setdefault(symbol, {})
            if limits.get("utc_day") != day:
                limits["utc_day"] = day
                limits["trades_today"] = 0
                limits.pop("disabled_until_utc_day", None)
            limits["daily_realized_pnl_usdt"] = round(float(total), 8)
            limits["consecutive_losses"] = int(streak) if last_was_loss else 0

        self._save_state_best_effort()

    # ------------------------- disable/reset/persist -------------------------

    def _disable_symbol_until_utc_reset(self, symbol: str) -> None:
        day = _utc_day_key()
        with self._lock:
            limits = self.symbol_limits.setdefault(symbol, {})
            limits["disabled_until_utc_day"] = day
        self._save_state_best_effort()

    def _reset_daily_if_needed(self) -> None:
        day = _utc_day_key()
        with self._lock:
            for symbol, limits in list(self.symbol_limits.items()):
                if limits.get("utc_day") != day:
                    limits["utc_day"] = day
                    limits["trades_today"] = 0
                    limits["consecutive_losses"] = 0
                    limits["daily_realized_pnl_usdt"] = 0.0
                    limits.pop("disabled_until_utc_day", None)

    def _load_state(self) -> None:
        try:
            if not os.path.exists(self._state_path):
                return
            with open(self._state_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if isinstance(payload, dict):
                self.backtest = payload.get("backtest", {}) or {}
                self.indicators = payload.get("indicators", {}) or {}
                self.symbol_limits = payload.get("symbol_limits", {}) or {}
                self.meta = payload.get("meta", {}) or {}
        except Exception:
            # best-effort; safety service remains functional
            return

    def _save_state_best_effort(self) -> None:
        tmp: str | None = None
        try:
            os.makedirs(os.path.dirname(self._state_path), exist_ok=True)
            payload = {
                "meta": {**(self.meta or {}), "last_save": _utc_now().isoformat()},
                "backtest": self.backtest,
                "indicators": self.indicators,
                "symbol_limits": self.symbol_limits,
            }
            tmp = f"{self._state_path}.tmp.{os.getpid()}.{int(time.time())}"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, default=str)
            os.replace(tmp, self._state_path)
        except Exception:
            try:
                if tmp and os.path.exists(tmp):
                    os.unlink(tmp)
            except Exception:
                pass

    # ------------------------- backtest loop -------------------------

    def _run_loop(self) -> None:
        self._log("🧪 FuturesSafetyService loop started (running backtest checks)")
        while not self._stop_event.is_set():
            try:
                self._run_backtest_once()
            except Exception as exc:  # pragma: no cover
                self._log(f"⚠️ FuturesSafetyService backtest loop error: {exc}")
            self._stop_event.wait(self._get_interval_seconds())

    def _run_backtest_once(self) -> None:
        cfg = self._effective_config()
        if not cfg.enabled:
            self._log("ℹ️ FuturesSafetyService backtest disabled (futures_safety_enabled=False)")
            return

        # Try to use the function passed at init, or fall back to trader method
        backtest_fn = self.backtest_function or getattr(self.ultimate_trader, "comprehensive_backtest", None)
        if not callable(backtest_fn):
            self._log("⚠️ FuturesSafetyService: comprehensive_backtest not available (will try next cycle)")
            return

        years = float(cfg.backtest_window_days) / 365.0
        symbols = list(self.futures_symbols)

        # Mark start and persist early so operators can confirm the loop is alive
        # even if individual symbol backtests are slow.
        with self._lock:
            self.meta["last_backtest_started"] = _utc_now().isoformat()
            self.meta["last_backtest_symbols_total"] = len(symbols)
        self._log(
            f"🧪 FuturesSafetyService backtest started (symbols={len(symbols)}, interval={cfg.backtest_interval}, window_days={cfg.backtest_window_days})"
        )
        self._save_state_best_effort()

        # If we have no symbols configured, record a heartbeat so the state file
        # doesn't look stuck.
        if not symbols:
            with self._lock:
                self.backtest = {}
                self.meta["last_backtest"] = _utc_now().isoformat()
                self.meta["last_backtest_symbols_completed"] = 0
            self._save_state_best_effort()
            return

        results: dict[str, dict[str, Any]] = {}

        completed = 0
        eligible_count = 0
        for symbol in symbols:
            if self._stop_event.is_set():
                break
            try:
                raw = backtest_fn(
                    symbol,
                    years=years,
                    interval=cfg.backtest_interval,
                    initial_balance=1000.0,
                    use_real_data=True,
                )
                summary = summarize_backtest_result(raw if isinstance(raw, Mapping) else {})
            except Exception:
                summary = {}

            win_rate = _safe_float(summary.get("win_rate_pct"), 0.0)
            pf = summary.get("profit_factor")
            pf_f = _safe_float(pf, 0.0) if pf is not None else 0.0
            trades = _coerce_int(summary.get("trades"), 0)

            eligible = bool(
                trades >= cfg.min_backtest_trades
                and win_rate >= cfg.min_win_rate_pct
                and pf_f >= cfg.min_profit_factor
            )

            completed += 1
            if eligible:
                eligible_count += 1

            results[symbol] = {
                "generated_at": _utc_now().isoformat(),
                "eligible": eligible,
                "win_rate_pct": win_rate,
                "profit_factor": pf_f,
                "trades": trades,
                "total_return_pct": _safe_float(summary.get("total_return_pct"), 0.0),
                "max_drawdown_pct": _safe_float(summary.get("max_drawdown_pct"), 0.0),
            }

            # Persist incremental progress so a long run is observable.
            with self._lock:
                self.backtest[symbol] = results[symbol]
                self.meta["last_backtest_symbols_completed"] = completed
                self.meta["last_backtest_symbols_eligible"] = eligible_count
                self.meta["last_backtest_progress_utc"] = _utc_now().isoformat()
            if completed == 1 or completed % 5 == 0:
                self._save_state_best_effort()

        with self._lock:
            self.backtest = results
            self.meta["last_backtest"] = _utc_now().isoformat()
            self.meta["last_backtest_symbols_completed"] = completed
            self.meta["last_backtest_symbols_eligible"] = eligible_count

        self._save_state_best_effort()
        self._log(
            f"✅ FuturesSafetyService backtest completed (symbols={completed}, eligible={eligible_count})"
        )

    def _get_interval_seconds(self) -> float:
        cfg = self._effective_config()
        return max(300.0, float(cfg.backtest_refresh_minutes) * 60.0)

    # ------------------------- config/env/logging -------------------------

    def _effective_config(self) -> FuturesSafetyConfig:
        tc = self.trading_config
        return FuturesSafetyConfig(
            enabled=bool(tc.get("futures_safety_enabled", True)),
            vps_only=bool(tc.get("futures_safety_vps_only", True)),
            backtest_interval=str(tc.get("futures_safety_backtest_interval", "5m")),
            backtest_window_days=_safe_float(tc.get("futures_safety_backtest_window_days", 1.0), 1.0),
            backtest_refresh_minutes=_coerce_int(tc.get("futures_safety_backtest_refresh_minutes", 45), 45),
            min_backtest_trades=_coerce_int(tc.get("futures_safety_min_backtest_trades", 5), 5),
            min_win_rate_pct=_safe_float(tc.get("futures_safety_min_win_rate_pct", 52.0), 52.0),
            min_profit_factor=_safe_float(tc.get("futures_safety_min_profit_factor", 1.05), 1.05),
            indicator_interval=str(tc.get("futures_safety_indicator_interval", "5m")),
            indicator_lookback_days=_safe_float(tc.get("futures_safety_indicator_lookback_days", 2.0), 2.0),
            atr_period=_coerce_int(tc.get("futures_safety_atr_period", 14), 14),
            adx_period=_coerce_int(tc.get("futures_safety_adx_period", 14), 14),
            min_atr_pct=_safe_float(tc.get("futures_safety_min_atr_pct", 0.35), 0.35),
            min_adx=_safe_float(tc.get("futures_safety_min_adx", 18.0), 18.0),
            indicator_cache_seconds=_coerce_int(tc.get("futures_safety_indicator_cache_seconds", 300), 300),
            max_trades_per_day=_coerce_int(tc.get("futures_safety_max_trades_per_day", 6), 6),
            max_daily_loss_usdt=_safe_float(tc.get("futures_safety_max_daily_loss_usdt", 25.0), 25.0),
            max_consecutive_losses=_coerce_int(tc.get("futures_safety_max_consecutive_losses", 3), 3),
        )

    def _is_enabled_environment(self) -> bool:
        cfg = self._effective_config()
        if not cfg.vps_only:
            return True

        # Conservative production-only rule (typical for VPS docker deploy).
        if os.getenv("AI_BOT_TEST_MODE") in ("1", "true", "TRUE", "yes", "YES"):
            return False
        flask_env = (os.getenv("FLASK_ENV") or os.getenv("ENV") or "").lower()
        if flask_env not in ("production", "prod"):
            return False
        return True

    def _log(self, message: str) -> None:
        if self.logger:
            try:
                self.logger.info(message)
                return
            except Exception:
                pass
        print(message)


__all__ = ["FuturesSafetyService", "FuturesSafetyConfig"]
