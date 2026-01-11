"""Persistence services for saving and scheduling bot state."""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict

from utils.compression import get_compressor

LoggerLike = logging.Logger

logger = logging.getLogger(__name__)


@contextmanager
def _bot_state_file_lock(state_file: os.PathLike[str] | str):
    """Best-effort cross-process lock for bot_state.json writers.

    Uses a sidecar lock file + fcntl.flock on POSIX; falls back to a process-local
    threading lock if flock is unavailable.
    """

    lock_path = f"{str(state_file)}.lock"
    os.makedirs(os.path.dirname(str(lock_path)), exist_ok=True)

    # Process-local fallback lock (still helpful when flock isn't available).
    _local_lock = getattr(_bot_state_file_lock, "_local_lock", None)
    if _local_lock is None:
        _local_lock = threading.RLock()
        setattr(_bot_state_file_lock, "_local_lock", _local_lock)

    try:
        import fcntl  # type: ignore

        with open(lock_path, "a+") as lock_handle:
            with _local_lock:
                try:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
                except Exception:
                    # If flock fails, still proceed under local lock.
                    pass
                try:
                    yield
                finally:
                    try:
                        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
                    except Exception:
                        pass
        return
    except Exception:
        # No fcntl (or other failure): local-only.
        with _local_lock:
            yield


def _atomic_write_json(path: os.PathLike[str] | str, payload: Any) -> None:
    target = str(path)
    tmp = f"{target}.tmp.{os.getpid()}.{int(time.time()*1000)}"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except Exception:
            pass
    os.replace(tmp, target)


def _default_noop(*_: Any, **__: Any) -> None:
    """Fallback noop for optional callbacks."""


def ensure_persistence_dirs(profile_override: str | None = None) -> Path:
    """Return the profile-specific persistence directory, creating it if needed.

    When profile_override is None, uses the workspace/profile-aware pathing rules.
    When profile_override is provided (e.g. multi-user runtime profiles like
    "user_123"), the directory is resolved without mutating process-wide
    BOT_PROFILE.
    """

    # Invariant: resolving a profile override must not mutate global BOT_PROFILE.
    before_env_profile = os.environ.get("BOT_PROFILE")
    before_pathing_profile = None
    if profile_override is not None:
        try:
            from app.services import pathing as _pathing

            before_pathing_profile = getattr(_pathing, "BOT_PROFILE", None)
        except Exception:
            before_pathing_profile = None

    env_path = os.getenv("BOT_PERSISTENCE_DIR")
    if env_path:
        base_path = Path(env_path)
        base_path.mkdir(parents=True, exist_ok=True)

        if profile_override:
            profile = str(profile_override).strip() or "default"
            target = base_path / profile
        else:
            profile = str(os.getenv("BOT_PROFILE", "default")).strip() or "default"
            target = base_path / profile
    else:
        from app.services import pathing

        if profile_override:
            profile = pathing._sanitize_profile(profile_override)
            target = pathing.PROJECT_ROOT_PATH / "bot_persistence" / profile
        else:
            # Preserve legacy-single-tenant behavior for BOT_PROFILE=default.
            target = Path(
                pathing.resolve_profile_path(
                    "bot_persistence", allow_legacy=True, migrate_legacy=True
                )
            )

    dirs_to_create = [
        target,
        target / "backups",
        target / "logs",
        target / "models",
    ]

    for directory in dirs_to_create:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            directory.chmod(0o755)
        except PermissionError as exc:
            logging.warning("Permission error creating %s: %s", directory, exc)
            try:
                directory.chmod(0o777)
            except Exception:
                pass
        except Exception as exc:
            logging.error("Error creating %s: %s", directory, exc)

    if profile_override is not None:
        assert os.environ.get("BOT_PROFILE") == before_env_profile
        try:
            from app.services import pathing as _pathing

            assert getattr(_pathing, "BOT_PROFILE", None) == before_pathing_profile
        except Exception:
            pass
    return target


