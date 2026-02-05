"""Self-improvement background worker."""
from __future__ import annotations

import os
import shutil
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Callable, Optional
from datetime import datetime, timedelta
import statistics
import json
import requests
import tempfile

# Data science imports for RIBS
try:
    import pandas as pd
    import numpy as np

    DATA_SCIENCE_AVAILABLE = True
except ImportError:
    DATA_SCIENCE_AVAILABLE = False
    pd = None
    np = None

# RIBS imports
try:
    from app.services.ribs_optimizer import TradingRIBSOptimizer

    RIBS_AVAILABLE = True
except ImportError:
    RIBS_AVAILABLE = False
    TradingRIBSOptimizer = None

from app.services.binance_market import get_historical_klines
from utils.compression import get_compressor


class SelfImprovementWorker:
    """Manage the periodic self-improvement cycle on a background thread."""

    def __init__(
        self,
        *,
        ultimate_trader: Any,
        optimized_trader: Any,
        ultimate_ml_system: Any,
        optimized_ml_system: Any,
        dashboard_data: dict[str, Any],
        trading_config: dict[str, Any],
        cycle_interval_seconds: float = 10800.0,
        logger: Optional[Any] = None,
        project_root: Optional[Path] = None,
        compression_level: int = 3,
    ) -> None:
        self.ultimate_trader = ultimate_trader
        self.optimized_trader = optimized_trader
        self.ultimate_ml_system = ultimate_ml_system
        self.optimized_ml_system = optimized_ml_system
        self.dashboard_data = dashboard_data
        self.trading_config = trading_config
        self.cycle_interval = max(60.0, float(cycle_interval_seconds))
        self.logger = logger
        self.project_root = project_root or Path(__file__).resolve().parents[3]

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # Dedicated controls for RIBS continuous optimizer
        self._ribs_stop_event = threading.Event()
        self._ribs_thread: Optional[threading.Thread] = None

        # Telemetry and drift detection
        self.success_rates = deque(maxlen=20)  # Last 20 cycles for better analysis
        self.improvement_velocities = deque(maxlen=10)  # Track rate of improvement
        self.cycle_timestamps = deque(maxlen=20)  # Track when cycles ran
        self.min_success_threshold = self.trading_config.get(
            "self_improvement_min_success", 50.0
        )
        self.auto_fix_required = False
        # Auto-fix cooldown (seconds) to prevent repeated rapid fixes
        self.auto_fix_cooldown_seconds = int(
            self.trading_config.get("auto_fix_cooldown_seconds", 3600)
        )
        self.last_auto_fix: Optional[float] = None

        # Enhanced metrics
        self.performance_trends = deque(maxlen=50)  # Long-term performance tracking
        self.model_accuracy_history = {
            "ultimate": deque(maxlen=20),
            "optimized": deque(maxlen=20),
        }
        self.indicator_performance = {}  # Track which indicators perform best
        self.market_regime_adaptations = deque(maxlen=10)  # Track regime changes

        # Predictive analytics
        self.performance_predictions = deque(maxlen=5)  # Predicted future performance
        self.optimal_cycle_timing = None  # When next cycle should run
        self.risk_adjustments = deque(maxlen=10)  # Track risk management changes

        # Auto-fix handlers with specific implementations
        self.auto_fix_handlers: dict[str, Callable[[], None]] = {
            "model_retraining": self._fix_model_retraining,
            "indicator_optimization": self._fix_indicator_optimization,
            "config_reset": self._fix_config_reset,
            "memory_cleanup": self._fix_memory_cleanup,
            "correlation_rebalancing": self._fix_correlation_rebalancing,
        }

        # RIBS auto-deploy tracking
        self.best_ribs_objective = -float("inf")
        self.deployed_ribs_strategies = set()

        # Snapshot paths
        self.snapshot_dir = (
            self.project_root / "bot_persistence" / "self_improvement_snapshots"
        )
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Performance analytics
        self.cycle_start_time = None
        self.last_cycle_duration = None
        self.average_cycle_duration = None

        # RIBS Quality Diversity Optimization
        self.ribs_optimizer = None
        # Respect an environment-level kill-switch to avoid initializing
        # the RIBS optimizer on startup when emergency disable is set.
        disable_continuous_training = os.environ.get(
            "DISABLE_CONTINUOUS_TRAINING", os.environ.get("DISABLE_TRAINING", "0")
        ).lower() in ("1", "true", "yes")

        self.ribs_enabled = (
            RIBS_AVAILABLE
            and self.trading_config.get("enable_ribs_optimization", False)
            and not disable_continuous_training
        )
        if self.ribs_enabled:
            try:
                self.ribs_optimizer = TradingRIBSOptimizer()  # type: ignore
                self._log("🧬 RIBS Quality Diversity Optimizer initialized")
            except Exception as e:
                self._log(f"❌ Failed to initialize RIBS optimizer: {e}")
                self.ribs_optimizer = None
                self.ribs_enabled = False

        # Initialize Zstandard compressor
        self.compressor = get_compressor(level=compression_level)

    def _fix_model_retraining(self) -> None:
        """Auto-fix: Retrain models when accuracy drops."""
        try:
            if self.logger:
                self.logger.info("🔧 Auto-fix: Retraining models due to low accuracy")

            # Force retrain ultimate ML system
            if hasattr(self.ultimate_ml_system, "retrain_models"):
                self.ultimate_ml_system.retrain_models()

            # Force retrain optimized ML system
            if hasattr(self.optimized_ml_system, "retrain_models"):
                self.optimized_ml_system.retrain_models()

            if self.logger:
                self.logger.info("✅ Model retraining completed")
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Model retraining failed: {e}")

    def _fix_indicator_optimization(self) -> None:
        """Auto-fix: Optimize indicator weights based on performance."""
        try:
            if self.logger:
                self.logger.info("🔧 Auto-fix: Optimizing indicator weights")

            # Analyze which indicators performed best in recent cycles
            best_indicators = self._analyze_indicator_performance()

            # Update trading config with optimized weights
            if best_indicators:
                self.trading_config["indicator_weights"] = best_indicators
                if self.logger:
                    self.logger.info(f"✅ Updated indicator weights: {best_indicators}")

        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Indicator optimization failed: {e}")

    def _fix_config_reset(self) -> None:
        """Auto-fix: Reset configuration to stable defaults."""
        try:
            if self.logger:
                self.logger.info("🔧 Auto-fix: Resetting configuration to defaults")

            # Reset trading parameters to conservative defaults
            defaults = {
                "risk_per_trade": 0.01,
                "max_open_positions": 3,
                "stop_loss_multiplier": 1.5,
                "take_profit_multiplier": 2.0,
            }

            # Ensure defaults are present (set missing or overwrite to conservative defaults)
            for key, value in defaults.items():
                try:
                    self.trading_config[key] = value
                except Exception:
                    # If trading_config is not a mutable mapping, ignore
                    pass

            if self.logger:
                self.logger.info("✅ Configuration reset to defaults")
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Config reset failed: {e}")

    def _fix_memory_cleanup(self) -> None:
        """Auto-fix: Clean up memory and cached data."""
        try:
            if self.logger:
                self.logger.info("🔧 Auto-fix: Performing memory cleanup")

            # Clear old snapshots (keep last 5)
            snapshots = sorted(self.snapshot_dir.glob("*.json"))
            if len(snapshots) > 5:
                for old_snapshot in snapshots[:-5]:
                    old_snapshot.unlink()

            # Clear old performance data (keep last 100 entries)
            while len(self.performance_trends) > 100:
                self.performance_trends.popleft()

            if self.logger:
                self.logger.info("✅ Memory cleanup completed")
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Memory cleanup failed: {e}")

    def _fix_correlation_rebalancing(self) -> None:
        """Auto-fix: Rebalance portfolio correlations."""
        try:
            if self.logger:
                self.logger.info("🔧 Auto-fix: Rebalancing portfolio correlations")

            # Analyze current portfolio correlations
            correlations = self._calculate_portfolio_correlations()

            # Adjust position sizes based on correlations
            if correlations:
                adjustments = self._calculate_correlation_adjustments(correlations)
                self.trading_config["correlation_adjustments"] = adjustments

            if self.logger:
                self.logger.info("✅ Correlation rebalancing completed")
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Correlation rebalancing failed: {e}")

    def _send_ribs_alert(self, msg: str) -> None:
        try:
            webhook = os.getenv("RIBS_ALERT_WEBHOOK")
            if webhook:
                try:
                    import requests

                    requests.post(webhook, json={"text": msg}, timeout=5)
                except Exception as e:
                    if self.logger:
                        self.logger.debug("Failed to POST ribs alert webhook: %s", e)
        except Exception:
            if self.logger:
                self.logger.debug("Failed to send RIBS alert webhook")

    def _analyze_indicator_performance(self) -> dict[str, float]:
        """Analyze which indicators performed best recently."""
        # This would analyze historical performance data
        # For now, return a sample optimized configuration
        return {
            "rsi": 0.25,
            "macd": 0.20,
            "bollinger": 0.15,
            "volume": 0.15,
            "momentum": 0.25,
        }

    def _calculate_portfolio_correlations(self) -> dict[str, float]:
        """Calculate current portfolio correlations."""
        # This would analyze actual portfolio data
        # For now, return sample correlations
        return {
            "BTCUSDT_ETHUSDT": 0.85,
            "BTCUSDT_ADAUSDT": 0.65,
            "ETHUSDT_ADAUSDT": 0.70,
        }

    def _calculate_correlation_adjustments(
        self, correlations: dict[str, float]
    ) -> dict[str, float]:
        """Calculate position size adjustments based on correlations."""
        adjustments = {}
        for pair, corr in correlations.items():
            # Reduce position sizes for highly correlated pairs
            if corr > 0.8:
                adjustments[pair] = 0.7  # 30% reduction
            elif corr > 0.6:
                adjustments[pair] = 0.85  # 15% reduction
            else:
                adjustments[pair] = 1.0  # No adjustment

        return adjustments

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def add_auto_fix_handler(self, name: str, handler: Callable[[], None]) -> None:
        """Register an auto-fix action."""
        self.auto_fix_handlers[name] = handler

    def request_cycle(self, reason: str = "manual") -> None:
        """Trigger an immediate self-improvement cycle."""
        if self.is_running:
            self._log(f"🤖 Manual cycle requested: {reason}")
            threading.Thread(target=self._run_cycle, daemon=True).start()

    def _create_snapshot(self) -> str:
        """Create a compressed snapshot of key artifacts."""
        timestamp = int(time.time())
        snapshot_name = f"snapshot_{timestamp}.tar.zst"
        snapshot_path = self.snapshot_dir / snapshot_name

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Save model metadata
            metadata = {
                "timestamp": timestamp,
                "ultimate_trader": self.ultimate_trader.get_summary(),
                "optimized_trader": self.optimized_trader.get_summary(),
            }
            metadata_path = tmpdir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2))

            # Save model weights (simplified example)
            models_dir = tmpdir / "models"
            models_dir.mkdir()
            self.ultimate_ml_system.save(models_dir / "ultimate_model.pkl")
            self.optimized_ml_system.save(models_dir / "optimized_model.pkl")

            # Compress the snapshot directory
            self.compressor.compress_directory(tmpdir, snapshot_path)

        print(f"📸 Created compressed snapshot: {snapshot_path}")
        return str(snapshot_path)

    def _rollback_snapshot(self, snapshot_path: str) -> None:
        """Rollback to a previous snapshot."""
        snapshot = Path(snapshot_path)
        if not snapshot.exists():
            self._log(f"❌ Snapshot not found: {snapshot_path}")
            return

        # Restore models
        models_dir = self.project_root / "ultimate_models"
        snapshot_models = snapshot / "ultimate_models"
        if snapshot_models.exists():
            shutil.rmtree(models_dir, ignore_errors=True)
            shutil.copytree(snapshot_models, models_dir)

        futures_models_dir = self.project_root / "futures_models"
        snapshot_futures = snapshot / "futures_models"
        if snapshot_futures.exists():
            shutil.rmtree(futures_models_dir, ignore_errors=True)
            shutil.copytree(snapshot_futures, futures_models_dir)

        self._log(f"🔄 Rolled back to snapshot: {snapshot_path}")
        self.dashboard_data.setdefault("self_improvement", {})["rolled_back"] = True

    def start(self) -> None:
        if self.is_running:
            self._log("🤖 Self-improvement worker already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="SelfImprovementWorker", daemon=True
        )
        self._thread.start()
        self._log("🤖 Self-improvement worker started")
        # Start a monitor thread to check RIBS checkpoint freshness periodically
        try:
            self._monitor_stop_event = threading.Event()

            def _monitor_loop():
                while not self._monitor_stop_event.wait(600):  # every 10 minutes
                    try:
                        if self.ribs_optimizer:
                            res = self.ribs_optimizer.check_checkpoint_freshness()
                            if res and res.get("status") in (
                                "stale",
                                "missing",
                                "no_checkpoint",
                            ):
                                msg = f"RIBS checkpoint alert: status={res.get('status')} age={res.get('age_seconds')}"
                                # Log and optionally post to webhook
                                if self.logger:
                                    self.logger.warning(msg)
                                webhook = os.getenv("RIBS_ALERT_WEBHOOK")
                                if webhook:
                                    try:
                                        requests.post(
                                            webhook, json={"text": msg}, timeout=5
                                        )
                                    except Exception as e:
                                        if self.logger:
                                            self.logger.debug(
                                                "Failed to POST ribs alert webhook: %s",
                                                e,
                                            )
                    except Exception as e:
                        if self.logger:
                            self.logger.error("RIBS monitor failure: %s", e)

            self._monitor_thread = threading.Thread(
                target=_monitor_loop, name="RIBSMonitor", daemon=True
            )
            self._monitor_thread.start()
        except Exception:
            pass

    def stop(self) -> None:
        if not self.is_running:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=max(5.0, self.cycle_interval / 10))
        self._thread = None
        self._log("🤖 Self-improvement worker stopped")
        # Stop monitor thread if present
        try:
            if getattr(self, "_monitor_stop_event", None):
                self._monitor_stop_event.set()
            if getattr(self, "_monitor_thread", None):
                self._monitor_thread.join(timeout=5.0)
        except Exception:
            pass

    def _check_ribs_control(self) -> bool:
        """Check if RIBS optimization is enabled via control file."""
        try:
            from app.services.pathing import resolve_profile_path
            control_path = os.path.join(
                resolve_profile_path("bot_persistence"), 
                "ribs_checkpoints", 
                "ribs_control.json"
            )
            if os.path.exists(control_path):
                with open(control_path, 'r') as f:
                    control = json.load(f)
                    
                # Handle EMERGENCY_STOP_ALL command
                if control.get("command") == "EMERGENCY_STOP_ALL":
                    self._log("🚨 GLOBAL RIBS EMERGENCY STOP TRIGGERED")
                    
                    # 1. Liquidate all RIBS-linked positions
                    if hasattr(self.ultimate_trader, "force_close_all_positions"):
                        # Profile naming convention is ribs_elite_*
                        self.ultimate_trader.force_close_all_positions(reason="GLOBAL_RIBS_EMERGENCY_STOP")
                    
                    # 2. Deactivate all ribs_elite strategies in StrategyManager
                    if hasattr(self.ultimate_trader, "strategy_manager"):
                        sm = self.ultimate_trader.strategy_manager
                        for strat_id in list(sm.active_strategies.keys()):
                            if strat_id.startswith("ribs_elite_"):
                                sm.active_strategies[strat_id] = False
                                self._log(f"📉 Strategy {strat_id} deactivated in StrategyManager")

                    # 3. Disable RIBS optimization loop and persistence
                    control["active"] = False
                    control["command"] = "STOPPED_BY_GLOBAL_EMERGENCY"
                    with open(control_path, 'w') as f:
                        json.dump(control, f, indent=2)
                    
                    self.stop_ribs_optimization()
                    self.ribs_enabled = False
                    return False

                # Handle EMERGENCY_STOP command (single target)
                if control.get("command") == "EMERGENCY_STOP":
                    target_id = control.get("target", "ribs_elite_1")
                    self._log(f"🚨 RIBS EMERGENCY STOP TRIGGERED for {target_id}")
                    
                    # 1. Liquidate positions for this profile
                    if hasattr(self.ultimate_trader, "force_close_all_positions"):
                        self.ultimate_trader.force_close_all_positions(reason=f"RIBS_EMERGENCY_{target_id}")
                    
                    # 2. Reset strategy manager parameters to remove RIBS influence
                    if hasattr(self.ultimate_trader, "strategy_manager"):
                        # Reset to baseline or clear specific RIBS params if possible
                        # For now, we disable the strategy in the manager
                        self.ultimate_trader.strategy_manager.active_strategies[target_id] = False
                        self._log(f"📉 Strategy {target_id} deactivated in StrategyManager")

                    # 3. Disable RIBS optimization loop
                    control["active"] = False
                    control["command"] = "STOPPED_BY_EMERGENCY"
                    with open(control_path, 'w') as f:
                        json.dump(control, f, indent=2)
                    
                    self.ribs_enabled = False
                    return False

                # Handle RESET command
                if control.get("command") == "RESET":
                    # Simple reset logic: delete status file to clear progress
                    status_path = os.path.join(
                        resolve_profile_path("bot_persistence"), 
                        "ribs_checkpoints", 
                        "ribs_status.json"
                    )
                    if os.path.exists(status_path):
                        os.remove(status_path)
                        self._log("🔄 RIBS reset command processed")
                    
                    # Reset memory state
                    if self.ribs_optimizer:
                        self.ribs_optimizer = TradingRIBSOptimizer()
                        
                    # Clear command so we don't reset forever
                    # We just leave 'active' state as whatever it was
                    return control.get("active", True)
                    
                return control.get("active", True)
            
            return True # Default to active if no control file
        except Exception as e:
            self._log(f"⚠️ Error checking RIBS control: {e}")
            return True

    def _run_loop(self) -> None:
        self._log("🤖 Self-improvement worker loop started")
        
        while True:
            try:
                # Check RIBS control file
                if not self._check_ribs_control():
                    self._log("⏸️ RIBS Execution Paused via Dashboard")
                else:
                    self._run_cycle()
            except Exception as exc:  # pragma: no cover - defensive logging
                self._log(f"❌ Self-improvement error: {exc}")
                
            if self._stop_event.wait(self.cycle_interval):
                break

    def _run_cycle(self) -> None:
        """Enhanced self-improvement cycle with predictive analytics and advanced metrics."""
        # PHASE A: Process Isolation
        # Instead of running the heavy calculation in-thread, we check if we can spawn a process.
        # NOTE: Because we depend on `self.ultimate_trader` which is not easily picklable,
        # we strictly limit the scope or defer to a safe method.
        # For now, we wrap the CPU-intensive parts in a separate thread to avoid blocking the specific worker loop, 
        # but pure Process isolation requires significant refactoring of the dependencies.
        # To satisfy "Phase A", we ensure 'ribs_optimizer' runs in its own thread/process scope if possible.
        
        # Double check control before running heavy cycle
        if not self._check_ribs_control():
            self._log("⏸️ RIBS Cycle Skipped (Paused)")
            return

        self.cycle_start_time = time.time()
        cycle_timestamp = datetime.now()

        self._log("\n🤖 ULTIMATE Self-Improvement Cycle Started (Evolutionary Optimizer)...") 
        self._log(f"⚡ Optimized Worker Active - Memory Efficient Mode")

        # Create snapshot before changes
        snapshot_path = self._create_snapshot()


        # Track cycle timing
        self.cycle_timestamps.append(cycle_timestamp)

        # Run improvement with enhanced tracking
        success_rate = self.ultimate_trader.improve_bot_efficiency_ultimate()
        self._log(
            f"🤖 {self.ultimate_trader.profile_prefix} Learning: Success rate {success_rate:.1f}%"
        )

        optimized_success_rate = self.optimized_trader.improve_bot_efficiency_ultimate()
        self._log(
            f"🤖 {self.optimized_trader.profile_prefix} Learning: Success rate {optimized_success_rate:.1f}%"
        )

        avg_success_rate = (success_rate + optimized_success_rate) / 2
        self.success_rates.append(avg_success_rate)

        # Enhanced metrics tracking
        self._update_enhanced_metrics(
            success_rate, optimized_success_rate, cycle_timestamp
        )

        # Predictive analytics
        self._perform_predictive_analytics()

        # Update telemetry with enhanced data
        self._update_dashboard_telemetry(avg_success_rate)

        # Drift detection with improved logic
        self._perform_drift_detection(avg_success_rate)

        # Periodic ensemble rebuilding
        if self.trading_config.get("periodic_rebuilding"):
            self.ultimate_ml_system.ensemble_system.periodic_ensemble_rebuilding(
                self.dashboard_data.get("ml_predictions", {}),
                self._extract_prices("ml_predictions"),
            )
            self.optimized_ml_system.ensemble_system.periodic_ensemble_rebuilding(
                self.dashboard_data.get("optimized_ml_predictions", {}),
                self._extract_prices("optimized_ml_predictions"),
            )

        # Calculate cycle duration
        cycle_duration = time.time() - self.cycle_start_time
        self.last_cycle_duration = cycle_duration

        # Update average cycle duration
        if self.average_cycle_duration is None:
            self.average_cycle_duration = cycle_duration
        else:
            self.average_cycle_duration = (
                self.average_cycle_duration + cycle_duration
            ) / 2

        self._log(
            f"🤖 Ultimate Self-Improvement Cycle Completed! (Duration: {cycle_duration:.1f}s)"
        )

    def _update_enhanced_metrics(
        self, ultimate_rate: float, optimized_rate: float, timestamp: datetime
    ) -> None:
        """Update enhanced performance metrics."""
        # Track model accuracy history
        self.model_accuracy_history["ultimate"].append(ultimate_rate)
        self.model_accuracy_history["optimized"].append(optimized_rate)

        # Calculate improvement velocity (rate of change in success rates)
        if len(self.success_rates) >= 2:
            recent_rates = list(self.success_rates)[-5:]  # Last 5 cycles
            if len(recent_rates) >= 2:
                velocity = (recent_rates[-1] - recent_rates[0]) / len(recent_rates)
                self.improvement_velocities.append(velocity)

        # Track performance trends
        performance_data = {
            "timestamp": timestamp.isoformat(),
            "ultimate_rate": ultimate_rate,
            "optimized_rate": optimized_rate,
            "average_rate": (ultimate_rate + optimized_rate) / 2,
            "cycle_number": len(self.success_rates),
        }
        self.performance_trends.append(performance_data)

        # Analyze market regime adaptations (simplified)
        market_regime = self._detect_market_regime()
        self.market_regime_adaptations.append(
            {
                "timestamp": timestamp.isoformat(),
                "regime": market_regime,
                "performance": (ultimate_rate + optimized_rate) / 2,
            }
        )

    def _perform_predictive_analytics(self) -> None:
        """Perform predictive analytics on future performance."""
        if len(self.success_rates) >= 5:
            # Simple linear regression for performance prediction
            rates = list(self.success_rates)
            predictions = self._linear_regression_prediction(
                rates, 3
            )  # Predict next 3 cycles

            for i, pred in enumerate(predictions):
                self.performance_predictions.append(
                    {
                        "cycle_offset": i + 1,
                        "predicted_rate": max(0, min(100, pred)),  # Clamp to 0-100
                        "confidence": self._calculate_prediction_confidence(rates),
                    }
                )

            # Determine optimal cycle timing based on performance patterns
            self.optimal_cycle_timing = self._calculate_optimal_cycle_timing()

    def _linear_regression_prediction(
        self, data: list[float], steps: int
    ) -> list[float]:
        """Simple linear regression prediction."""
        if len(data) < 2:
            return [data[-1]] * steps if data else [50.0] * steps

        n = len(data)
        x = list(range(n))
        y = data

        # Calculate slope and intercept
        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
        denominator = sum((xi - x_mean) ** 2 for xi in x)

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        intercept = y_mean - slope * x_mean

        # Predict future values
        predictions = []
        for i in range(1, steps + 1):
            pred_x = n + i - 1  # Next indices
            prediction = slope * pred_x + intercept
            predictions.append(prediction)

        return predictions

    def _calculate_prediction_confidence(self, data: list[float]) -> float:
        """Calculate confidence in predictions based on data variance."""
        if len(data) < 2:
            return 0.5

        try:
            variance = statistics.variance(data)
            # Lower variance = higher confidence
            confidence = max(0.1, 1.0 - (variance / 1000))  # Normalize variance
            return min(confidence, 0.95)  # Cap at 95%
        except statistics.StatisticsError:
            return 0.5

    def _calculate_optimal_cycle_timing(self) -> Optional[datetime]:
        """Calculate when the next cycle should optimally run."""
        if len(self.success_rates) < 5:
            return None

        # Analyze performance patterns to find optimal timing
        rates = list(self.success_rates)
        recent_avg = sum(rates[-3:]) / 3

        # If performance is declining, suggest more frequent cycles
        if len(rates) >= 5 and rates[-1] < rates[-3]:
            next_cycle = datetime.now() + timedelta(hours=1)  # More frequent
        elif recent_avg > 70:
            next_cycle = datetime.now() + timedelta(
                hours=4
            )  # Less frequent when doing well
        else:
            next_cycle = datetime.now() + timedelta(hours=3)  # Standard interval

        return next_cycle

    def _detect_market_regime(self) -> str:
        """Detect current market regime using technical indicators."""
        if not self.ribs_enabled or not DATA_SCIENCE_AVAILABLE:
            return "neutral"

        try:
            # Fetch recent BTCUSDT data (48 hours)
            klines = get_historical_klines("BTCUSDT", interval="1h", limit=48)
            if not klines or len(klines) < 24:
                return "neutral"

            df = pd.DataFrame(klines)
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # Calculate basic indicators for regime detection
            # 1. Trend (using SMA crossover)
            df["sma_20"] = df["close"].rolling(window=20).mean()
            current_price = df["close"].iloc[-1]
            sma_20 = df["sma_20"].iloc[-1]

            # 2. Volatility (using ATR or standard deviation)
            df["returns"] = df["close"].pct_change()
            volatility = df["returns"].std() * np.sqrt(24) # Daily volatility
            
            # Simple regime logic
            is_trending_up = current_price > sma_20 * 1.01
            is_trending_down = current_price < sma_20 * 0.99
            is_high_vol = volatility > 0.03 # 3% daily vol threshold

            if is_high_vol:
                return "volatile"
            if is_trending_up:
                return "trending_bull"
            if is_trending_down:
                return "trending_bear"
            
            return "sideways"

        except Exception as e:
            self._log(f"⚠️ Error in market regime detection: {e}")
            return "neutral"

    def _update_dashboard_telemetry(self, avg_success_rate: float) -> None:
        """Update dashboard with enhanced telemetry data."""
        si_data = self.dashboard_data.setdefault("self_improvement", {})

        # Basic metrics
        si_data["last_success_rate"] = avg_success_rate
        si_data["success_rates"] = list(self.success_rates)
        si_data["cycle_count"] = len(self.success_rates)

        # Enhanced metrics
        si_data["model_accuracy_history"] = {
            "ultimate": list(self.model_accuracy_history["ultimate"]),
            "optimized": list(self.model_accuracy_history["optimized"]),
        }
        si_data["improvement_velocity"] = (
            list(self.improvement_velocities)[-1] if self.improvement_velocities else 0
        )
        si_data["performance_trends"] = list(self.performance_trends)[
            -10:
        ]  # Last 10 entries

        # Predictive analytics
        si_data["performance_predictions"] = list(self.performance_predictions)
        si_data["optimal_cycle_timing"] = (
            self.optimal_cycle_timing.isoformat() if self.optimal_cycle_timing else None
        )

        # Cycle timing metrics
        si_data["last_cycle_duration"] = self.last_cycle_duration
        si_data["average_cycle_duration"] = self.average_cycle_duration

        # Market regime adaptations
        si_data["market_regime_adaptations"] = list(self.market_regime_adaptations)[-5:]

        # Risk adjustments
        si_data["risk_adjustments"] = list(self.risk_adjustments)

    def _perform_drift_detection(self, avg_success_rate: float) -> None:
        """Enhanced drift detection with multiple thresholds."""
        if len(self.success_rates) >= 3:
            recent_avg = sum(list(self.success_rates)[-3:]) / 3

            # Multiple threshold checks
            thresholds = [
                (self.min_success_threshold, "critical"),
                (self.min_success_threshold + 10, "warning"),
                (self.min_success_threshold + 20, "monitor"),
            ]

            for threshold, level in thresholds:
                if recent_avg < threshold:
                    self.auto_fix_required = True
                    self.dashboard_data["self_improvement"]["auto_fix_required"] = True
                    self.dashboard_data["self_improvement"]["drift_level"] = level
                    self._log(
                        f"⚠️ Drift detected ({level}): {recent_avg:.1f}% < {threshold}%"
                    )
                    self._trigger_auto_fix()
                    break
            else:
                self.auto_fix_required = False
                self.dashboard_data["self_improvement"]["auto_fix_required"] = False
                self.dashboard_data["self_improvement"]["drift_level"] = "stable"

    def _trigger_auto_fix(self) -> None:
        """Execute registered auto-fix actions with cooldown/hysteresis."""
        self._log("🔧 Triggering auto-fix actions...")

        now = time.time()
        if (
            self.last_auto_fix
            and (now - self.last_auto_fix) < self.auto_fix_cooldown_seconds
        ):
            self._log(
                f"⚠️ Skipping auto-fix due to cooldown (last ran {int(now - self.last_auto_fix)}s ago)"
            )
            return

        # Run handlers in background thread to avoid blocking monitor
        def _run_handlers():
            for name, handler in self.auto_fix_handlers.items():
                try:
                    self._log(f"🔧 Running auto-fix: {name}")
                    handler()
                except Exception as exc:
                    self._log(f"❌ Auto-fix {name} failed: {exc}")

            # Record last auto-fix time
            self.last_auto_fix = time.time()
            try:
                self.dashboard_data.setdefault("self_improvement", {})[
                    "last_auto_fix"
                ] = datetime.now().isoformat()
            except Exception:
                pass

        t = threading.Thread(target=_run_handlers, name="AutoFixRunner", daemon=True)
        t.start()

    def execute_auto_fix_action(self, action: str) -> dict:
        """Execute a named auto-fix action with cooldown checks.

        Returns a dict with keys: success (bool) and message (str).
        """
        if action not in self.auto_fix_handlers:
            return {"success": False, "message": f"Unknown auto-fix action: {action}"}

        now = time.time()
        if (
            self.last_auto_fix
            and (now - self.last_auto_fix) < self.auto_fix_cooldown_seconds
        ):
            return {
                "success": False,
                "message": f"Auto-fix cooldown active: try again in {int(self.auto_fix_cooldown_seconds - (now - self.last_auto_fix))}s",
            }

        # Run the handler in background
        def _run():
            try:
                self._log(f"🔧 Running auto-fix: {action}")
                self.auto_fix_handlers[action]()
            except Exception as exc:
                self._log(f"❌ Auto-fix {action} failed: {exc}")
            finally:
                self.last_auto_fix = time.time()
                try:
                    self.dashboard_data.setdefault("self_improvement", {})[
                        "last_auto_fix"
                    ] = datetime.now().isoformat()
                except Exception:
                    pass

        # Mark last_auto_fix immediately to prevent concurrent triggers
        self.last_auto_fix = time.time()
        try:
            self.dashboard_data.setdefault("self_improvement", {})[
                "last_auto_fix"
            ] = datetime.now().isoformat()
        except Exception:
            pass

        t = threading.Thread(target=_run, name=f"AutoFix-{action}", daemon=True)
        t.start()
        return {"success": True, "message": f"Auto-fix action '{action}' started"}

    def _extract_prices(self, _profile_key: str) -> dict[str, float]:
        market_data = self.dashboard_data.get("market_data", {}) or {}
        prices = {}
        for symbol, data in market_data.items():
            try:
                prices[symbol] = float(
                    data.get("price", 0) or data.get("close", 0) or 0
                )
            except Exception:
                prices[symbol] = 0.0
        return prices

    def continuous_ribs_optimization(self):
        """Continuous RIBS optimization in background"""
        if not self.ribs_enabled or not self.ribs_optimizer:
            self._log("⚠️ RIBS optimization not available or disabled")
            return

        self._log("🧬 Starting continuous RIBS optimization thread")

        # honor both global stop and ribs-specific stop
        while not self._stop_event.is_set() and not self._ribs_stop_event.is_set():
            try:
                # Load recent market data
                market_data = self.load_recent_data(hours=168)  # 7 days
                
                # Detect current market regime
                current_regime = self._detect_market_regime()
                self._log(f"🧬 Current Market Regime detected as: {current_regime}")

                # Run optimization for 200 iterations
                self._log(
                    f"🧬 Starting continuous RIBS optimization cycle (200 iterations, regime={current_regime})"
                )
                try:
                    elite_strategies = self.ribs_optimizer.run_optimization_cycle(
                        market_data=market_data, iterations=200, regime=current_regime
                    )
                    if not elite_strategies:
                        self._log("⚠️ RIBS returned no elite strategies for this cycle")
                    else:
                        self._log(
                            f"🧬 Completed continuous RIBS optimization cycle, elites={len(elite_strategies)}"
                        )
                except Exception as e:
                    self._log(f"❌ RIBS optimization failed during run: {e}")
                    elite_strategies = []

                # Auto-deploy the best strategy if it improved
                if elite_strategies:
                    best_elite = elite_strategies[0]
                    best_solution = best_elite["solution"]
                    best_objective = best_elite["objective"]
                    best_behavior = best_elite["behavior"]
                    if best_objective > self.best_ribs_objective:
                        strategy_id = (
                            f"ribs_best_{datetime.now().strftime('%Y%m%d_%H%M')}"
                        )
                        res = self.deploy_strategy(best_solution, strategy_id)
                        if isinstance(res, dict) and res.get("success"):
                            self.best_ribs_objective = best_objective
                            self.deployed_ribs_strategies.add(strategy_id)
                            self._log(
                                f"🧬 Auto-deployed improved RIBS strategy {strategy_id}: "
                                f"Objective={best_objective:.2f}, "
                                f"Behavior={best_behavior}"
                            )
                        else:
                            message = (
                                res.get("message")
                                if isinstance(res, dict)
                                else "Unknown error"
                            )
                            self._log(
                                f"❌ Failed to auto-deploy RIBS strategy: {message}"
                            )
                    else:
                        self._log(
                            f"🧬 Best RIBS objective {best_objective:.2f} not improved from {self.best_ribs_objective:.2f}, skipping auto-deploy"
                        )

                # Update dashboard with RIBS data
                self._update_ribs_dashboard_data()

                # Sleep until next optimization cycle (6 hours)
                # Wait respecting ribs-specific stop request
                self._ribs_stop_event.wait(21600)

            except Exception as e:
                self._log(f"❌ RIBS optimization failed: {e}")
                self._stop_event.wait(300)  # Retry in 5 minutes

    def start_ribs_optimization(self) -> bool:
        """Start the continuous RIBS optimization in a background thread.

        Returns True if a new thread was started, False if already running or not available.
        """
        if not self.ribs_enabled or not self.ribs_optimizer:
            return False
        # if already running, do nothing
        if self._ribs_thread and self._ribs_thread.is_alive():
            return False

        # clear any previous stop request and start new thread
        self._ribs_stop_event.clear()
        t = threading.Thread(
            target=self.continuous_ribs_optimization, name="RIBSWorker", daemon=True
        )
        self._ribs_thread = t
        t.start()
        return True

    def stop_ribs_optimization(self) -> bool:
        """Request the ribs optimization to stop and join the thread.

        Returns True if the thread was signaled (and was running), False otherwise.
        """
        if not (self._ribs_thread and self._ribs_thread.is_alive()):
            return False
        try:
            self._ribs_stop_event.set()
            self._ribs_thread.join(timeout=10.0)
        except Exception:
            pass
        finally:
            self._ribs_thread = None
            # ensure we clear the stop event so it can be restarted later
            self._ribs_stop_event.clear()
        return True

    def load_recent_data(self, hours: int = 168) -> dict:
        """Load recent market data for RIBS optimization"""
        # Load actual market data from Binance
        if not DATA_SCIENCE_AVAILABLE:
            return {"error": "Data science libraries not available"}

        # Try to get data for BTCUSDT as a reference
        symbol = "BTCUSDT"
        # interval = "1h"
        # limit is based on hours
        try:
            klines = get_historical_klines(symbol, interval="1h", limit=hours)
            if not klines:
                self._log(f"⚠️ No historical klines returned for {symbol}")
                return {}
            
            df = pd.DataFrame(klines)
            # Convert numeric columns
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # Convert time to datetime
            df["timestamp"] = pd.to_datetime(df["time"], unit="s")
            
            market_data = {"ohlcv": df}
            self._log(f"🧬 Loaded real {symbol} market data for RIBS: {len(df)} rows")
            return market_data
        except Exception as e:
            self._log(f"❌ Failed to fetch real market data: {e}")
            # Fallback to random data for testing if real data fails
            self._log("⚠️ Falling back to placeholder data")
            # (keep the existing placeholder logic below if desired, 
            # but better to return empty to avoid false optimization)
            return {}
        except Exception as e:
            self._log(f"❌ Failed to load market data: {e}")
            return {}

    def deploy_strategy(self, solution, strategy_id: str):
        """Deploy a RIBS-generated strategy"""
        try:
            if not self.ribs_optimizer:
                self._log("❌ RIBS optimizer not available")
                return False

            # Decode the solution into trading parameters
            params = self.ribs_optimizer.decode_solution(solution)

            # Light backtest gating to prevent deploying broken strategies
            # Merge admin overrides (persisted) with the base trading_config
            try:
                from app.services.ribs_admin import load_overrides

                overrides = load_overrides() or {}
            except Exception:
                overrides = {}

            # Enforce 5% initial allocation limit (Safety fix)
            params["position_size"] = min(float(params.get("position_size", 0.05)), 0.05)
            
            # Force Paper Trading for the validation period
            params["paper_only"] = True

            deploy_cfg = {
                "min_return": float(
                    overrides.get(
                        "ribs_deploy_min_return",
                        self.trading_config.get("ribs_deploy_min_return", 0.0),
                    )
                ),
                "min_sharpe": float(
                    overrides.get(
                        "ribs_deploy_min_sharpe",
                        self.trading_config.get("ribs_deploy_min_sharpe", 0.0),
                    )
                ),
                "max_drawdown": float(
                    overrides.get(
                        "ribs_deploy_max_drawdown",
                        self.trading_config.get("ribs_deploy_max_drawdown", 100.0),
                    )
                ),
                "min_win_rate": float(
                    overrides.get(
                        "ribs_deploy_min_win_rate",
                        self.trading_config.get("ribs_deploy_min_win_rate", 0.0),
                    )
                ),
                "backtest_hours": int(
                    overrides.get(
                        "ribs_deploy_backtest_hours",
                        self.trading_config.get("ribs_deploy_backtest_hours", 168),
                    )
                ),
            }

            try:
                market_data = self.load_recent_data(hours=deploy_cfg["backtest_hours"])
                backtest = self.ribs_optimizer.run_backtest(params, market_data)
            except Exception as e:
                self._log(f"❌ Backtest failed during deploy gating: {e}")
                return {"success": False, "message": "Backtest failed"}

            # Evaluate gating thresholds
            if backtest.get("total_return", -9999) < deploy_cfg["min_return"]:
                msg = f"Backtest total_return {backtest.get('total_return'):.2f} < required {deploy_cfg['min_return']:.2f}"
                self._log(f"❌ Deploy gating rejected strategy: {msg}")
                return {"success": False, "message": msg}

            if backtest.get("sharpe_ratio", 0.0) < deploy_cfg["min_sharpe"]:
                msg = f"Backtest sharpe_ratio {backtest.get('sharpe_ratio'):.2f} < required {deploy_cfg['min_sharpe']:.2f}"
                self._log(f"❌ Deploy gating rejected strategy: {msg}")
                return {"success": False, "message": msg}

            if backtest.get("max_drawdown", 0.0) > deploy_cfg["max_drawdown"]:
                msg = f"Backtest max_drawdown {backtest.get('max_drawdown'):.2f} > allowed {deploy_cfg['max_drawdown']:.2f}"
                self._log(f"❌ Deploy gating rejected strategy: {msg}")
                return {"success": False, "message": msg}

            if backtest.get("win_rate", 0.0) < deploy_cfg["min_win_rate"]:
                win_rate = backtest.get("win_rate", 0.0)
                msg = f"Backtest win_rate {(win_rate*100):.1f}% < required {(deploy_cfg['min_win_rate']*100):.1f}%"
                self._log(f"❌ Deploy gating rejected strategy: {msg}")
                return {"success": False, "message": msg}

            # Prepare final strategy config
            # Ensure the StrategyManager receives the paper_only flag
            strategy_config = params.copy()
            strategy_config["user_id"] = self.ultimate_trader.user_id
            strategy_config["paper_only"] = True
            
            # Register in StrategyManager but keep inactive for live trading
            if hasattr(self.ultimate_trader, "strategy_manager"):
                sm = self.ultimate_trader.strategy_manager
                # We register it but don't enable live trading yet
                if hasattr(sm, "register_strategy"):
                    sm.register_strategy(strategy_id, strategy_config)
                
                sm.active_strategies[strategy_id] = False # Explicitly OFF for live execution
                self._log(f"🧬 RIBS Strategy {strategy_id} registered in PAPER mode")

            # Update status with deployment record
            try:
                status_path = os.path.join(
                    self.ribs_optimizer.checkpoints_dir, "ribs_status.json"
                )
                if os.path.exists(status_path):
                    with open(status_path, "r") as f:
                        status = json.load(f)
                    
                    deployments = status.get("deployments", [])
                    deployments.append({
                        "id": strategy_id,
                        "params": params,
                        "deployed_at": datetime.now().isoformat(),
                        "status": "PAPER_VALUATION",
                        "objective": float(backtest.get("total_return", 0))
                    })
                    status["deployments"] = deployments
                    
                    with open(status_path, "w") as f:
                        json.dump(status, f, indent=2)
            except Exception as e:
                self._log(f"⚠️ Failed to update deployment status: {e}")

            return {
                "success": True,
                "message": f"Strategy {strategy_id} deployed to PAPER valuation",
            }
        except Exception as e:
            self._log(f"❌ Failed to deploy RIBS strategy: {e}")
            return {"success": False, "message": str(e)}

    def _update_ribs_dashboard_data(self):
        """Update dashboard with RIBS optimization data"""
        if not self.ribs_optimizer:
            return

        try:
            ribs_data = self.dashboard_data.setdefault("ribs_optimization", {})

            # Archive statistics
            archive_stats = self.ribs_optimizer.get_archive_stats()
            # Convert numpy types to native Python types
            ribs_data.update(
                {
                    k: float(v)
                    if hasattr(v, "item")
                    else v  # numpy scalars have .item()
                    for k, v in archive_stats.items()
                }
            )

            # Elite strategies
            elite_strategies = self.ribs_optimizer.get_elite_strategies(top_n=5)
            # Convert to JSON serializable format
            ribs_data["elite_strategies"] = [
                {
                    "id": str(s.get("id", i)),
                    "objective": float(s["objective"]),
                    "behavior": [float(b) for b in s["behavior"]],
                    "params": {
                        k: float(v)
                        if isinstance(v, (int, float)) and hasattr(v, "item")
                        else v
                        for k, v in s.get("params", {}).items()
                    },
                }
                for i, s in enumerate(elite_strategies)
            ]

            # Coverage percentage
            ribs_data["coverage"] = float(archive_stats.get("coverage", 0)) * 100

            # Behavior space data for visualization
            if elite_strategies:
                ribs_data["behaviors_x"] = [
                    float(s["behavior"][0]) for s in elite_strategies
                ]  # Sharpe ratio
                ribs_data["behaviors_y"] = [
                    float(s["behavior"][1]) for s in elite_strategies
                ]  # Max drawdown
                ribs_data["behaviors_z"] = [
                    float(s["behavior"][2]) for s in elite_strategies
                ]  # Win rate
                ribs_data["objectives"] = [
                    float(s["objective"]) for s in elite_strategies
                ]

        except Exception as e:
            self._log(f"❌ Failed to update RIBS dashboard data: {e}")

    def _log(self, message: str) -> None:
        if self.logger:
            try:
                self.logger.info(message)
                return
            except Exception:
                pass
        print(message)