class ProfessionalPersistence:
    """File-backed persistence for the AI bot state."""

    def __init__(
        self,
        persistence_dir: str = "bot_persistence",
        *,
        market_cap_weights_provider: Callable[[], Dict[str, Any]] | None = None,
        futures_settings_getter: Callable[[], Dict[str, Any]] | None = None,
        futures_settings_setter: Callable[[Dict[str, Any]], None] | None = None,
        compression_level: int = 3,
    ) -> None:
        self.persistence_dir = persistence_dir
        persist_dir = ensure_persistence_dirs()
        self.state_file = str(persist_dir / "bot_state.json")
        self.backup_dir = str(persist_dir / "backups")
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)

        self.current_version = "2.0"
        self._market_cap_weights_provider = market_cap_weights_provider or (lambda: {})
        self._futures_settings_getter = futures_settings_getter or (lambda: {})
        self._futures_settings_setter = futures_settings_setter or (lambda data: None)

        # Initialize Zstandard compressor
        self.compressor = get_compressor(level=compression_level)

    def save_complete_state(
        self,
        trader,
        ml_system,
        config,
        symbols,
        historical_data,
        *,
        profile: str | None = None,
    ) -> bool:
        """Persist the full bot state to disk."""
        # Ensure directories exist first
        persist_dir = ensure_persistence_dirs(profile)

        # Update file paths to use the ensured directory
        state_file = persist_dir / "bot_state.json"
        backup_dir = persist_dir / "backups"

        # Lightweight debug logging to help diagnose state mismatches
        try:
            # Print to stdout so container logs always show this regardless
            # of logging configuration. This is intentionally concise.
            print(
                f"[PERSIST DEBUG] saving trader flags: id(trader)={id(trader)}, trading_enabled={getattr(trader, 'trading_enabled', None)}, paper_trading={getattr(trader, 'paper_trading', None)}, futures_trading_enabled={getattr(trader, 'futures_trading_enabled', None)}"
            )
        except Exception:
            pass
        try:
            # Debug: log key trader flags at save time to diagnose mismatch
            try:
                t_enabled = getattr(trader, "trading_enabled", None)
                t_paper = getattr(trader, "paper_trading", None)
            except Exception:
                t_enabled = None
                t_paper = None
            logger.info(
                "Persistence.save_complete_state called - id(trader)=%s, trading_enabled=%s, paper_trading=%s",
                id(trader),
                t_enabled,
                t_paper,
            )
            state = {
                "version": self.current_version,
                "timestamp": datetime.now().isoformat(),
                "trader_state": self._get_trader_state(trader),
                "ml_system_state": self._get_ml_system_state(ml_system),
                "configuration": {
                    "TRADING_CONFIG": config,
                    "TOP_SYMBOLS": symbols,
                    "MARKET_CAP_WEIGHTS": self._market_cap_weights_provider(),
                },
                "historical_data_summary": self._summarize_historical_data(
                    historical_data
                ),
                "futures_manual_settings": self._futures_settings_getter() or {},
                "system_metrics": {
                    "total_uptime": self._calculate_uptime(),
                    "save_count": self._get_save_count(profile),
                    "last_trade_time": trader.trade_history.get_trade_history()[-1][
                        "timestamp"
                    ]
                    if trader.trade_history.get_trade_history()
                    else None,
                },
            }

            # Validate pnl before persisting state
            def validate_pnl(trade):
                if trade.get("status") == "CLOSED" and _to_float(trade.get("pnl", 0)) == 0:
                    raise ValueError("Invalid pnl for CLOSED trade")

            # Create backup directory if it doesn't exist
            backup_dir.mkdir(exist_ok=True)

            # Compress and save the state
            backup_file = backup_dir / f"state_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json.zst"
            self.compressor.compress_json(state, backup_file)

            with _bot_state_file_lock(state_file):
                _atomic_write_json(state_file, {
                    **state,
                    "trades": [
                        validate_pnl(trade) or trade for trade in state.get("trades", [])
                    ],
                })

            self._save_critical_components(trader, ml_system)
            self._update_save_count(profile)
            return True
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"❌ Error saving bot state: {exc}")
            return False

    def load_complete_state(
        self,
        trader,
        ml_system,
        *,
        profile: str | None = None,
        restore_ml_state: bool = True,
        restore_futures_settings: bool = True,
    ) -> bool:
        """Load bot state from disk.

        The persisted JSON schema remains unchanged. Optional flags allow
        restoring only trader state (useful for multi-user isolation where the
        ML engine is shared/read-only).
        """
        persist_dir = ensure_persistence_dirs(profile)
        state_file = persist_dir / "bot_state.json"

        if not state_file.exists():
            print("💾 No previous state found - starting fresh")
            return False
        try:
            with open(state_file, "r") as handle:
                state = json.load(handle)

            if not self._check_version_compatibility(state.get("version", "1.0")):
                print("⚠️ State version mismatch - some data may not load correctly")

            self._restore_trader_state(trader, state.get("trader_state", {}))
            if restore_ml_state:
                self._restore_ml_system_state(ml_system, state.get("ml_system_state", {}))
                self._restore_configuration(state.get("configuration", {}))
            if restore_futures_settings and "futures_manual_settings" in state:
                self._futures_settings_setter(state["futures_manual_settings"])
                print("💾 Futures manual settings restored")
            print("💾 Bot state restored successfully from persistence")
            return True
        except Exception as exc:  # pragma: no cover
            print(f"❌ Error loading bot state: {exc}")
            return self._emergency_recovery(trader, ml_system, profile=profile)

    def _get_trader_state(self, trader) -> Dict[str, Any]:
        return {
            "balance": trader.balance,
            "positions": trader.positions,
            "trading_enabled": trader.trading_enabled,
            "paper_trading": trader.paper_trading,
            "futures_trading_enabled": getattr(trader, "futures_trading_enabled", False),
            "daily_pnl": trader.daily_pnl,
            "max_drawdown": trader.max_drawdown,
            "peak_balance": trader.peak_balance,
            "bot_efficiency": trader.bot_efficiency,
            "risk_manager_state": {
                "current_risk_profile": trader.risk_manager.current_risk_profile,
                "risk_adjustment_history": trader.risk_manager.risk_adjustment_history[
                    -10:
                ],
                "volatility_regime": trader.risk_manager.volatility_regime,
                "market_stress_indicator": trader.risk_manager.market_stress_indicator,
            },
            "ensemble_system_state": {
                "market_regime": trader.ensemble_system.market_regime,
                "correlation_matrix": trader.ensemble_system.correlation_matrix,
                "last_rebuild_time": trader.ensemble_system.last_rebuild_time,
            },
        }

    def _get_ml_system_state(self, ml_system) -> Dict[str, Any]:
        return {
            "models_loaded": list(ml_system.models.keys()),
            "training_progress": ml_system.training_progress,
            "last_training_cycle": ml_system.training_logs[-5:]
            if ml_system.training_logs
            else [],
            "crt_signals_count": len(ml_system.crt_generator.signals_history),
        }

    def _summarize_historical_data(self, historical_data) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        for symbol, prices in historical_data.items():
            if prices:
                summary[symbol] = {
                    "data_points": len(prices),
                    "latest_price": prices[-1],
                    "price_range": (
                        (min(prices), max(prices))
                        if len(prices) > 1
                        else (prices[0], prices[0])
                    ),
                    "last_updated": datetime.now().isoformat(),
                }
        return summary

    def _save_critical_components(self, trader, ml_system) -> None:
        try:
            critical_state = {
                "positions": trader.positions,
                "balance": trader.balance,
                "trading_enabled": trader.trading_enabled,
                "models_loaded": list(ml_system.models.keys()),
                "futures_manual_settings": self._futures_settings_getter() or {},
            }
            persist_dir = ensure_persistence_dirs()
            critical_file = persist_dir / "critical_state.json"
            with open(critical_file, "w") as handle:
                json.dump(critical_state, handle, indent=2, default=str)
        except Exception as exc:  # pragma: no cover
            print(f"⚠️ Warning: Could not save critical components: {exc}")

    def _restore_trader_state(self, trader, state: Dict[str, Any]) -> None:
        trader.balance = state.get("balance", trader.initial_balance)
        trader.positions = state.get("positions", {})
        trader.trading_enabled = state.get("trading_enabled", False)
        trader.paper_trading = state.get("paper_trading", True)
        # Don't override futures_trading_enabled if it was already enabled (e.g., by auto-enabling logic)
        if not getattr(trader, "futures_trading_enabled", False):
            trader.futures_trading_enabled = state.get("futures_trading_enabled", False)
        trader.daily_pnl = state.get("daily_pnl", 0)
        trader.max_drawdown = state.get("max_drawdown", 0)
        trader.peak_balance = state.get("peak_balance", trader.initial_balance)
        trader.bot_efficiency = state.get("bot_efficiency", trader.bot_efficiency)

        risk_state = state.get("risk_manager_state", {})
        trader.risk_manager.current_risk_profile = risk_state.get(
            "current_risk_profile", "moderate"
        )
        trader.risk_manager.volatility_regime = risk_state.get(
            "volatility_regime", "NORMAL"
        )
        trader.risk_manager.market_stress_indicator = risk_state.get(
            "market_stress_indicator", 0.0
        )

        ensemble_state = state.get("ensemble_system_state", {})
        trader.ensemble_system.market_regime = ensemble_state.get(
            "market_regime", "NEUTRAL"
        )
        print(
            f"💾 Trader state restored: Balance ${trader.balance:.2f}, Positions: {len(trader.positions)}, Trading: {trader.trading_enabled}, Futures: {trader.futures_trading_enabled}"
        )

    def _restore_ml_system_state(self, ml_system, state: Dict[str, Any]) -> None:
        models_to_load = state.get("models_loaded", [])
        for symbol in models_to_load:
            if symbol not in ml_system.models:
                ml_system.load_models(symbol)
        ml_system.training_progress = state.get("training_progress", {})
        print(f"💾 ML system state restored: {len(models_to_load)} models")

    def _restore_configuration(self, config: Dict[str, Any]) -> None:
        if config:
            print(
                f"💾 Configuration backup available: {len(config.get('TOP_SYMBOLS', []))} symbols"
            )

    def _emergency_recovery(self, trader, ml_system, *, profile: str | None = None) -> bool:
        try:
            persist_dir = ensure_persistence_dirs(profile)
            critical_file = persist_dir / "critical_state.json"
            if critical_file.exists():
                with open(critical_file, "r") as handle:
                    critical_state = json.load(handle)

                trader.positions = critical_state.get("positions", {})
                trader.balance = critical_state.get("balance", trader.initial_balance)
                trader.trading_enabled = critical_state.get("trading_enabled", False)

                if "futures_manual_settings" in critical_state:
                    self._futures_settings_setter(
                        critical_state["futures_manual_settings"]
                    )
                    print("💾 Futures manual settings restored from emergency backup")

                for symbol in critical_state.get("models_loaded", []):
                    ml_system.load_models(symbol)

                print(
                    f"🚨 Emergency recovery completed: ${trader.balance:.2f}, {len(trader.positions)} positions"
                )
                return True
        except Exception as exc:  # pragma: no cover
            print(f"❌ Emergency recovery failed: {exc}")
        return False

    def _create_backup(self, *, profile: str | None = None) -> None:
        persist_dir = ensure_persistence_dirs(profile)
        state_file = str(persist_dir / "bot_state.json")
        backup_dir = str(persist_dir / "backups")
        if not os.path.exists(state_file):
            return
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs(backup_dir, exist_ok=True)
            backup_file = os.path.join(backup_dir, f"state_backup_{timestamp}.json")
            shutil.copy2(state_file, backup_file)
            self._cleanup_old_backups(profile=profile)
        except Exception as exc:  # pragma: no cover
            print(f"⚠️ Backup creation failed: {exc}")

    def _cleanup_old_backups(self, *, profile: str | None = None) -> None:
        try:
            persist_dir = ensure_persistence_dirs(profile)
            backup_dir = str(persist_dir / "backups")
            backup_files = [
                (
                    os.path.join(backup_dir, file),
                    os.path.getctime(os.path.join(backup_dir, file)),
                )
                for file in os.listdir(backup_dir)
                if file.startswith("state_backup_") and file.endswith(".json")
            ]
            backup_files.sort(key=lambda entry: entry[1])
            while len(backup_files) > 10:
                oldest_file, _ = backup_files.pop(0)
                os.remove(oldest_file)
        except Exception as exc:  # pragma: no cover
            print(f"⚠️ Backup cleanup failed: {exc}")

    def _check_version_compatibility(self, saved_version: str) -> bool:
        return saved_version == self.current_version

    def _calculate_uptime(self) -> str:
        return "unknown"

    def _get_save_count(self, profile: str | None = None) -> int:
        try:
            persist_dir = ensure_persistence_dirs(profile)
            count_file = str(persist_dir / "save_count.txt")
            if os.path.exists(count_file):
                with open(count_file, "r") as handle:
                    return int(handle.read().strip())
            return 0
        except Exception:  # pragma: no cover
            return 0

    def _update_save_count(self, profile: str | None = None) -> None:
        try:
            persist_dir = ensure_persistence_dirs(profile)
            count_file = str(persist_dir / "save_count.txt")
            current_count = self._get_save_count(profile)
            with open(count_file, "w") as handle:
                handle.write(str(current_count + 1))
        except Exception:  # pragma: no cover
            pass

    def get_persistence_status(self, *, profile: str | None = None) -> Dict[str, Any]:
        persist_dir = ensure_persistence_dirs(profile)
        state_file = str(persist_dir / "bot_state.json")
        backup_dir = str(persist_dir / "backups")
        status = {
            "persistence_enabled": True,
            "state_file_exists": os.path.exists(state_file),
            "backup_count": len([f for f in os.listdir(backup_dir) if f.endswith(".json")])
            if os.path.exists(backup_dir)
            else 0,
            "last_save_time": None,
            "total_saves": self._get_save_count(profile),
        }
        if status["state_file_exists"]:
            try:
                with open(state_file, "r") as handle:
                    state = json.load(handle)
                status["last_save_time"] = state.get("timestamp")
            except Exception:
                pass
        return status


class PersistenceScheduler:
    """Background loop for automatic persistence."""

    def __init__(
        self,
        persistence_manager: ProfessionalPersistence,
        save_interval_minutes: int = 5,
        *,
        log_event: Callable[..., None] | None = None,
        log_debug: Callable[..., None] | None = None,
        bot_logger: LoggerLike | None = None,
    ) -> None:
        self.persistence_manager = persistence_manager
        self.save_interval = save_interval_minutes * 60
        self.is_running = False
        self.last_save_time = 0.0
        self._log_event = log_event or _default_noop
        self._log_debug = log_debug or _default_noop
        self._bot_logger = bot_logger

    def start_automatic_saving(
        self, trader, ml_system, config, symbols, historical_data
    ) -> None:
        self._log_event(
            "PERSISTENCE",
            "Automatic saving loop requested",
            level=logging.INFO,
            details={"interval_minutes": round(self.save_interval / 60, 2)},
        )
        self.is_running = True

        def save_loop() -> None:
            while self.is_running:
                try:
                    current_time = time.time()
                    if current_time - self.last_save_time >= self.save_interval:
                        self._log_debug(
                            "PERSISTENCE",
                            "Attempting automatic state save",
                            {
                                "since_last_save_sec": round(
                                    current_time - self.last_save_time, 2
                                ),
                            },
                        )
                        started_at = time.time()
                        success = self.persistence_manager.save_complete_state(
                            trader, ml_system, config, symbols, historical_data
                        )
                        duration = time.time() - started_at
                        if success:
                            self._log_event(
                                "PERSISTENCE",
                                "Automatic state save completed",
                                level=logging.INFO,
                                details={"duration_sec": round(duration, 3)},
                            )
                        else:
                            self._log_event(
                                "PERSISTENCE",
                                "Automatic state save failed",
                                level=logging.WARNING,
                                details={"duration_sec": round(duration, 3)},
                            )
                        self.last_save_time = current_time
                except Exception as exc:  # pragma: no cover
                    print(f"❌ Automatic save error: {exc}")
                    self._log_event(
                        "PERSISTENCE",
                        f"Automatic state save error: {exc}",
                        level=logging.ERROR,
                    )
                    if self._bot_logger:
                        self._bot_logger.exception("Automatic state save error")
                time.sleep(60)

        threading.Thread(target=save_loop, daemon=True).start()
        print(
            f"💾 Automatic state saving started (every {self.save_interval//60} minutes)"
        )
        self._log_event(
            "PERSISTENCE",
            "Automatic state saving thread started",
            level=logging.INFO,
            details={"interval_minutes": round(self.save_interval / 60, 2)},
        )

    def stop_automatic_saving(self) -> None:
        self.is_running = False
        print("💾 Automatic state saving stopped")
        self._log_event(
            "PERSISTENCE", "Automatic state saving stopped", level=logging.INFO
        )

    def manual_save(
        self,
        trader,
        ml_system,
        config,
        symbols,
        historical_data,
        *,
        profile: str | None = None,
    ) -> bool:
        self._log_event("PERSISTENCE", "Manual save requested", level=logging.INFO)
        success = self.persistence_manager.save_complete_state(
            trader, ml_system, config, symbols, historical_data, profile=profile
        )
        if success:
            self.last_save_time = time.time()
            self._log_event(
                "PERSISTENCE",
                "Manual save completed successfully",
                level=logging.INFO,
                details={"timestamp": datetime.utcnow().isoformat()},
            )
        else:
            self._log_event("PERSISTENCE", "Manual save failed", level=logging.WARNING)
        return success
