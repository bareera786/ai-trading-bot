import os
import sys
import atexit
import time
import math
import random
import logging
import threading
import collections
from copy import deepcopy
from urllib.parse import urlparse
import numpy as np
import pandas as pd
import requests
import json
import talib
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from app.extensions import socketio
print(f"DEBUG: socketio imported: {socketio}")

from app.core.config_trading import TRADING_CONFIG
from app.services.pathing import resolve_profile_path, BOT_PROFILE, PROJECT_ROOT
from app.core.logging import log_component_event, log_component_debug, setup_application_logging
setup_logger = setup_application_logging
from app.services import (
    get_real_market_data,
    BinanceMarketDataHelper,
    create_ml_services,
    create_trading_services,
    attach_trading_ml_dependencies,
    ComprehensiveTradeHistory,
    TimescaleDBService,
    FuturesManualService,
    BinanceFuturesTrader,
)
from app.services.binance import _coerce_bool
from app.services import BacktestManager
from app.services.trading import RealBinanceTrader
from app.services.health import HealthReportService, evaluate_health_payload



# Modules
from app.ml.training.system import UltimateMLTrainingSystem, OptimizedMLTrainingSystem
from app.ml.training.futures_system import FuturesMLTrainingSystem
from app.ml.components.parallel import ParallelPredictionEngine
from app.ml.components.ensemble import UltimateEnsembleSystem
from app.ml.components.crt import CRTSignalGenerator
from app.ml.components.ict import ICTIndicatorModule
from app.ml.components.smc import SMCIndicatorModule
from app.strategies.qfm import QuantumFusionMomentumEngine
from app.strategies.manager import StrategyManager
from app.strategies.oracle import ModelOracle
from app.core.governor import EnsembleGovernor
from app.ml.inference.manager import AsyncInferenceManager
from app.core.safety import SafetyManager
from app.risk.manager import AdaptiveRiskManager
from app.risk.stop_loss import AdvancedStopLossSystem
from app.core.telemetry import PerformanceMonitor
from app.trading.futures.module import FuturesTradingModule
from app.runtime.symbols import (
    TOP_SYMBOLS,
    FUTURES_SYMBOLS,
    INDICATOR_SIGNAL_OPTIONS,
    get_active_trading_universe,
    normalize_symbol as _normalize_symbol,
    get_all_known_symbols,
    attach_dashboard_data,
    refresh_symbol_counters,
    MARKET_CAP_WEIGHTS,
    DISABLED_SYMBOLS,
    get_disabled_symbols,
    clear_symbol_from_dashboard,
    is_symbol_disabled,
    disable_symbol,
    enable_symbol,
    save_symbol_state,
)
from app.models import User, UserPortfolio
from app.runtime.persistence import build_persistence_runtime
from app.runtime.builder import assemble_runtime_context
from app.runtime.indicators import BEST_INDICATORS, IndicatorSelectionManager
from app.runtime.services import build_service_runtime
from app.runtime.background import build_background_runtime
from app.runtime.payloads import build_ai_bot_context_payload


AI_BOT_VERSION = "2.6.0"
bot_start_time = datetime.utcnow()



# Models (assuming usage)
try:
    from app.models import UserPortfolio, UserTrade, db
except ImportError:
    pass # Might be used inside methods

# Binance client classes
try:
    from binance.client import Client as BinanceClient
    from binance.exceptions import BinanceAPIException
except ImportError:
    BinanceClient = None
    BinanceAPIException = Exception

try:
    from binance.um_futures import UMFutures as BinanceFuturesClient
except ImportError:
    BinanceFuturesClient = None

# DEBUG: Throttled/Buffered Logger for loop diagnostics
class ThrottledLogger:
    def __init__(self, logger, interval=60):
        self.logger = logger
        self.interval = interval
        self.last_log = {}

    def info(self, key, msg):
        now = time.time()
        if now - self.last_log.get(key, 0) > self.interval:
            self.logger.info(msg)
            self.last_log[key] = now
            
    def warning(self, key, msg):
        now = time.time()
        if now - self.last_log.get(key, 0) > self.interval:
            self.logger.warning(msg)
            self.last_log[key] = now

debug_logger = None # Will init in __init__

# ==================== ULTIMATE AI TRADER ====================
class UltimateAIAutoTrader:
    def _get_trading_config(self) -> dict:
        cfg = getattr(self, "trading_config", None)
        return cfg if isinstance(cfg, dict) else TRADING_CONFIG

    def _stabilize_ensemble_confidence(self, confidence_value, default: float = 0.5) -> float:
        """Return a stable, per-instance ensemble confidence value.

        This is intentionally conservative: it only guards against non-finite
        inputs and rate-limits extreme single-tick jumps.
        """

        previous = getattr(self, "_last_ensemble_confidence", None)
        previous_float = None
        if isinstance(previous, (int, float)):
            try:
                previous_float = float(previous)
            except Exception:
                previous_float = None
            else:
                if not math.isfinite(previous_float):
                    previous_float = None

        try:
            candidate = float(confidence_value)
        except Exception:
            candidate = None

        if candidate is None or not math.isfinite(candidate):
            stabilized = previous_float if previous_float is not None else float(default)
            setattr(self, "_last_ensemble_confidence", stabilized)
            return stabilized

        max_jump = 0.35


        stabilized = candidate
        if previous_float is not None and max_jump > 0:
            delta = candidate - previous_float
            if abs(delta) > max_jump:
                stabilized = previous_float + (max_jump if delta > 0 else -max_jump)
                stabilized = max(0.0, min(1.0, stabilized))

        setattr(self, "_last_ensemble_confidence", stabilized)
        return stabilized

    def initialize_performance_analytics(self):
        """Initialize comprehensive performance analytics system"""
        self.performance_analytics = {
            "qfm_performance_correlation": {},
            "strategy_qfm_sensitivity": {},
            "market_regime_performance": {},
            "time_based_performance": {},
            "risk_adjusted_metrics": {},
            "predictive_analytics": {},
            "analytics_cache": {},
            "last_update": 0,
        }

    def analyze_qfm_strategy_performance(
        self, symbol=None, timeframe="1d", analysis_window=30
    ):
        """Analyze performance correlation between QFM metrics and strategy results"""
        analytics = {}

        # Get performance data
        performance_data = []
        for strategy_name in self.strategies:  # type: ignore
            perf = self.strategy_performance.get(strategy_name, {})  # type: ignore
            if perf.get("total_trades", 0) > 0:
                performance_data.append(
                    {
                        "strategy": strategy_name,
                        "win_rate": perf.get("win_rate", 0),
                        "total_pnl": perf.get("total_pnl", 0),
                        "total_trades": perf.get("total_trades", 0),
                        "avg_pnl": perf.get("total_pnl", 0)
                        / perf.get("total_trades", 0),
                    }
                )

        if not performance_data:
            return {"error": "Insufficient performance data"}

        # Analyze QFM correlations if QFM engine available
        if self.qfm_engine and hasattr(self.qfm_engine, "get_historical_features"):
            try:
                qfm_history = self.qfm_engine.get_historical_features(  # type: ignore
                    symbol, timeframe, analysis_window
                )

                for strategy_data in performance_data:
                    strategy_name = strategy_data["strategy"]
                    correlations = self._calculate_qfm_performance_correlations(
                        qfm_history, strategy_name, analysis_window
                    )
                    analytics[f"{strategy_name}_qfm_correlation"] = correlations

            except Exception as e:
                analytics["qfm_analysis_error"] = str(e)

        # Calculate strategy comparisons
        analytics["strategy_comparison"] = self._compare_strategy_performance(
            performance_data
        )

        # Calculate risk-adjusted metrics
        analytics["risk_adjusted_metrics"] = self._calculate_risk_adjusted_metrics(
            performance_data
        )

        # Market regime analysis
        analytics["market_regime_analysis"] = self._analyze_market_regime_performance()

        return analytics

    def _maybe_record_system_trade(self, trade_record: dict[str, Any]) -> None:
        """If enabled by TRADING_CONFIG, record an automated trade to the DB.

        This is a safe best-effort call to the module-level `record_user_trade`
        function. If no `system_trade_user_id` is configured, nothing is done.
        """
        try:
            cfg = TRADING_CONFIG
            if not cfg.get("record_system_trades_to_db"):
                log_component_event(
                    "TRADE_HISTORY",
                    "System trade recording is disabled (record_system_trades_to_db=False)",
                    level=logging.DEBUG,
                )
                return

            user_id = (
                (trade_record or {}).get("user_id")
                or getattr(self, "user_id", None)
                or cfg.get("system_trade_user_id")
            )
            if not user_id:
                # Nothing to do without a resolved user id
                log_component_event(
                    "TRADE_HISTORY",
                    "System trade recording skipped: no user_id resolved",
                    level=logging.DEBUG,
                )
                return

            # record_user_trade handles UUID/int conversion and app context internally
            symbol = trade_record.get("symbol")
            side = trade_record.get("side")
            quantity = (
                trade_record.get("quantity") or trade_record.get("base_received") or 0
            )
            price = trade_record.get("price") or trade_record.get("entry_price") or 0
            trade_type = (
                trade_record.get("type") or trade_record.get("action_type") or "system"
            )
            signal_source = trade_record.get("signal")
            confidence = trade_record.get("confidence")
            
            # Determine market_type and profile
            market_type = trade_record.get("market_type") or ("FUTURES" if "futures" in trade_type.lower() else "SPOT")
            profile = trade_record.get("profile") or ("ULTIMATE" if "ultimate" in trade_type.lower() or "ultimate" in str(signal_source).lower() else "OPTIMIZED")

            # Call module-level helper to persist to DB
            # record_user_trade handles UUID conversion and app context internally
            ok = record_user_trade(
                user_id,  # Pass as-is; record_user_trade handles UUID/int conversion
                symbol,
                side,
                quantity,
                price,
                trade_type=trade_type,
                signal_source=signal_source,
                confidence_score=confidence,
                market_type=market_type,
                profile=profile,
            )

            if ok:
                log_component_event(
                    "TRADE_HISTORY",
                    f"Recorded system trade to DB for user_id={user_id}: {symbol} {side} qty={quantity} price={price}",
                    level=logging.INFO,
                )
            else:
                log_component_event(
                    "TRADE_HISTORY",
                    f"Failed to record system trade to DB for user_id={user_id}: {symbol} {side} qty={quantity} price={price}",
                    level=logging.WARNING,
                )
        except Exception as e:  # pragma: no cover - best effort
            log_component_event(
                "TRADE_HISTORY",
                f"Failed to record system trade: {e}",
                level=logging.WARNING,
            )

    def _calculate_qfm_performance_correlations(
        self, qfm_history, strategy_name, window
    ):
        """Calculate correlations between QFM features and strategy performance"""
        correlations = {}

        if not qfm_history:
            return correlations

        # Get strategy performance history
        strategy_trades = []
        for entry in self.ml_feedback.get("performance_history", []):  # type: ignore
            if entry["strategy"] == strategy_name:
                strategy_trades.append(entry)

        if len(strategy_trades) < 5 or not qfm_history:
            return correlations
        
        # Align data by time (simple approximation)
        # In a real impl, we'd match timestamps. Here we just take the last N.
        
        # Calculate feature correlations against trade PnL
        features_to_check = ["velocity", "acceleration", "jerk", "regime_score", "trend_confidence"]
        
        for feature in features_to_check:
            feature_values = []
            pnl_values = []
            
            # Match recent trades to recent features
            # This is a simplified logic to restore functionality
            min_len = min(len(strategy_trades), len(qfm_history))
            for i in range(min_len):
                trade = strategy_trades[-(i+1)]
                features = qfm_history[-(i+1)].get("features", {})
                
                if feature in features:
                    feature_values.append(features[feature])
                    pnl_values.append(trade["pnl"])
            
            if len(feature_values) > 3:
                try:
                    correlation = np.corrcoef(feature_values, pnl_values)[0, 1]
                    if not math.isnan(correlation):
                        correlations[feature] = {
                            "correlation": correlation,
                            "strength": abs(correlation)
                        }
                except Exception:
                    pass
                    
        return correlations

    def _compare_strategy_performance(self, performance_data):
        """Compare and rank strategies"""
        if not performance_data:
            return {}

        # Sort by different metrics
        by_win_rate = sorted(
            performance_data, key=lambda x: x["win_rate"], reverse=True
        )
        by_pnl = sorted(performance_data, key=lambda x: x["total_pnl"], reverse=True)
        by_avg_pnl = sorted(performance_data, key=lambda x: x["avg_pnl"], reverse=True)

        rankings = {}
        for strategy in performance_data:
            name = strategy["strategy"]
            rankings[name] = {
                "win_rate_rank": next(
                    i for i, s in enumerate(by_win_rate) if s["strategy"] == name
                ),
                "pnl_rank": next(
                    i for i, s in enumerate(by_pnl) if s["strategy"] == name
                ),
                "composite_score": (
                    strategy["win_rate"] * 0.4
                    + strategy["avg_pnl"] * 100 * 0.4
                    + strategy["total_pnl"] * 0.2
                ),
            }

        return {
            "rankings": rankings,
            "best_by_win_rate": by_win_rate[0]["strategy"] if by_win_rate else None,
            "best_by_pnl": by_pnl[0]["strategy"] if by_pnl else None,
            "best_by_avg_pnl": by_avg_pnl[0]["strategy"] if by_avg_pnl else None,
            "total_strategies": len(performance_data),
        }

    def _calculate_risk_adjusted_metrics(self, performance_data):
        """Calculate risk-adjusted performance metrics"""
        risk_metrics = {}

        for strategy_data in performance_data:
            strategy_name = strategy_data["strategy"]
            total_pnl = strategy_data["total_pnl"]
            total_trades = strategy_data["total_trades"]

            if total_trades == 0:
                continue

            # Get P&L history for volatility calculation
            pnl_history = []
            for entry in self.ml_feedback.get("performance_history", []):  # type: ignore
                if entry["strategy"] == strategy_name:
                    pnl_history.append(entry["pnl"])

            if len(pnl_history) < 5:
                continue

            # Calculate risk metrics
            pnl_array = np.array(pnl_history)
            volatility = np.std(pnl_array)
            avg_pnl = np.mean(pnl_array)
            max_drawdown = self._calculate_max_drawdown(pnl_history)

            # Sharpe ratio (assuming 0% risk-free rate)
            sharpe_ratio = avg_pnl / volatility if volatility > 0 else 0

            # Sortino ratio (downside deviation)
            downside_returns = pnl_array[pnl_array < 0]
            downside_deviation = (
                np.std(downside_returns) if len(downside_returns) > 0 else 0
            )
            sortino_ratio = (
                avg_pnl / downside_deviation if downside_deviation > 0 else 0
            )

            # Calmar ratio
            calmar_ratio = avg_pnl / abs(max_drawdown) if max_drawdown != 0 else 0

            risk_metrics[strategy_name] = {
                "sharpe_ratio": sharpe_ratio,
                "sortino_ratio": sortino_ratio,
                "calmar_ratio": calmar_ratio,
                "volatility": volatility,
                "max_drawdown": max_drawdown,
                "win_loss_ratio": strategy_data["win_rate"]
                / (100 - strategy_data["win_rate"])
                if strategy_data["win_rate"] < 100
                else float("inf"),
                "profit_factor": abs(total_pnl / sum(p for p in pnl_history if p < 0))
                if any(p < 0 for p in pnl_history)
                else float("inf"),
            }

        return risk_metrics

    def _calculate_max_drawdown(self, pnl_history):
        """Calculate maximum drawdown from P&L history"""
        if not pnl_history:
            return 0

        cumulative = np.cumsum(pnl_history)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative
        max_drawdown = np.max(drawdown)

        return max_drawdown

    def _analyze_market_regime_performance(self):
        """Analyze strategy performance across different market regimes"""
        regime_analysis = {}

        # Define regime categories based on QFM features
        regime_categories = {
            "trending_bull": lambda f: f.get("velocity", 0) > 0.3
            and f.get("trend_confidence", 0) > 0.7,
            "trending_bear": lambda f: f.get("velocity", 0) < -0.3
            and f.get("trend_confidence", 0) > 0.7,
            "sideways": lambda f: abs(f.get("velocity", 0)) < 0.2
            and f.get("regime_score", 0.5) < 0.4,
            "volatile": lambda f: abs(f.get("jerk", 0)) > 0.5,
            "calm": lambda f: abs(f.get("jerk", 0)) < 0.2,
        }

        for regime_name, regime_condition in regime_categories.items():
            regime_performance = {}

            for strategy_name in self.strategies:  # type: ignore
                regime_trades = []

                # Find trades in this regime
                for entry in self.ml_feedback.get("performance_history", []):  # type: ignore
                    if entry["strategy"] == strategy_name and entry.get("qfm_features"):
                        if regime_condition(entry["qfm_features"]):
                            regime_trades.append(entry)

                if len(regime_trades) >= 5:
                    wins = sum(1 for t in regime_trades if t["win"])
                    total_pnl = sum(t["pnl"] for t in regime_trades)

                    regime_performance[strategy_name] = {
                        "trades": len(regime_trades),
                        "win_rate": (wins / len(regime_trades)) * 100,
                        "total_pnl": total_pnl,
                        "avg_pnl": total_pnl / len(regime_trades),
                    }

            if regime_performance:
                regime_analysis[regime_name] = regime_performance

        return regime_analysis

    def get_strategy_recommendations(self):
        """Get AI-powered strategy recommendations based on analytics"""
        analytics = self.analyze_qfm_strategy_performance()

        if "error" in analytics:
            return {"error": analytics["error"]}

        recommendations = {}

        # Strategy comparison recommendations
        comparison = analytics.get("strategy_comparison", {})
        rankings = comparison.get("rankings", {})  # type: ignore

        if rankings:
            # Find best overall strategy
            best_strategy = max(
                rankings.items(), key=lambda x: x[1]["composite_score"]
            )[0]
            recommendations["best_overall_strategy"] = best_strategy

            # Find strategies that perform well in specific conditions
            regime_analysis = analytics.get("market_regime_analysis", {})
            for regime, regime_perf in regime_analysis.items():  # type: ignore
                if regime_perf:
                    best_in_regime = max(
                        regime_perf.items(), key=lambda x: x[1]["win_rate"]
                    )[0]
                    recommendations[f"best_in_{regime}"] = best_in_regime

        # Risk-adjusted recommendations
        risk_metrics = analytics.get("risk_adjusted_metrics", {})
        if risk_metrics:
            # Find strategy with best Sharpe ratio
            best_sharpe = max(risk_metrics.items(), key=lambda x: x[1]["sharpe_ratio"])  # type: ignore
            recommendations["best_risk_adjusted"] = best_sharpe

            # Find strategy with lowest volatility
            lowest_volatility = min(
                risk_metrics.items(), key=lambda x: x[1]["volatility"]  # type: ignore
            )[0]
            recommendations["lowest_volatility"] = lowest_volatility

        # QFM correlation recommendations
        qfm_correlations = {}
        for key, correlation_data in analytics.items():
            if "qfm_correlation" in key:
                strategy_name = key.replace("_qfm_correlation", "")
                qfm_correlations[strategy_name] = correlation_data

        if qfm_correlations:
            for strategy_name, correlations in qfm_correlations.items():
                if correlations:
                    # Find most important QFM features for this strategy
                    important_features = sorted(
                        correlations.items(),
                        key=lambda x: x[1]["strength"],
                        reverse=True,
                    )[:3]
                    recommendations[f"{strategy_name}_key_qfm_features"] = [
                        f[0] for f in important_features
                    ]

        return recommendations

    def generate_performance_report(self, report_type="comprehensive"):
        """Generate comprehensive performance report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "report_type": report_type,
            "summary": {},
            "strategies": {},
            "analytics": {},
            "recommendations": {},
        }

        # Basic summary
        total_strategies = len(self.strategies)  # type: ignore
        active_strategies = sum(
            1
            for s in self.strategy_performance.values()  # type: ignore
            if s.get("total_trades", 0) > 0
        )

        report["summary"] = {
            "total_strategies": total_strategies,
            "active_strategies": active_strategies,
            "total_trades": sum(
                s.get("total_trades", 0) for s in self.strategy_performance.values()  # type: ignore
            ),
            "total_pnl": sum(
                s.get("total_pnl", 0) for s in self.strategy_performance.values()  # type: ignore
            ),
        }

        # Individual strategy performance
        for strategy_name, perf in self.strategy_performance.items():  # type: ignore
            report["strategies"][strategy_name] = {
                "performance": perf,
                "parameters": self.strategies[strategy_name].parameters,  # type: ignore
                "last_updated": perf.get("last_updated", 0),
            }

        # Analytics
        if report_type in ["comprehensive", "analytics"]:
            report["analytics"] = self.analyze_qfm_strategy_performance()

        # Recommendations
        if report_type in ["comprehensive", "recommendations"]:
            report["recommendations"] = self.get_strategy_recommendations()

        # ML insights
        if hasattr(self, "ml_feedback"):
            report["ml_insights"] = self.get_ml_feedback_insights()  # type: ignore

        return report

    def reset_paper_balance(self, initial_balance=None):
        """Reset paper trading balance and clear positions."""
        if initial_balance is None:
            initial_balance = self.initial_balance
        self.balance = initial_balance
        self.peak_balance = initial_balance
        self.positions = {}
        # Reset specific metrics
        self.daily_pnl = 0
        self.max_drawdown = 0
        from app.core.logging import log_component_event
        import logging
        log_component_event(
            "PAPER_TRADING",
            f"Paper trading balance reset to {initial_balance}",
            level=logging.INFO
        )

    def emergency_reset_drawdown(self):
        """Reset drawdown metrics without clearing positions."""
        # Calculate current total (best effort approximation using cost basis if no prices)
        current_total = self.balance + sum(
            pos.get("quantity", 0) * (pos.get("avg_price") or pos.get("entry_price", 0))
            for pos in self.positions.values()
        )
        self.peak_balance = current_total
        self.max_drawdown = 0
        
        # Sync rolling history
        self._update_balance_history(current_total)
        
        from app.core.logging import log_component_event
        import logging
        log_component_event(
            "SAFETY",
            f"🚨 EMERGENCY DRAWDOWN RESET: Peak balance recalibrated to ${current_total:.2f}. Drawdown cleared.",
            level=logging.WARNING
        )

    def _update_balance_history(self, current_total):
        """Update rolling 24h balance history."""
        now = time.time()
        self.balance_history.append((now, current_total))
        # Prune older than 24h (86400 seconds)
        cutoff = now - 86400
        self.balance_history = [item for item in self.balance_history if item[0] > cutoff]

    def _get_rolling_max_drawdown(self, current_total):
        """Calculate max drawdown within the rolling 24h window."""
        if not self.balance_history:
            return 0.0
        
        window_peak = max(val for ts, val in self.balance_history)
        if window_peak <= 0:
            return 0.0
            
        rolling_dd = max(0.0, (window_peak - current_total) / window_peak)
        return rolling_dd

    def __init__(self, initial_balance=10000):
        self.app = None # injected by register_ai_bot_context
        logging.getLogger("ai_trading_bot").warning(f"DEBUG: UltimateAIAutoTrader initialized. ID={id(self)}")
        self.profile_prefix = getattr(self, "profile_prefix", "ULTIMATE")
        self.trade_type_label = getattr(self, "trade_type_label", "ULTIMATE_TRADE")
        self.strategy_label = getattr(self, "strategy_label", "50_INDICATORS_ULTIMATE")
        self.indicator_block_key = getattr(
            self, "indicator_block_key", "ultimate_ensemble"
        )
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}
        self.trading_config = deepcopy(TRADING_CONFIG)
        # NEW: Use ComprehensiveTradeHistory instead of EnhancedTradeHistory
        self.trade_history = ComprehensiveTradeHistory(log_callback=log_component_event)
        # Initialize TimescaleDB service for efficient candle storage
        # Parse DATABASE_URL to get connection parameters for TimescaleDB
        database_url = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")
        if database_url.startswith("postgresql://"):
            parsed = urlparse(database_url)
            db_host = parsed.hostname or "localhost"
            db_port = parsed.port or 5432
            db_name = parsed.path.lstrip("/")
            db_user = parsed.username or "trading_user"
            db_password = parsed.password or "secure_password_123"
            self.timescaledb_service = TimescaleDBService(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password,
                logger=bot_logger
            )
        else:
            # Fallback to default for SQLite or other databases
            self.timescaledb_service = TimescaleDBService(logger=bot_logger)
        self.trading_enabled = TRADING_CONFIG.get("auto_trade_enabled", False)
        self.paper_trading = False
        self.real_trader = RealBinanceTrader(
            api_key=None,
            api_secret=None,
            account_type="spot",
            testnet=_coerce_bool(os.getenv("USE_TESTNET", "1"), default=True),
            binance_client_cls=BinanceClient,
            api_exception_cls=BinanceAPIException,
            binance_log_manager=globals().get("binance_log_manager"),
            logger=bot_logger,
            coerce_bool=_coerce_bool,
            user_id=getattr(self, "user_id", "system_default"),  # SECURITY: Pass user_id for isolation
        )
        self.real_trading_enabled = False
        self.last_real_order = None
        self.last_futures_order = None
        self.latest_market_data = {}
        self.daily_pnl = 0
        self.max_drawdown = 0
        self.peak_balance = initial_balance
        self.balance_history = []  # List of (timestamp, value) for rolling DD
        self.ensemble_system = UltimateEnsembleSystem()
        self.risk_manager = AdaptiveRiskManager()
        self.safety_manager = SafetyManager(initial_balance=initial_balance)
        self.stop_loss_system = AdvancedStopLossSystem()
        self.parallel_engine = ParallelPredictionEngine()
        self.qfm_engine = QuantumFusionMomentumEngine()
        # QFM analytics must be per-trader (multi-user safe) and always initialized.
        self.initialize_performance_analytics()
        # NEW: CRT Module
        self.crt_generator = CRTSignalGenerator()
        self.symbol_min_notional_cache = {}
        self.real_equity_baseline = None
        self.auto_take_profit_state = {}
        self.futures_trader = None
        self.futures_trading_enabled = False

        self.bot_efficiency = {
            "total_trades": 0,
            "successful_trades": 0,
            "total_profit": 0,
            "learning_cycles": 0,
            "last_improvement": None,
            "ensemble_accuracy": 0.5,
            "risk_adjustment_history": [],
            "market_stress_history": [],
        }

        # Initialize Throttled Logger
        global debug_logger
        debug_logger = ThrottledLogger(bot_logger)

        print(
            f"🚀 {self.profile_prefix} AI Trader with All Advanced Systems & CRT Module Initialized"
        )
        
        # Phase B: Initialize Async Inference Manager
        # Non-blocking inference to decouple ML from execution loop
        _models_key = "optimized_models" if self.profile_prefix == "OPTIMIZED" else "ultimate_models"
        # We need to import resolve_profile_path locally if not available, or assume it's global
        # It is imported at module level: from app.services.pathing import resolve_profile_path
        try:
             _models_dir = resolve_profile_path(_models_key, allow_legacy=True)
        except Exception:
             _models_dir = _models_key # Fallback
        
        
        self.inference_manager = AsyncInferenceManager(
            models_dir=_models_dir,
            ml_system_class=OptimizedMLTrainingSystem
        )
        
        # Phase 7: Strategies + Oracle + Governor
        self.model_oracle = ModelOracle(self.inference_manager)
        self.governor = EnsembleGovernor()
        
        # Inject Oracle into strategies
        # (Assuming self.strategies is a dict of Strategy instances, 
        #  or accessible via self.strategy_manager)
        # Note: self.strategies is set via StrategyManager usually, but here it seems missing?
        # Let's check StrategyManager usage.
        self.strategy_manager = StrategyManager(user_id=getattr(self, "user_id", None))
        
        # --- RIBS MANUAL DEPLOYMENT OVERRIDE ---
        try:
            ribs_deploy_file = os.path.join("bot_persistence", "active_ribs_strategy.json")
            if os.path.exists(ribs_deploy_file):
                with open(ribs_deploy_file, "r") as f:
                    ribs_cfg = json.load(f)
                    ribs_params = ribs_cfg.get("params", {})
                    if ribs_params:
                        self.strategy_manager.update_parameters(ribs_params)
                        log_component_event(
                            "STRATEGY", 
                            f"🧬 Manual RIBS strategy applied: {ribs_cfg.get('id')} with allocation {ribs_cfg.get('overrides', {}).get('allocation')}",
                            level=logging.INFO
                        )
        except Exception as e:
            bot_logger.error(f"❌ Failed to load manual RIBS strategy: {e}")
        # ----------------------------------------

        for strat in self.strategy_manager.strategies.values():
            if hasattr(strat, "set_model_oracle"):
                strat.set_model_oracle(self.model_oracle)

        # NOTE: Do NOT start process in __init__ to avoid recursive spawning loops 
 
        # when imported by the child process itself.
        # self.inference_manager.start()

    def start_inference_service(self):
        """Explicitly start the inference worker process."""
        if hasattr(self, "inference_manager"):
            self.inference_manager.start()

    def cleanup(self):
        """Graceful shutdown of resources"""
        if hasattr(self, "inference_manager"):
            self.inference_manager.stop()

    def get_training_logs(self):
        """Get training logs from ML system"""
        return []

    def _reset_virtual_positions_for_real_trading(self):
        """Drop any paper-only positions before activating live trading."""
        if not self.positions:
            return

        summary = {
            "symbol_count": len(self.positions),
            "symbols": list(self.positions.keys()),
            "total_virtual_value": sum(
                _safe_float(pos.get("quantity"), 0.0)
                * _safe_float(pos.get("avg_price"), 0.0)
                for pos in self.positions.values()
            ),
        }

        self.positions.clear()
        self.auto_take_profit_state.clear()

        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event("REAL_TRADING_POSITION_RESET", summary)

        try:
            bot_logger.info(
                "Cleared %d paper positions before enabling real trading (virtual value %.2f)",
                summary["symbol_count"],
                summary["total_virtual_value"],
            )
        except Exception:
            pass

    def run_strategy_cycle(self, symbol: str):
        """
        Phase 7: Main Execution Loop for a Symbol.
        Orchestrates Strategies -> Governor -> Execution.
        """
        if not self.trading_enabled:
            debug_logger.info("trading_disabled", "ℹ️ Trading is DISABLED globally in config")
            return
            
        if not self.real_trader.is_ready():
            debug_logger.warning("trader_not_ready", "⚠️ Real Trader is NOT READY (check credentials/network)")
            return

        # 1. Get Market Data (e.g. last 100 candles)
        # For simplicity, fetching directly
        try:
            market_data = self.get_latest_candles(symbol, limit=200)
            if not market_data:
                debug_logger.warning(f"no_data_{symbol}", f"⚠️ Skipping {symbol}: No market data available")
                return
        except Exception as e:
            debug_logger.warning(f"data_error_{symbol}", f"⚠️ Skipping {symbol}: Market data error {e}")
            return

        # 2. Get Oracle Advice (Non-blocking)
        oracle_advice = self.model_oracle.get_advice(symbol, market_data)

        # 3. Get Strategy Signals
        signals = {}
        for name, strat in self.strategy_manager.strategies.items():
            if not strat.active:
                continue
            # Logic: strat.analyze_market(symbol, data) -> enhances with oracle inside if set
            raw_sig = strat.analyze_market(symbol, market_data)
            
            # Phase 7: Forcibly enhance with Oracle if method exists
            if hasattr(strat, "enhance_with_oracle"):
                 raw_sig = strat.enhance_with_oracle(symbol, market_data, raw_sig)
                 
            signals[name] = raw_sig

        # 4. Governor Decision
        decision = self.governor.decide(symbol, signals, oracle_advice)

        # 5. Execution
        if decision.action in ["BUY", "SELL"]:
            if decision.confidence >= self.governor.min_global_confidence:
                self.logger.info(f"GOVERNOR DECISION: {decision.action} {symbol} (Conf: {decision.confidence:.2f}) | Reason: {decision.reason}")
                
                # Execute Trade
                self.execute_governor_decision(decision)
            else:
                self.logger.info(f"GOVERNOR WATCHING: {decision.action} {symbol} (Conf: {decision.confidence:.2f}) | Reason: {decision.reason}")

    def get_latest_candles(self, symbol, limit=100):
        # Wrapper to fetch candles via existing helpers
        # self.latest_market_data might have it, or fetch fresh
        # Assuming existing 'get_real_market_data' service is available globally or via self
        from app.services import get_real_market_data
        return get_real_market_data(symbol, limit=limit)

    def execute_governor_decision(self, decision):
        # Send to RealBinanceTrader
        # Use existing 'process_signal' or 'place_real_order' logic
        # For now, simplistic implementation
        side = decision.action
        qty = 0.001 # Placeholder - need position sizing logic
        
        # self._submit_real_order(...)
        pass

    # ==================== REAL TRADING CONTROL ====================
    def enable_real_trading(
        self, api_key=None, api_secret=None, testnet=True, force=False, user_id=None
    ):
        """Configure the Binance trader and disable paper trading if successful.

        Safety: enabling real trading is gated by the FINAL_HAMMER environment flag
        (set FINAL_HAMMER=1/true/yes) or by explicitly passing force=True. This
        prevents accidental activation of live trading in deployments where the
        environment variable is not set.
        """
        testnet = _coerce_bool(testnet, default=True)

        # Final hammer safety guard: require explicit env flag or force parameter
        # NOTE: allow enabling for testnet without FINAL_HAMMER so users can
        # validate live-like behaviour on Binance testnet. Only block when
        # attempting to enable real trading against live environment.
        final_hammer = os.getenv("FINAL_HAMMER", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if not testnet and not final_hammer and not force:
            try:
                bot_logger.warning(
                    "Blocked enable_real_trading: FINAL_HAMMER not set and force not provided."
                )
            except Exception:
                print(
                    "Blocked enable_real_trading: FINAL_HAMMER not set and force not provided."
                )
            return False

        was_paper_mode = self.paper_trading
        
        # Set self.user_id if provided (for singleton traders)
        if user_id:
            self.user_id = user_id

        if not self.real_trader:
            self.real_trader = RealBinanceTrader(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet,
                account_type="spot",
                binance_client_cls=BinanceClient,
                api_exception_cls=BinanceAPIException,
                binance_log_manager=globals().get("binance_log_manager"),
                logger=bot_logger,
                coerce_bool=_coerce_bool,
                user_id=user_id or getattr(self, "user_id", None),
            )
        else:
            self.real_trader.set_testnet(testnet)
            self.real_trader.set_credentials(
                api_key=api_key,
                api_secret=api_secret,
                auto_connect=True,
                user_id=user_id or getattr(self, "user_id", None),
            )

        self.real_trading_enabled = self.real_trader.is_ready()
        self.paper_trading = not self.real_trading_enabled

        if self.real_trading_enabled and was_paper_mode:
            self._reset_virtual_positions_for_real_trading()

        status = self.get_real_trading_status()
        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event(
                "REAL_TRADING_TOGGLED",
                {
                    "enabled": self.real_trading_enabled,
                    "testnet": status.get("testnet"),
                    "reason": status.get("last_error")
                    if not self.real_trading_enabled
                    else "connected",
                },
            )

        if self.real_trading_enabled:
            # Reset baseline so the next portfolio snapshot seeds it from live equity
            self.real_equity_baseline = None

        return self.real_trading_enabled

    def disable_real_trading(self, reason="manual"):
        self.real_trading_enabled = False
        self.paper_trading = True
        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event(
                "REAL_TRADING_DISABLED", {"reason": reason}
            )
        self.real_equity_baseline = None
        return True

    def get_real_trading_status(self):
        base_status = {
            "enabled": self.real_trading_enabled,
            "paper_trading": self.paper_trading,
            "last_order": self.last_real_order,
        }
        if self.real_trader:
            base_status.update(self.real_trader.get_status())
        return base_status

    # ==================== FUTURES TRADING CONTROL ====================
    def enable_futures_trading(
        self, api_key=None, api_secret=None, testnet=True, force=False, user_id=None
    ):
        if not (BinanceFuturesClient or BinanceClient):
            print(
                "❌ Futures trading unavailable: python-binance client libraries not installed"
            )
            return False

        testnet = _coerce_bool(os.getenv("USE_TESTNET", "1"), default=True)

        # Legacy safety guard (FINAL_HAMMER) removed to allow UI-based activation
        # User authorization is handled by the API layer (login_required + user_id check)
        final_hammer = True 
        
        # if not final_hammer and not force:
        #    ... (removed blocking logic)
        # Set self.user_id if provided (for singleton traders)
        if user_id:
            self.user_id = user_id

        if not self.futures_trader:
            self.futures_trader = BinanceFuturesTrader(
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet,
                binance_um_futures_cls=BinanceFuturesClient,
                binance_rest_client_cls=BinanceClient,
                binance_log_manager=globals().get("binance_log_manager"),
                logger=bot_logger,
                coerce_bool=_coerce_bool,
                safe_float=_safe_float,
                user_id=user_id or getattr(self, "user_id", None),  # SECURITY: Pass user_id for isolation
            )
        else:
            self.futures_trader.set_testnet(testnet)
            self.futures_trader.set_credentials(
                api_key=api_key, 
                api_secret=api_secret, 
                auto_connect=True,
                user_id=user_id or getattr(self, "user_id", None)
            )

        self.futures_trading_enabled = self.futures_trader.is_ready()
        return self.futures_trading_enabled

    def disable_futures_trading(self, reason="manual"):
        if self.futures_trader:
            self.futures_trading_enabled = False
            if hasattr(self.trade_history, "log_journal_event"):
                self.trade_history.log_journal_event(
                    "FUTURES_TRADING_DISABLED", {"reason": reason}
                )
        return True

    def get_futures_trading_status(self):
        status = {
            "enabled": self.futures_trading_enabled,
            "last_order": getattr(self, "last_futures_order", None),
        }
        if self.futures_trader:
            status.update(self.futures_trader.get_status())
        return status

    def _submit_futures_order(
        self, symbol, side, quantity, leverage=None, reduce_only=False, reason=None, details=None
    ):
        # ...existing code...
        if not self.futures_trading_enabled or not self.futures_trader:
            return None

        qty = _safe_float(quantity, 0.0)
        if qty <= 0:
            return None

        leverage_to_use = leverage or TRADING_CONFIG.get("futures_manual_leverage", 3)

        # Futures safety gate (VPS-only): blocks unsafe entries without changing
        # strategy logic.
        safety_service = getattr(self, "futures_safety_service", None)
        if safety_service and hasattr(safety_service, "should_allow_order"):
            try:
                allowed, reason, details = safety_service.should_allow_order(
                    symbol=str(symbol).upper(),
                    side=str(side).upper(),
                    quantity=qty,
                    leverage=int(leverage_to_use),
                    reduce_only=bool(reduce_only),
                    trader=self,
                )
            except Exception as exc:
                allowed = False
                reason = "TRADE_BLOCKED: SAFETY_SERVICE_ERROR"
                details = {"symbol": str(symbol).upper(), "error": str(exc)}

            if not allowed:
                journal_payload = {
                    "symbol": str(symbol).upper(),
                    "side": str(side).upper(),
                    "quantity": qty,
                    "leverage": leverage_to_use,
                    "reduce_only": reduce_only,
                    "status": "BLOCKED",
                    "block_reason": reason,
                    "details": details or {},
                    "testnet": getattr(self.futures_trader, "testnet", None),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                try:
                    if hasattr(self.trade_history, "log_journal_event"):
                        self.trade_history.log_journal_event(
                            "FUTURES_TRADE_BLOCKED", journal_payload
                        )
                except Exception:
                    pass
                try:
                    bot_logger.warning(
                        f"{reason} | symbol={journal_payload['symbol']} | details={details}"
                    )
                except Exception:
                    pass
                self.last_futures_order = journal_payload
                return None

        self.futures_trader.ensure_leverage(symbol, leverage_to_use)

        # Submit to exchange with timeout + retry for timeout errors
        retries = 2
        timeout = 30
        response = None
        for attempt in range(retries + 1):
            try:
                # Run the exchange call in a short-lived thread and enforce a timeout
                with ThreadPoolExecutor(max_workers=1) as _ex:
                    future = _ex.submit(
                        self.futures_trader.place_market_order, symbol, side, qty, reduce_only
                    )
                    response = future.result(timeout=timeout)
                break
            except (Timeout, FutureTimeoutError):
                if attempt < retries:
                    time.sleep(1)
                else:
                    raise

        # After Binance confirms order acceptance, persist an explicit futures execution.
        if response and isinstance(response, dict):
            try:
                order_id = response.get("orderId")
                client_order_id = response.get("clientOrderId")

                order_details = None
                get_order_fn = getattr(self.futures_trader, "get_order", None)
                if callable(get_order_fn) and (order_id or client_order_id):
                    try:
                        order_details = get_order_fn(
                            symbol,
                            order_id=order_id,
                            client_order_id=client_order_id,
                        )
                    except Exception:
                        order_details = None

                position_snapshot = None
                if hasattr(self.futures_trader, "get_position"):
                    try:
                        position_snapshot = self.futures_trader.get_position(symbol)
                    except Exception:
                        position_snapshot = None

                merged = dict(response)
                if isinstance(order_details, dict):
                    merged.update(order_details)

                ts_ms = None
                for key in ("updateTime", "transactTime", "time"):
                    raw_ts = merged.get(key)
                    if raw_ts in (None, ""):
                        continue
                    try:
                        ts_ms = int(float(raw_ts))
                        break
                    except Exception:
                        continue

                timestamp_iso = None
                if ts_ms:
                    try:
                        timestamp_iso = datetime.utcfromtimestamp(ts_ms / 1000.0).isoformat() + "Z"
                    except Exception:
                        timestamp_iso = None

                execution = {
                    "market_type": "FUTURES",
                    "exchange": "BINANCE_FUTURES",
                    "execution_mode": "futures",
                    "symbol": merged.get("symbol"),
                    "side": merged.get("side"),
                    "quantity": merged.get("origQty") if merged.get("origQty") is not None else merged.get("executedQty"),
                    "price": merged.get("avgPrice") if merged.get("avgPrice") not in (None, "", 0, "0", "0.0") else merged.get("price"),
                    "timestamp": timestamp_iso,
                    "status": merged.get("status"),
                    "binance_order_id": order_id,
                    "client_order_id": client_order_id,
                    "binance_timestamp_ms": ts_ms,
                    "margin_type": position_snapshot.get("marginType") if isinstance(position_snapshot, dict) else None,
                    "leverage": (position_snapshot.get("leverage") if isinstance(position_snapshot, dict) else None) or merged.get("leverage"),
                    "position_side": merged.get("positionSide") or (position_snapshot.get("positionSide") if isinstance(position_snapshot, dict) else None),
                    "reduce_only": merged.get("reduceOnly"),
                    "close_position": merged.get("closePosition"),
                    "working_type": merged.get("workingType"),
                    "price_protect": merged.get("priceProtect"),
                    "reason": reason,
                    "details": details,
                }

                if hasattr(self.trade_history, "record_exchange_execution"):
                    self.trade_history.record_exchange_execution(execution)
            except Exception:
                pass
        safe_response = response
        if response is not None:
            try:
                safe_response = copy.deepcopy(response)
            except Exception:
                if isinstance(response, dict):
                    safe_response = dict(response)
                elif isinstance(response, list):
                    safe_response = list(response)
        journal_payload = {
            "symbol": symbol,
            "side": side,
            "quantity": qty,
            "leverage": leverage_to_use,
            "reduce_only": reduce_only,
            "status": "SUCCESS" if response else "FAILED",
            "testnet": self.futures_trader.testnet,
            "raw_response": safe_response,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event("FUTURES_ORDER", journal_payload)
        self.last_futures_order = journal_payload

        # Track successful entry for daily trade limits.
        if response and not reduce_only and safety_service and hasattr(
            safety_service, "record_successful_entry"
        ):
            try:
                safety_service.record_successful_entry(str(symbol).upper())
            except Exception:
                pass
        return response

    def _submit_real_order(
        self, symbol, side, quantity, price=None, order_type="MARKET", reason=None, details=None
    ):
        # ...existing code...

        try:
            qty = _safe_float(quantity, 0.0)
        except Exception:
            return None

        if qty <= 0:
            return None

        normalized_side = str(side).upper()
        resolved_price = self._resolve_market_price(symbol, price)
        min_notional = (
            self._get_symbol_min_notional(symbol) if normalized_side == "SELL" else None
        )

        if normalized_side == "SELL":
            qty = self._prepare_sell_quantity(symbol, qty)
            if qty <= 0:
                reason_details = {
                    "reason": "insufficient_quantity",
                    "message": "No sellable quantity available on exchange",
                    "resolved_price": resolved_price,
                    "attempted_quantity": _safe_float(quantity, 0.0),
                }
                return self._record_skipped_real_order(
                    symbol, normalized_side, quantity, resolved_price, reason_details
                )

            if min_notional and resolved_price:
                order_value = qty * resolved_price
                if order_value < min_notional:
                    reason_details = {
                        "reason": "min_notional",
                        "message": f"Order value {order_value:.2f} below Binance minNotional {min_notional:.2f}",
                        "min_notional": float(min_notional),
                        "resolved_price": resolved_price,
                        "attempted_quantity": qty,
                    }
                    return self._record_skipped_real_order(
                        symbol,
                        normalized_side,
                        quantity,
                        resolved_price,
                        reason_details,
                    )
        else:
            qty = round(qty, 6)

        if qty <= 0:
            return None

        # Submit to exchange with timeout + retry for timeout errors
        retries = 2
        timeout = 30
        response = None
        for attempt in range(retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as _ex:
                    future = _ex.submit(
                        self.real_trader.place_real_order, symbol, normalized_side, qty, price, order_type
                    )
                    response = future.result(timeout=timeout)
                break
            except (Timeout, FutureTimeoutError):
                if attempt < retries:
                    time.sleep(1)
                else:
                    raise

        # After Binance confirms order acceptance, persist an explicit spot execution.
        if response and isinstance(response, dict):
            try:
                order_id = response.get("orderId")
                client_order_id = response.get("clientOrderId")

                order_details = None
                get_order_fn = getattr(self.real_trader, "get_order", None)
                if callable(get_order_fn) and (order_id or client_order_id):
                    try:
                        order_details = get_order_fn(
                            symbol,
                            order_id=order_id,
                            client_order_id=client_order_id,
                        )
                    except Exception:
                        order_details = None

                merged = dict(response)
                if isinstance(order_details, dict):
                    merged.update(order_details)

                ts_ms = None
                for key in ("transactTime", "updateTime", "time"):
                    raw_ts = merged.get(key)
                    if raw_ts in (None, ""):
                        continue
                    try:
                        ts_ms = int(float(raw_ts))
                        break
                    except Exception:
                        continue

                timestamp_iso = None
                if ts_ms:
                    try:
                        timestamp_iso = datetime.utcfromtimestamp(ts_ms / 1000.0).isoformat() + "Z"
                    except Exception:
                        timestamp_iso = None

                execution = {
                    "market_type": "SPOT",
                    "exchange": "BINANCE_SPOT",
                    "execution_mode": "real",
                    "symbol": merged.get("symbol"),
                    "side": merged.get("side"),
                    "quantity": merged.get("origQty") if merged.get("origQty") is not None else merged.get("executedQty"),
                    "price": merged.get("price"),
                    "timestamp": timestamp_iso,
                    "status": merged.get("status"),
                    "binance_order_id": order_id,
                    "client_order_id": client_order_id,
                    "binance_timestamp_ms": ts_ms,
                    # Futures-only fields must never be inferred for spot.
                    "margin_type": None,
                    "leverage": None,
                    "position_side": None,
                    "reduce_only": False,
                    "close_position": False,
                    "working_type": None,
                    "working_type": None,
                    "price_protect": None,
                    "reason": reason,
                    "details": details,
                }

                if hasattr(self.trade_history, "record_exchange_execution"):
                    self.trade_history.record_exchange_execution(execution)
            except Exception:
                pass
        safe_response = response
        if response is not None:
            try:
                safe_response = copy.deepcopy(response)
            except Exception:
                if isinstance(response, dict):
                    safe_response = dict(response)
                elif isinstance(response, list):
                    safe_response = list(response)
        status = "SUCCESS" if response else "FAILED"
        journal_payload = {
            "symbol": symbol,
            "side": normalized_side,
            "quantity": round(float(qty), 6) if isinstance(qty, (int, float)) else qty,
            "price": price,
            "resolved_price": resolved_price,
            "order_type": order_type,
            "status": status,
            "testnet": self.real_trader.testnet,
            "api_error": self.real_trader.last_error if not response else None,
        }
        # If we have a response, extract fills/commission metrics for the journal
        if response and isinstance(response, dict):
            try:
                executed_qty = self._extract_filled_quantity(response, qty)
                quote_received = self._calculate_quote_spent(
                    response, executed_qty, price or 0
                )
                commissions = self._extract_commissions(response)
                journal_payload.update(
                    {
                        "executed_qty": executed_qty,
                        "quote_received": quote_received,
                        "commissions": commissions,
                    }
                )
            except Exception:
                pass
        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event("REAL_ORDER", journal_payload)

        self.last_real_order = {
            "timestamp": datetime.now().isoformat(),
            **journal_payload,
            "raw_response": safe_response,
        }
        return response

    def _record_skipped_real_order(
        self, symbol, side, requested_quantity, price_reference, reason_details
    ):
        payload = {
            "status": "SKIPPED",
            "symbol": symbol,
            "side": side,
            "requested_quantity": _safe_float(requested_quantity, 0.0),
            "price_reference": _safe_float(price_reference, 0.0)
            if price_reference is not None
            else None,
            "reason": (reason_details or {}).get("reason")
            if isinstance(reason_details, dict)
            else str(reason_details),
            "details": reason_details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        message = None
        if isinstance(reason_details, dict):
            message = reason_details.get("message")
            if message:
                payload["message"] = message

        if hasattr(self.trade_history, "log_journal_event"):
            self.trade_history.log_journal_event("REAL_ORDER_SKIPPED", payload)

        try:
            bot_logger.warning(
                "Skipping real %s order for %s reason=%s",
                side,
                symbol,
                payload["reason"],
            )
        except Exception:
            pass

        self.last_real_order = payload
        return payload

    def _get_symbol_min_notional(self, symbol):
        if not symbol:
            return None

        symbol_key = str(symbol).upper()
        cached = self.symbol_min_notional_cache.get(symbol_key)
        if cached is not None:
            return cached

        overrides = TRADING_CONFIG.get("min_notional_overrides") or {}
        if symbol_key in overrides:
            try:
                value = float(overrides[symbol_key])
                self.symbol_min_notional_cache[symbol_key] = value
                return value
            except (TypeError, ValueError):
                pass

        if self.real_trader and self.real_trader.is_ready():
            min_notional = self.real_trader.get_min_notional(symbol_key)
            if min_notional:
                try:
                    value = float(min_notional)
                    self.symbol_min_notional_cache[symbol_key] = value
                    return value
                except (TypeError, ValueError):
                    pass

        default_min = TRADING_CONFIG.get("default_min_notional")
        if default_min:
            try:
                value = float(default_min)
                self.symbol_min_notional_cache[symbol_key] = value
                return value
            except (TypeError, ValueError):
                pass

        return None

    def _get_real_account_snapshot(self, current_prices):
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return None

        try:
            account = (
                self.real_trader.account_status
                or self.real_trader.refresh_account_status()
            )
            if not account:
                return None

            balances = account.get("balances", []) or []
            tracked_assets = {
                sym[:-4]: sym
                for sym in get_active_trading_universe()
                if sym.endswith("USDT")
            }
            stable_suffixes = ("USDT", "BUSD", "USDC", "FDUSD", "DAI", "TUSD")

            cash_total = 0.0
            cash_breakdown = []
            holdings = []
            asset_value_total = 0.0

            for bal in balances:
                asset = str(bal.get("asset") or "").upper()
                free_qty = _safe_float(bal.get("free"), 0.0)
                locked_qty = _safe_float(bal.get("locked"), 0.0)
                total_qty = free_qty + locked_qty
                if total_qty <= 0:
                    continue

                if asset.endswith(stable_suffixes):
                    cash_total += total_qty
                    cash_breakdown.append(
                        {
                            "asset": asset,
                            "free": free_qty,
                            "locked": locked_qty,
                            "total": total_qty,
                        }
                    )
                    continue

                # Skip leveraged tokens and synthetic prefixes that don't map to spot symbols
                normalized_asset = asset
                if normalized_asset.startswith("LD"):
                    normalized_asset = normalized_asset[2:]

                symbol = (
                    tracked_assets.get(normalized_asset) or f"{normalized_asset}USDT"
                )
                price = current_prices.get(symbol)
                if not price:
                    continue

                current_value = total_qty * price
                asset_value_total += current_value
                holdings.append(
                    {
                        "asset": asset,
                        "symbol": symbol,
                        "quantity": total_qty,
                        "free": free_qty,
                        "locked": locked_qty,
                        "price": price,
                        "current_value": current_value,
                    }
                )

            total_equity = cash_total + asset_value_total
            return {
                "cash": cash_total,
                "cash_breakdown": cash_breakdown,
                "asset_value": asset_value_total,
                "holdings": holdings,
                "total_equity": total_equity,
                "updated_at": account.get("update_time"),
                "can_trade": account.get("can_trade"),
            }
        except Exception as exc:
            bot_logger.warning("Failed to build real account snapshot error=%s", exc)
            return None

    def _resolve_market_price(self, symbol, reference_price=None):
        try:
            if reference_price is not None:
                candidate = float(reference_price)
                if candidate > 0:
                    return candidate
        except Exception:
            pass

        latest = (
            self.latest_market_data.get(symbol)
            if isinstance(self.latest_market_data, dict)
            else None
        )
        if isinstance(latest, dict):
            for key in ("price", "last_price", "close", "current_price"):
                value = latest.get(key)
                if value is None:
                    continue
                try:
                    price_val = float(value)
                    if price_val > 0:
                        return price_val
                except Exception:
                    continue

        if self.real_trader and self.real_trader.is_ready():
            resolved = self.real_trader._resolve_price(symbol, reference_price)
            try:
                if resolved is not None and float(resolved) > 0:
                    return float(resolved)
            except Exception:
                pass

        return None

    def _determine_quote_asset(self, symbol):
        if not symbol:
            return "USDT"
        symbol_key = str(symbol).upper()
        known_quotes = sorted(
            ["USDT", "BUSD", "USDC", "FDUSD", "TUSD", "DAI"], key=len, reverse=True
        )
        for quote in known_quotes:
            if symbol_key.endswith(quote):
                return quote
        return "USDT"

    def _get_real_free_balance(self, asset, *, refresh=False):
        if not asset or not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return None

        account = None
        if refresh or not getattr(self.real_trader, "account_status", None):
            account = self.real_trader.refresh_account_status()
        else:
            account = self.real_trader.account_status

        if not account:
            return None

        target = str(asset).upper()
        total_free = 0.0
        for bal in account.get("balances", []) or []:
            asset_code = str(bal.get("asset") or "").upper()
            normalized = asset_code[2:] if asset_code.startswith("LD") else asset_code
            if normalized == target:
                total_free += _safe_float(bal.get("free"), 0.0)
        return total_free

    def _determine_base_asset(self, symbol):
        symbol_key = str(symbol or "").upper()
        if not symbol_key:
            return ""
        quote_asset = self._determine_quote_asset(symbol_key)
        if quote_asset and symbol_key.endswith(quote_asset):
            return symbol_key[: -len(quote_asset)]
        return symbol_key

    def _calculate_net_filled_quantity(
        self, symbol, filled_quantity, order_response=None
    ):
        quantity = _safe_float(filled_quantity, 0.0)
        if quantity <= 0 or not order_response or not isinstance(order_response, dict):
            return max(quantity, 0.0)

        fills = order_response.get("fills") or []
        if not fills:
            return max(quantity, 0.0)

        base_asset = self._determine_base_asset(symbol)
        if not base_asset:
            return max(quantity, 0.0)

        base_commission = 0.0
        for fill in fills:
            commission_asset = str(fill.get("commissionAsset") or "").upper()
            if commission_asset == base_asset:
                base_commission += _safe_float(fill.get("commission"), 0.0)

        net_quantity = quantity - base_commission
        return max(net_quantity, 0.0)

    def _calculate_quote_spent(self, order_response, filled_quantity, fallback_price):
        fallback_value = _safe_float(filled_quantity, 0.0) * _safe_float(
            fallback_price, 0.0
        )
        if not order_response or not isinstance(order_response, dict):
            return fallback_value

        cumulative = order_response.get("cummulativeQuoteQty")
        if cumulative is not None:
            value = _safe_float(cumulative, fallback_value)
            if value > 0:
                return value

        fills = order_response.get("fills") or []
        if fills:
            total = 0.0
            for fill in fills:
                price = _safe_float(fill.get("price"), fallback_price)
                qty = _safe_float(fill.get("qty"), 0.0)
                total += price * qty
            if total > 0:
                return total

        return fallback_value

    def _extract_commissions(self, order_response):
        """Return a dict of commission amounts keyed by asset from an order response."""
        result = {}
        if not order_response or not isinstance(order_response, dict):
            return result
        fills = order_response.get("fills") or []
        for fill in fills:
            try:
                comm = _safe_float(fill.get("commission"), 0.0)
                asset = str(fill.get("commissionAsset") or "").upper()
                if not asset:
                    continue
                result[asset] = result.get(asset, 0.0) + comm
            except Exception:
                continue
        return result

    def _prepare_sell_quantity(self, symbol, desired_quantity):
        quantity = _safe_float(desired_quantity, 0.0)
        if quantity <= 0:
            return 0.0

        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return quantity

        base_asset = self._determine_base_asset(symbol)
        if not base_asset:
            return quantity

        available = self._get_real_free_balance(base_asset, refresh=True)
        if available is not None and available > 0:
            quantity = min(quantity, _safe_float(available, quantity))

        return max(quantity, 0.0)

    def _has_sufficient_real_balance(self, symbol, required_quote_value):
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return True, {"reason": "real_trading_disabled"}

        quote_asset = self._determine_quote_asset(symbol)
        available = self._get_real_free_balance(quote_asset, refresh=True)
        if available is None:
            return False, {
                "reason": "balance_unavailable",
                "message": f"Unable to determine available {quote_asset} balance",
                "quote_asset": quote_asset,
            }

        buffer = TRADING_CONFIG.get("balance_cash_buffer") or 1.0
        try:
            required_value = float(required_quote_value) * float(buffer)
        except Exception:
            required_value = float(required_quote_value)

        if available < required_value:
            return False, {
                "reason": "insufficient_balance",
                "message": f"Insufficient {quote_asset} balance ({available:.2f} < {required_value:.2f})",
                "quote_asset": quote_asset,
                "available": available,
                "required": required_value,
                "buffer": buffer,
            }

        return True, {
            "reason": "sufficient_balance",
            "quote_asset": quote_asset,
            "available": available,
            "required": required_value,
            "buffer": buffer,
        }

    def _extract_filled_quantity(self, response, fallback_quantity):
        try:
            if isinstance(response, dict):
                executed = response.get("executedQty")
                if executed is not None:
                    executed_qty = float(executed)
                    if executed_qty > 0:
                        return executed_qty
                fills = response.get("fills")
                if isinstance(fills, list) and fills:
                    total = 0.0
                    for fill in fills:
                        try:
                            total += float(fill.get("qty", 0))
                        except Exception:
                            continue
                    if total > 0:
                        return total
        except Exception:
            pass
        try:
            return float(fallback_quantity)
        except Exception:
            return fallback_quantity

    def _handle_auto_take_profit(
        self, symbol, entry_price, quantity, order_response=None
    ):
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return

        config = TRADING_CONFIG
        percent = config.get("auto_take_profit_percent", 0.0)
        if not percent or percent <= 0:
            return

        # Cancel any existing take-profit for this symbol to prevent duplicates
        if symbol in self.auto_take_profit_state:
            self._cancel_auto_take_profit(symbol)

        adjusted_quantity = quantity
        if (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            adjusted_quantity = self._prepare_sell_quantity(symbol, quantity)

        normalized_qty, _ = self.real_trader._normalize_order_quantity(
            symbol, adjusted_quantity
        )
        if not normalized_qty or normalized_qty <= 0:
            return

        desired_price = entry_price * (1 + percent)
        order_book = self.real_trader.get_order_book(symbol, limit=5)
        spread_margin = config.get("auto_take_profit_spread_margin", 0.0) or 0.0
        if order_book and isinstance(order_book, dict):
            asks = order_book.get("asks") or []
            if asks:
                try:
                    best_ask = float(asks[0][0])
                    desired_price = max(desired_price, best_ask * (1 + spread_margin))
                except Exception:
                    pass

        tif = config.get("auto_take_profit_time_in_force", "GTC")
        response = self.real_trader.place_limit_order(
            symbol, "SELL", normalized_qty, price=desired_price, time_in_force=tif
        )

        if not response:
            log_component_event(
                "AUTO_TAKE_PROFIT",
                "Failed to place take-profit order",
                level=logging.WARNING,
                details={
                    "symbol": symbol,
                    "target_price": desired_price,
                    "quantity": normalized_qty,
                },
            )
            return

        self.auto_take_profit_state[symbol] = {
            "order_id": response.get("orderId") if isinstance(response, dict) else None,
            "client_order_id": response.get("clientOrderId")
            if isinstance(response, dict)
            else None,
            "target_price": float(response.get("price", desired_price))
            if isinstance(response, dict)
            else desired_price,
            "entry_price": entry_price,
            "quantity": normalized_qty,
            "created_at": datetime.utcnow().isoformat(),
            "last_checked": time.time(),
            "percent": percent,
        }

        log_component_event(
            "AUTO_TAKE_PROFIT",
            "Take-profit order placed",
            level=logging.INFO,
            details={
                "symbol": symbol,
                "entry_price": entry_price,
                "target_price": self.auto_take_profit_state[symbol]["target_price"],
                "quantity": normalized_qty,
                "order_id": self.auto_take_profit_state[symbol]["order_id"],
            },
        )

    def _cancel_auto_take_profit(self, symbol):
        state = self.auto_take_profit_state.pop(symbol, None)
        if not state:
            return
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return
        self.real_trader.cancel_order(
            symbol,
            order_id=state.get("order_id"),
            client_order_id=state.get("client_order_id"),
        )

    def update_auto_take_profit_orders(self, market_data=None):
        if not self.auto_take_profit_state:
            return
        if not (
            self.real_trading_enabled
            and self.real_trader
            and self.real_trader.is_ready()
        ):
            return

        config = TRADING_CONFIG
        interval = config.get("auto_take_profit_adjust_interval", 30)
        reprice_threshold = config.get("auto_take_profit_reprice_threshold", 0.003)
        spread_margin = config.get("auto_take_profit_spread_margin", 0.0) or 0.0

        for symbol in list(self.auto_take_profit_state.keys()):
            state = self.auto_take_profit_state.get(symbol)
            if not state:
                continue

            last_checked = state.get("last_checked")
            if last_checked and (time.time() - last_checked) < interval:
                continue

            state["last_checked"] = time.time()

            order_info = self.real_trader.get_order(
                symbol,
                order_id=state.get("order_id"),
                client_order_id=state.get("client_order_id"),
            )

            if not order_info:
                self.auto_take_profit_state.pop(symbol, None)
                continue

            status = str(order_info.get("status", "")).upper()
            if status in {"FILLED", "CANCELED", "REJECTED", "EXPIRED"}:
                self.auto_take_profit_state.pop(symbol, None)
                continue

            try:
                orig_qty = float(order_info.get("origQty", state.get("quantity", 0)))
                executed_qty = float(order_info.get("executedQty", 0))
            except Exception:
                orig_qty = state.get("quantity", 0)
                executed_qty = 0

            remaining_qty = max(0.0, orig_qty - executed_qty)
            if remaining_qty <= 0:
                self.auto_take_profit_state.pop(symbol, None)
                continue

            current_order_price = None
            try:
                current_order_price = float(order_info.get("price"))
            except Exception:
                current_order_price = state.get("target_price")

            market_price = None
            if (
                market_data
                and symbol in market_data
                and isinstance(market_data[symbol], dict)
            ):
                market_price = market_data[symbol].get("price")

            entry_price = state.get("entry_price") or market_price
            if not entry_price:
                continue

            desired_price = entry_price * (
                1 + state.get("percent", config.get("auto_take_profit_percent", 0.05))
            )
            order_book = self.real_trader.get_order_book(symbol, limit=5)
            if order_book and isinstance(order_book, dict):
                asks = order_book.get("asks") or []
                if asks:
                    try:
                        best_ask = float(asks[0][0])
                        desired_price = max(
                            desired_price, best_ask * (1 + spread_margin)
                        )
                    except Exception:
                        pass

            desired_price = self.real_trader.normalize_price(symbol, desired_price)
            if not current_order_price:
                current_order_price = desired_price

            price_diff = abs(desired_price - current_order_price)  # type: ignore
            price_diff_pct = (
                price_diff / current_order_price if current_order_price else 0
            )

            if price_diff_pct < reprice_threshold:
                continue

            cancel_result = self.real_trader.cancel_order(
                symbol,
                order_id=state.get("order_id"),
                client_order_id=state.get("client_order_id"),
            )

            if cancel_result is None:
                continue

            new_order = self.real_trader.place_limit_order(
                symbol,
                "SELL",
                remaining_qty,
                price=desired_price,
                time_in_force=config.get("auto_take_profit_time_in_force", "GTC"),
            )

            if new_order:
                state["order_id"] = (
                    new_order.get("orderId") if isinstance(new_order, dict) else None
                )
                state["client_order_id"] = (
                    new_order.get("clientOrderId")
                    if isinstance(new_order, dict)
                    else None
                )
                state["target_price"] = (
                    float(new_order.get("price", desired_price))
                    if isinstance(new_order, dict)
                    else desired_price
                )
                state["quantity"] = remaining_qty
                state["entry_price"] = entry_price
                state["last_checked"] = time.time()
                log_component_event(
                    "AUTO_TAKE_PROFIT",
                    "Take-profit order repriced",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "new_price": state["target_price"],
                        "remaining_qty": remaining_qty,
                        "previous_price": current_order_price,
                    },
                )
            else:
                self.auto_take_profit_state.pop(symbol, None)

    def calculate_ultimate_position_size(
        self,
        symbol,
        current_price,
        signal_confidence,
        volatility=0.02,
        ensemble_signal=None,
        portfolio_health=1.0,
    ):
        """Ultimate position sizing with all advanced factors"""
        cfg = self._get_trading_config()
        base_risk = (
            cfg["risk_per_trade"] * self.risk_manager.get_risk_multiplier()
        )

        # Confidence multiplier
        confidence_multiplier = min(signal_confidence * 1.5, 1.2)

        # Ensemble signal boost
        ensemble_boost = 1.0
        if ensemble_signal:
            if ensemble_signal.get("signal") in ["STRONG_BUY", "STRONG_SELL"]:
                ensemble_boost = 1.3
            elif ensemble_signal.get("signal") in ["BUY", "SELL"]:
                ensemble_boost = 1.15

        # Volatility adjustment
        vol_adjustment = 1.0
        if volatility > 0.06:
            vol_adjustment = 0.6
        elif volatility > 0.03:
            vol_adjustment = 0.8
        elif volatility < 0.01:
            vol_adjustment = 1.2

        # Market regime adjustment
        regime_adjustment = 1.0
        if self.ensemble_system.market_regime in ["STRONG_BULL", "STRONG_BEAR"]:
            regime_adjustment = 1.2
        elif self.ensemble_system.market_regime in [
            "HIGH_VOL_SIDEWAYS",
            "OVERBOUGHT",
            "OVERSOLD",
        ]:
            regime_adjustment = 0.7

        # Portfolio health adjustment
        health_factor = max(0.5, min(1.5, portfolio_health))

        # Market stress adjustment
        stress_factor = 1.0 - (
            self.risk_manager.market_stress_indicator * 0.5
        )  # Reduce size during stress

        # Calculate final position size
        position_value = (
            self.balance
            * base_risk
            * confidence_multiplier
            * ensemble_boost
            * vol_adjustment
            * regime_adjustment
            * health_factor
            * stress_factor
        )

        max_position_value = self.balance * cfg["max_position_size"]
        position_value = min(position_value, max_position_value)

        min_notional = self._get_symbol_min_notional(symbol)
        buffer = cfg.get("min_notional_buffer", 1.0)

        if min_notional and current_price:
            try:
                min_value = float(min_notional) * float(buffer if buffer else 1.0)
                if position_value < min_value:
                    log_component_event(
                        "POSITION_SIZING",
                        "Position value raised to min notional",
                        level=logging.INFO,
                        details={
                            "symbol": symbol,
                            "original_value": round(float(position_value), 4)
                            if isinstance(position_value, (int, float))
                            else position_value,
                            "min_notional": min_notional,
                            "buffer": buffer,
                            "target_value": min_value,
                        },
                    )
                    position_value = min(min_value, max_position_value)
            except Exception as exc:
                bot_logger.warning(
                    "Failed to enforce min notional for %s error=%s", symbol, exc
                )

        quantity = position_value / current_price if current_price else 0

        # Log ultimate position sizing
        print(f"🎯 {self.profile_prefix} Position Sizing for {symbol}:")
        print(
            f"   Base: ${base_risk*self.balance:.2f}, Confidence: {confidence_multiplier:.2f}"
        )
        print(f"   Ensemble: {ensemble_boost:.2f}, Vol: {vol_adjustment:.2f}")
        print(
            f"   Regime: {regime_adjustment:.2f}, Health: {health_factor:.2f}, Stress: {stress_factor:.2f}"
        )
        print(f"   Final: ${position_value:.2f} ({quantity:.4f} units)")

        return quantity, position_value

    def should_execute_ultimate_trade(
        self,
        symbol,
        ml_predictions,
        technical_signals,
        current_positions,
        market_regime,
        ensemble_signal,
        market_stress,
        market_data=None,
        historical_prices=None,
    ):
        """Ultimate trading decision with all advanced factors"""
        cfg = self._get_trading_config()
        log_component_debug(
            "TRADE_DECISION",
            "Evaluating trade decision",
            {
                "symbol": symbol,
                "open_positions": len(current_positions)
                if isinstance(current_positions, dict)
                else len(current_positions or []),
                "ml_signal_count": len(ml_predictions)
                if isinstance(ml_predictions, dict)
                else 0,
                "technical_signal_count": len(technical_signals)
                if technical_signals
                else 0,
                "market_regime": market_regime,
                "market_stress": round(float(market_stress), 4)
                if isinstance(market_stress, (int, float))
                else market_stress,
            },
        )
        if len(current_positions) >= cfg["max_positions"]:
            log_component_event(
                "TRADE_DECISION",
                "Decision blocked: max positions reached",
                level=logging.INFO,
                details={"symbol": symbol, "open_positions": len(current_positions)},
            )
            return False, "Max positions reached"

        if not ml_predictions and not technical_signals:
            log_component_event(
                "TRADE_DECISION",
                "Decision blocked: no predictions available",
                level=logging.INFO,
                details={"symbol": symbol},
            )
            return False, "No predictions available"

        # Generate CRT signals for decision making
        crt_signal = None
        if market_data and historical_prices and hasattr(self, "crt_generator"):
            try:
                crt_signal = self.crt_generator.generate_crt_signals(
                    symbol, market_data, historical_prices
                )
                log_component_debug(
                    "TRADE_DECISION",
                    "CRT signals generated",
                    {
                        "symbol": symbol,
                        "crt_signal": crt_signal.get("signal") if crt_signal else None,
                        "crt_confidence": crt_signal.get("confidence")
                        if crt_signal
                        else None,
                    },
                )
            except Exception as e:
                log_component_event(
                    "TRADE_DECISION",
                    f"CRT signal generation error: {e}",
                    level=logging.WARNING,
                    details={"symbol": symbol},
                )

        # Combine all signals
        all_signals = []

        # Add ML predictions
        if ml_predictions:
            for model_name, prediction in ml_predictions.items():
                if not isinstance(prediction, dict):
                    continue

                signal_value = prediction.get("signal")
                if not signal_value:
                    continue

                confidence_value = prediction.get("confidence")
                if confidence_value is None:
                    confidence_value = prediction.get("probability")
                if confidence_value is None:
                    confidence_value = 0.5

                signal_type = "ML"
                if isinstance(model_name, str):
                    lower_name = model_name.lower()
                    if "ensemble" in lower_name:
                        signal_type = "ENSEMBLE"
                    elif "futures" in lower_name:
                        signal_type = "ENSEMBLE"

                all_signals.append(
                    {
                        "signal": signal_value,
                        "confidence": float(confidence_value),
                        "type": signal_type,
                        "model": model_name,
                        "indicators": prediction.get("indicators_total", 0),
                        "data_source": prediction.get("data_source", "UNKNOWN"),
                    }
                )

        # Add technical signals
        for tech_signal in technical_signals:
            all_signals.append(
                {
                    "signal": tech_signal["signal"],
                    "confidence": tech_signal["confidence"],
                    "type": "TECHNICAL",
                    "strategy": tech_signal["strategy"],
                }
            )

        # Add ensemble signal
        ensemble_confidence = None
        if ensemble_signal:
            if isinstance(ensemble_signal, dict):
                ensemble_confidence = self._stabilize_ensemble_confidence(
                    ensemble_signal.get("confidence", 0.5)
                )
            all_signals.append(
                {
                    "signal": ensemble_signal["signal"],
                    "confidence": ensemble_confidence
                    if isinstance(ensemble_confidence, (int, float))
                    else ensemble_signal.get("confidence", 0.5),
                    "type": "ENSEMBLE",
                    "buy_ratio": ensemble_signal.get("buy_ratio", 0.5),
                    "consensus": ensemble_signal.get("weighted_consensus", 0),
                }
            )

        # Add CRT signal
        if crt_signal:
            all_signals.append(
                {
                    "signal": crt_signal.get("signal", "HOLD"),
                    "confidence": crt_signal.get("confidence", 0.5),
                    "type": "CRT",
                    "composite_score": crt_signal.get("composite_score", 0),
                    "components": crt_signal.get("components", {}),
                }
            )

        if not all_signals:
            log_component_event(
                "TRADE_DECISION",
                "Decision blocked: aggregated signal list empty",
                level=logging.INFO,
                details={"symbol": symbol},
            )
            return False, "No signals available"
        else:
            log_component_debug(
                "TRADE_DECISION",
                "Aggregated signals prepared",
                {"symbol": symbol, "total_signals": len(all_signals)},
            )

        # Apply signal prioritization and conflict resolution
        prioritized_signals = self._prioritize_signals(
            all_signals, market_regime, market_stress
        )

        # Calculate weighted signals with ultimate factors
        buy_strength = 0
        sell_strength = 0
        total_weight = 0

        for signal in prioritized_signals:
            # Ultimate weight assignment
            if signal["type"] == "ENSEMBLE":
                weight = 2.5
            elif signal["type"] == "CRT":
                weight = 2.0  # High weight for comprehensive CRT signals
            elif signal["type"] == "QFM":
                weight = 1.8  # High weight for Quantum Fusion Momentum signals
            elif signal["type"] == "ML" and signal.get("data_source") == "BINANCE_REAL":
                if signal.get("indicators", 0) >= 20:
                    weight = 1.8
                else:
                    weight = 1.3
            elif signal["type"] == "ML":
                weight = 1.2
            else:
                weight = 1.0

            # Strong signal bonus
            if signal["signal"] in ["STRONG_BUY", "STRONG_SELL"]:
                weight *= 1.3

            # Market stress penalty
            if market_stress > 0.6:
                weight *= 0.7

            if signal["signal"] in ["BUY", "STRONG_BUY"]:
                buy_strength += signal["confidence"] * weight
            elif signal["signal"] in ["SELL", "STRONG_SELL"]:
                sell_strength += signal["confidence"] * weight

            total_weight += weight

        buy_power = buy_strength / total_weight if total_weight > 0 else 0
        sell_power = sell_strength / total_weight if total_weight > 0 else 0

        # Dynamic threshold with all factors
        dynamic_threshold = cfg["confidence_threshold"]

        # Market stress adjustment
        if market_stress > 0.7:
            dynamic_threshold += 0.08
        elif market_stress > 0.4:
            dynamic_threshold += 0.04

        # Ensemble-based adjustments
        if ensemble_signal:
            if ensemble_confidence is None and isinstance(ensemble_signal, dict):
                ensemble_confidence = self._stabilize_ensemble_confidence(
                    ensemble_signal.get("confidence", 0.5)
                )
            if ensemble_confidence is None:
                ensemble_confidence = ensemble_signal.get("confidence", 0.5)
            if ensemble_confidence > 0.7:
                dynamic_threshold -= 0.03
            elif ensemble_confidence < 0.4:
                dynamic_threshold += 0.05

        # Market regime adjustments
        if market_regime in ["STRONG_BULL", "STRONG_BEAR"]:
            dynamic_threshold -= 0.015
        elif market_regime in ["HIGH_VOL_SIDEWAYS"]:
            dynamic_threshold += 0.025

        # Clamp dynamic threshold to configured bounds
        # FORCE_TRADING_UPDATE: Lowered floor to 0.15 to allow trading with 0.20-0.25 accuracy
        threshold_floor = cfg.get("dynamic_threshold_floor", 0.15)
        threshold_ceiling = cfg.get("dynamic_threshold_ceiling", 0.95)
        dynamic_threshold = max(
            threshold_floor, min(dynamic_threshold, threshold_ceiling)
        )

        strength_diff = abs(buy_power - sell_power)
        min_diff_required = cfg.get("min_confidence_diff", 0.05)

        log_component_debug(
            "TRADE_DECISION",
            "Threshold evaluation",
            {
                "symbol": symbol,
                "buy_power": round(float(buy_power), 3),
                "sell_power": round(float(sell_power), 3),
                "strength_diff": round(float(strength_diff), 3),
                "dynamic_threshold": round(float(dynamic_threshold), 3),
                "min_diff_required": round(float(min_diff_required), 3),
                "market_stress": round(float(market_stress), 3),
                "regime": market_regime,
            },
        )

        # Enhanced ensemble consensus requirement
        if ensemble_signal and cfg["use_ensemble"]:
            ensemble_agreement = (
                ensemble_signal.get("buy_ratio", 0.5)
                if buy_power > sell_power
                else (1 - ensemble_signal.get("buy_ratio", 0.5))
            )
            min_agreement = cfg.get("ensemble_min_agreement", 0.6)

            if ensemble_agreement < min_agreement:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision blocked: ensemble agreement too low",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "ensemble_agreement": round(float(ensemble_agreement), 3),
                        "min_required": round(float(min_agreement), 3),
                    },
                )
                return (
                    False,
                    f"Ensemble agreement too low: {ensemble_agreement:.2f} < {min_agreement:.2f}",
                )

        # Market stress override
        if market_stress > 0.8 and strength_diff < 0.2:
            log_component_event(
                "TRADE_DECISION",
                "Decision blocked: market stress override triggered",
                level=logging.WARNING,
                details={
                    "symbol": symbol,
                    "market_stress": round(float(market_stress), 3),
                    "strength_diff": round(float(strength_diff), 3),
                },
            )
            return False, f"Market stress too high: {market_stress:.2f}"

        # Final ultimate decision
        if (
            buy_power > sell_power
            and buy_power >= dynamic_threshold
            and strength_diff >= min_diff_required
        ):
            strong_buy_count = sum(
                1 for s in all_signals if s["signal"] == "STRONG_BUY"
            )
            if strong_buy_count >= 2:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision: STRONG_BUY approved",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "buy_power": round(float(buy_power), 3),
                        "sell_power": round(float(sell_power), 3),
                        "strength_diff": round(float(strength_diff), 3),
                        "market_stress": round(float(market_stress), 3),
                    },
                )
                return True, "STRONG_BUY"
            else:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision: BUY approved",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "buy_power": round(float(buy_power), 3),
                        "sell_power": round(float(sell_power), 3),
                        "strength_diff": round(float(strength_diff), 3),
                        "market_stress": round(float(market_stress), 3),
                    },
                )
                return True, "BUY"

        elif (
            sell_power > buy_power
            and symbol in current_positions
            and sell_power >= dynamic_threshold
            and strength_diff >= min_diff_required
        ):
            strong_sell_count = sum(
                1 for s in all_signals if s["signal"] == "STRONG_SELL"
            )
            if strong_sell_count >= 2:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision: STRONG_SELL approved",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "buy_power": round(float(buy_power), 3),
                        "sell_power": round(float(sell_power), 3),
                        "strength_diff": round(float(strength_diff), 3),
                        "market_stress": round(float(market_stress), 3),
                    },
                )
                return True, "STRONG_SELL"
            else:
                log_component_event(
                    "TRADE_DECISION",
                    "Decision: SELL approved",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "buy_power": round(float(buy_power), 3),
                        "sell_power": round(float(sell_power), 3),
                        "strength_diff": round(float(strength_diff), 3),
                        "market_stress": round(float(market_stress), 3),
                    },
                )
                return True, "SELL"

        log_component_debug(
            "TRADE_DECISION",
            "Decision: No trade (insufficient strength)",
            {
                "symbol": symbol,
                "buy_power": round(float(buy_power), 3),
                "sell_power": round(float(sell_power), 3),
                "strength_diff": round(float(strength_diff), 3),
                "dynamic_threshold": round(float(dynamic_threshold), 3),
                "market_stress": round(float(market_stress), 3),
            },
        )
        return (
            False,
            f"Signal weak (buy: {buy_power:.2f}, sell: {sell_power:.2f}, diff: {strength_diff:.2f}, stress: {market_stress:.2f})",
        )

    def _prioritize_signals(self, all_signals, market_regime, market_stress):
        """Prioritize signals to prevent conflicts and ensure fool-proof trading"""
        if not all_signals:
            return []

        # Signal priority hierarchy (higher = more important)
        priority_map = {
            "ENSEMBLE": 10,  # Highest priority - meta-analysis
            "CRT": 9,  # Comprehensive multi-timeframe analysis
            "ML": 7,  # Machine learning predictions
            "TECHNICAL": 5,  # Individual technical indicators
        }

        # Quality scoring for each signal
        scored_signals = []
        for signal in all_signals:
            base_priority = priority_map.get(signal["type"], 1)

            # Quality modifiers
            quality_score = 0

            # Confidence modifier
            confidence = signal.get("confidence", 0.5)
            if confidence > 0.8:
                quality_score += 2
            elif confidence > 0.6:
                quality_score += 1

            # Signal strength modifier
            signal_type = signal.get("signal", "")
            if signal_type in ["STRONG_BUY", "STRONG_SELL"]:
                quality_score += 1

            # Type-specific quality checks
            if signal["type"] == "CRT":
                # CRT quality based on composite score and component alignment
                composite_score = abs(signal.get("composite_score", 0))
                components = signal.get("components", {})
                aligned_components = sum(
                    1 for comp_score in components.values() if abs(comp_score) > 0.1
                )
                if composite_score > 0.2 and aligned_components >= 3:
                    quality_score += 2
            elif signal["type"] == "ML":
                # ML quality based on indicator count and data source
                indicators = signal.get("indicators", 0)
                data_source = signal.get("data_source", "")
                if indicators >= 20:
                    quality_score += 1
                if data_source == "BINANCE_REAL":
                    quality_score += 1
            elif signal["type"] == "ENSEMBLE":
                # Ensemble quality based on agreement and consensus
                buy_ratio = signal.get("buy_ratio", 0.5)
                consensus = abs(signal.get("consensus", 0))
                if consensus > 0.3 and (buy_ratio > 0.7 or buy_ratio < 0.3):
                    quality_score += 2

            # Market condition modifiers
            if market_stress > 0.6:
                # In high stress, prefer conservative signals
                if signal["type"] in ["ENSEMBLE", "CRT"]:
                    quality_score += 1
                elif signal["type"] == "TECHNICAL" and confidence < 0.7:
                    quality_score -= 1

            # Regime-specific adjustments
            if market_regime in ["STRONG_BULL", "STRONG_BEAR"]:
                if signal["type"] == "CRT":  # CRT handles trends well
                    quality_score += 1
            elif market_regime == "HIGH_VOL_SIDEWAYS":
                if signal["type"] == "ENSEMBLE":  # Ensemble handles uncertainty well
                    quality_score += 1

            total_priority = base_priority + quality_score
            scored_signals.append(
                {
                    **signal,
                    "priority_score": total_priority,
                    "quality_score": quality_score,
                }
            )

        # Sort by priority (highest first)
        scored_signals.sort(key=lambda x: x["priority_score"], reverse=True)

        # Conflict resolution: remove conflicting signals from lower priority sources
        filtered_signals = []
        buy_signals = []
        sell_signals = []

        for signal in scored_signals:
            signal_type = signal.get("signal", "")
            signal_priority = signal["priority_score"]

            if signal_type in ["BUY", "STRONG_BUY"]:
                # Check for conflicts with existing sell signals
                conflicting_sells = [
                    s
                    for s in sell_signals
                    if s["priority_score"] >= signal_priority - 2
                ]
                if not conflicting_sells:
                    buy_signals.append(signal)
                    filtered_signals.append(signal)
            elif signal_type in ["SELL", "STRONG_SELL"]:
                # Check for conflicts with existing buy signals
                conflicting_buys = [
                    s for s in buy_signals if s["priority_score"] >= signal_priority - 2
                ]
                if not conflicting_buys:
                    sell_signals.append(signal)
                    filtered_signals.append(signal)
            else:
                # HOLD signals don't conflict
                filtered_signals.append(signal)

        log_component_debug(
            "SIGNAL_PRIORITIZATION",
            "Signals prioritized and filtered",
            {
                "original_count": len(all_signals),
                "filtered_count": len(filtered_signals),
                "buy_signals": len(buy_signals),
                "sell_signals": len(sell_signals),
                "market_regime": market_regime,
                "market_stress": round(float(market_stress), 3),
            },
        )

        return filtered_signals

    def execute_ultimate_trade(
        self,
        symbol,
        ml_predictions,
        market_data,
        historical_prices,
        ensemble_signal=None,
    ):
        """Execute ultimate trade with all advanced systems"""
        # Refresh the in-memory toggle from persisted state so the trade executor
        # honors the LIVE dashboard switch even if this instance was initialized
        # with a different env value.
        try:
            profile = getattr(self, "persistence_profile", None) or "default"
            candidate_files = [
                os.path.join("bot_persistence", str(profile), str(profile), "bot_state.json"),
                os.path.join("bot_persistence", str(profile), "bot_state.json"),
            ]
            state_file = next((p for p in candidate_files if os.path.exists(p)), None)
            if state_file:
                with open(state_file, "r") as handle:
                    state = json.load(handle)
                trader_state = state.get("trader_state") or {}
                persisted_enabled = trader_state.get("trading_enabled")
                if isinstance(persisted_enabled, bool):
                    global_breaker_active = bool(
                        getattr(getattr(self, "safety_manager", None), "global_breaker_active", False)
                    )
                    if persisted_enabled is False:
                        self.trading_enabled = False
                    elif not global_breaker_active:
                        self.trading_enabled = True
        except Exception:
            pass
        log_component_event(
            "TRADE_EXECUTION",
            "Trade execution requested",
            level=logging.DEBUG,
            details={
                "symbol": symbol,
                "trading_enabled": bool(self.trading_enabled),
                "real_trading_enabled": bool(
                    getattr(self, "real_trading_enabled", False)
                ),
                "open_positions": len(self.positions),
                "has_ml_predictions": bool(ml_predictions),
            },
        )
        if not self.trading_enabled:
            log_component_event(
                "TRADE_EXECUTION",
                "Trade execution denied: trading disabled",
                level=logging.WARNING,
                details={"symbol": symbol},
            )
            return False, "Trading disabled"

        self.latest_market_data[symbol] = market_data

        # Generate technical signals
        technical_signals = self.generate_technical_signals(
            symbol, market_data, historical_prices
        )
        log_component_debug(
            "TRADE_EXECUTION",
            "Signals assembled for execution",
            {
                "symbol": symbol,
                "technical_signal_count": len(technical_signals),
                "ml_signal_count": len(ml_predictions)
                if isinstance(ml_predictions, dict)
                else 0,
            },
        )

        # Analyze market regime
        market_regime = self.ensemble_system.analyze_market_regime_advanced(
            market_data, historical_prices
        )

        # Calculate market stress
        market_stress = self.risk_manager.calculate_market_stress(
            {symbol: market_data}, historical_prices
        )
        log_component_debug(
            "TRADE_EXECUTION",
            "Market context evaluated",
            {
                "symbol": symbol,
                "market_regime": market_regime,
                "market_stress": round(float(market_stress), 4)
                if isinstance(market_stress, (int, float))
                else market_stress,
            },
        )

        # NEW: Generate CRT signals
        crt_signal = self.crt_generator.generate_crt_signals(
            symbol, market_data, historical_prices
        )

        # Make ultimate trading decision
        should_trade, trade_signal = self.should_execute_ultimate_trade(
            symbol,
            ml_predictions,
            technical_signals,
            self.positions,
            market_regime,
            ensemble_signal,
            market_stress,
            market_data,
            historical_prices,
        )

        if not should_trade:
            log_component_event(
                "TRADE_EXECUTION",
                "Trade aborted by decision engine",
                level=logging.INFO,
                details={"symbol": symbol, "reason": trade_signal},
            )
            return False, trade_signal

        # Calculate enhanced confidence
        all_confidence = []
        if ml_predictions:
            all_confidence.extend(
                [pred["confidence"] for pred in ml_predictions.values()]
            )
        all_confidence.extend([sig["confidence"] for sig in technical_signals])
        if ensemble_signal:
            stabilized = getattr(self, "_last_ensemble_confidence", None)
            if stabilized is None and isinstance(ensemble_signal, dict):
                stabilized = self._stabilize_ensemble_confidence(
                    ensemble_signal.get("confidence", 0.5)
                )
            all_confidence.append(
                float(
                    stabilized
                    if stabilized is not None
                    else ensemble_signal.get("confidence", 0.5)
                )
            )
        if crt_signal:
            all_confidence.append(crt_signal["confidence"])

        avg_confidence = np.mean(all_confidence) if all_confidence else 0.5

        # Get volatility for position sizing
        volatility = self.calculate_volatility(historical_prices)

        # Calculate portfolio health
        portfolio_health = self.calculate_portfolio_health()

        if trade_signal in ["BUY", "STRONG_BUY"]:
            quantity, position_value = self.calculate_ultimate_position_size(
                symbol,
                market_data["price"],
                avg_confidence,
                volatility,  # type: ignore
                ensemble_signal,
                portfolio_health,
            )
            min_notional = self._get_symbol_min_notional(symbol)
            if min_notional and market_data.get("price"):
                try:
                    notional = float(position_value)
                    min_value = float(min_notional) * float(
                        TRADING_CONFIG.get("min_notional_buffer", 1.0) or 1.0
                    )
                    if notional < min_value:
                        message = f"Position value {notional:.2f} below Binance minNotional {min_value:.2f}"
                        log_component_event(
                            "TRADE_EXECUTION",
                            "Trade blocked: below min notional",
                            level=logging.WARNING,
                            details={
                                "symbol": symbol,
                                "notional": notional,
                                "min_value": min_value,
                            },
                        )
                        if hasattr(self.trade_history, "log_journal_event"):
                            self.trade_history.log_journal_event(
                                "MIN_NOTIONAL_BLOCK",
                                {
                                    "symbol": symbol,
                                    "desired_notional": notional,
                                    "min_value": min_value,
                                    "price": market_data["price"],
                                },
                            )
                        return False, message
                except Exception as exc:
                    bot_logger.warning(
                        "Unable to verify notional for %s error=%s", symbol, exc
                    )
            approved, reason = self.safety_manager.approve_trade(
                symbol,
                position_value,
                self.balance,
                market_stress=market_stress,
                volatility=volatility,  # type: ignore
                portfolio_health=portfolio_health,
            )
            if not approved:
                log_component_event(
                    "TRADE_EXECUTION",
                    "Trade blocked by safety manager",
                    level=logging.WARNING,
                    details={
                        "symbol": symbol,
                        "reason": reason,
                        "position_value": round(float(position_value), 2)
                        if isinstance(position_value, (int, float))
                        else position_value,
                    },
                )
                if hasattr(self.trade_history, "log_journal_event"):
                    self.trade_history.log_journal_event(
                        "SAFETY_BLOCK",
                        {
                            "symbol": symbol,
                            "reason": reason,
                            "position_value": position_value,
                            "market_stress": market_stress,
                            "volatility": volatility,
                        },
                    )
                return False, f"Safety block: {reason}"

            if self.balance >= position_value and quantity > 0:
                pre_trade_balance = self.balance
                existing_position = symbol in self.positions
                previous_position_snapshot = (
                    deepcopy(self.positions.get(symbol)) if existing_position else None
                )

                self.balance -= position_value
                entry_price = market_data["price"]

                # Enhanced position management with advanced stop-loss
                if existing_position:
                    old_pos = self.positions[symbol]
                    new_qty = old_pos["quantity"] + quantity
                    new_avg = (
                        (old_pos["quantity"] * old_pos["avg_price"])
                        + (quantity * entry_price)
                    ) / new_qty

                    # Calculate advanced stop-loss levels
                    atr_value = self.calculate_atr(historical_prices)
                    stops = self.stop_loss_system.calculate_multiple_stop_losses(
                        symbol, new_avg, entry_price, historical_prices, atr_value
                    )

                    tp_multiplier = 1.12 if trade_signal == "STRONG_BUY" else 1.08
                    sl_multiplier = 0.96 if trade_signal == "STRONG_BUY" else 0.965

                    self.positions[symbol] = {
                        "quantity": new_qty,
                        "avg_price": new_avg,
                        "entry_time": datetime.now(),
                        "take_profit": new_avg * tp_multiplier,
                        "stop_loss": new_avg * sl_multiplier,
                        "signal_strength": trade_signal,
                        "advanced_stops": stops,
                    }
                else:
                    # New position with ultimate parameters
                    atr_value = self.calculate_atr(historical_prices)
                    stops = self.stop_loss_system.calculate_multiple_stop_losses(
                        symbol, entry_price, entry_price, historical_prices, atr_value
                    )

                    tp_multiplier = 1.12 if trade_signal == "STRONG_BUY" else 1.08
                    sl_multiplier = 0.96 if trade_signal == "STRONG_BUY" else 0.965

                    self.positions[symbol] = {
                        "quantity": quantity,
                        "avg_price": entry_price,
                        "entry_time": datetime.now(),
                        "take_profit": entry_price * tp_multiplier,
                        "stop_loss": entry_price * sl_multiplier,
                        "signal_strength": trade_signal,
                        "advanced_stops": stops,
                    }

                ensemble_block = {}
                if isinstance(ml_predictions, dict):
                    ensemble_block = (
                        ml_predictions.get(
                            self.indicator_block_key,
                            ml_predictions.get("ultimate_ensemble", {}),
                        )
                        or {}
                    )

                # NEW: Enhanced trade recording with comprehensive data
                trade_data = {
                    "symbol": symbol,
                    "side": "BUY",
                    "quantity": quantity,
                    "price": entry_price,
                    "total": position_value,
                    "pnl": 0,
                    "pnl_percent": 0,
                    "signal": trade_signal,
                    "confidence": avg_confidence,
                    "type": self.trade_type_label,
                    "strategy": self.strategy_label,
                    "market_regime": market_regime,
                    "indicators_used": ensemble_block.get("indicators_total", 0),
                    "data_source": ensemble_block.get("data_source", "UNKNOWN"),
                    "ensemble_agreement": ensemble_signal.get("buy_ratio", 0)
                    if ensemble_signal
                    else 0,
                    "risk_adjustment": self.risk_manager.get_risk_multiplier(),
                    "market_stress": market_stress,
                    "advanced_stops_used": True,
                    "crt_signal": crt_signal,  # NEW: Include CRT signal data
                    "position_size_percent": (position_value / self.initial_balance)
                    * 100,
                    "profile": self.profile_prefix,
                }

                execution_mode = "paper"
                real_order_id = None
                real_response = None

                log_component_event(
                    "TRADE_EXECUTION",
                    "Executing BUY trade",
                    level=logging.INFO,
                    details={
                        "symbol": symbol,
                        "quantity": round(float(quantity), 6)
                        if isinstance(quantity, (int, float))
                        else quantity,
                        "price": round(float(entry_price), 4)
                        if isinstance(entry_price, (int, float))
                        else entry_price,
                        "signal": trade_signal,
                        "confidence": round(float(avg_confidence), 3)
                        if isinstance(avg_confidence, (int, float))
                        else avg_confidence,
                    },
                )

                if self.futures_trading_enabled:
                    trade_data["reason"] = ensemble_block.get("reason")
                    trade_data["execution_mode"] = "futures"
                    real_response = self._submit_futures_order(
                        symbol,
                        "BUY",
                        quantity,
                        leverage=None,
                        reason=ensemble_block.get("reason"),
                        details=trade_data
                    )
                    execution_mode = "futures"
                elif self.real_trading_enabled:
                    trade_data["reason"] = ensemble_block.get("reason")
                    trade_data["execution_mode"] = "real"
                    real_response = self._submit_real_order(
                        symbol, 
                        "BUY", 
                        quantity, 
                        price=entry_price,
                        reason=ensemble_block.get("reason"),
                        details=trade_data
                    )
                    if real_response is None:
                        self.balance = pre_trade_balance
                        if existing_position:
                            if previous_position_snapshot is not None:
                                self.positions[symbol] = previous_position_snapshot
                            else:
                                self.positions.pop(symbol, None)
                        else:
                            self.positions.pop(symbol, None)
                        log_component_event(
                            "TRADE_EXECUTION",
                            "Real BUY order failed, reverting trade",
                            level=logging.WARNING,
                            details={
                                "symbol": symbol,
                                "quantity": round(float(quantity), 6)
                                if isinstance(quantity, (int, float))
                                else quantity,
                            },
                        )
                        return False, "Real BUY order failed"

                    execution_mode = "real"
                    real_order_id = (
                        real_response.get("orderId")
                        if isinstance(real_response, dict)
                        else None
                    )
                    filled_qty = self._extract_filled_quantity(real_response, quantity)
                    net_qty = self._calculate_net_filled_quantity(
                        symbol, filled_qty, order_response=real_response
                    )
                    if net_qty <= 0:
                        self.balance = pre_trade_balance
                        if existing_position:
                            if previous_position_snapshot is not None:
                                self.positions[symbol] = previous_position_snapshot
                            else:
                                self.positions.pop(symbol, None)
                        else:
                            self.positions.pop(symbol, None)
                        log_component_event(
                            "TRADE_EXECUTION",
                            "Real BUY order resulted in zero net quantity",
                            level=logging.WARNING,
                            details={"symbol": symbol, "filled_qty": filled_qty},
                        )
                        return False, "Real BUY order failed"

                    quote_spent = self._calculate_quote_spent(
                        real_response, filled_qty, entry_price
                    )
                    if quote_spent <= 0:
                        quote_spent = filled_qty * entry_price

                    commissions = self._extract_commissions(real_response)
                    quote_asset = self._determine_quote_asset(symbol)
                    base_asset = self._determine_base_asset(symbol)
                    quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
                    base_commission = _safe_float(commissions.get(base_asset), 0.0)

                    actual_total_spent = quote_spent + quote_commission

                    # Deduct actual spent (including quote commission) from cash balance
                    self.balance = pre_trade_balance - actual_total_spent

                    prev_qty = (
                        previous_position_snapshot["quantity"]
                        if (existing_position and previous_position_snapshot)
                        else 0.0
                    )
                    prev_avg = (
                        previous_position_snapshot["avg_price"]
                        if (existing_position and previous_position_snapshot)
                        else entry_price
                    )
                    total_qty = prev_qty + net_qty

                    position_record = self.positions.get(symbol, {})
                    position_record["quantity"] = total_qty
                    if total_qty > 0:
                        total_cost = (prev_qty * prev_avg) + actual_total_spent
                        avg_price = total_cost / total_qty
                    else:
                        avg_price = entry_price
                    position_record["avg_price"] = avg_price
                    if existing_position and previous_position_snapshot:
                        position_record["entry_time"] = previous_position_snapshot.get(
                            "entry_time",
                            position_record.get("entry_time", datetime.now()),
                        )
                    else:
                        position_record["entry_time"] = datetime.now()

                    tp_multiplier = 1.12 if trade_signal == "STRONG_BUY" else 1.08
                    sl_multiplier = 0.96 if trade_signal == "STRONG_BUY" else 0.965
                    position_record["take_profit"] = avg_price * tp_multiplier
                    position_record["stop_loss"] = avg_price * sl_multiplier

                    atr_value = self.calculate_atr(historical_prices)
                    position_record[
                        "advanced_stops"
                    ] = self.stop_loss_system.calculate_multiple_stop_losses(
                        symbol, avg_price, avg_price, historical_prices, atr_value
                    )
                    self.positions[symbol] = position_record

                    trade_data["quantity"] = net_qty
                    trade_data["total"] = quote_spent
                    trade_data["quote_spent"] = quote_spent
                    trade_data["quote_commission"] = quote_commission
                    trade_data["base_commission"] = base_commission
                    trade_data["base_received"] = net_qty
                    trade_data["commissions"] = commissions
                    if self.initial_balance:
                        trade_data["position_size_percent"] = (
                            actual_total_spent / self.initial_balance
                        ) * 100

                    self._handle_auto_take_profit(
                        symbol, avg_price, total_qty, order_response=real_response
                    )

                trade_data["execution_mode"] = execution_mode
                if real_order_id:
                    trade_data["real_order_id"] = real_order_id

                if self.app:
                    with self.app.app_context():
                        self.trade_history.add_trade(trade_data)
                else:
                    self.trade_history.add_trade(trade_data)
                # Optionally persist system (automated) trades to the DB
                try:
                    self._maybe_record_system_trade(trade_data)
                except Exception:
                    pass
                self.bot_efficiency["total_trades"] += 1

                action_msg = (
                    f"🎯 {self.profile_prefix} BUY"
                    if trade_signal == "BUY"
                    else f"🎯💥 {self.profile_prefix} STRONG BUY"
                )
                return (
                    True,
                    f"{action_msg}: {quantity:.4f} {symbol} at ${entry_price:.2f}",
                )

        elif trade_signal in ["SELL", "STRONG_SELL"] and symbol in self.positions:
            position = self.positions[symbol]
            quantity = position["quantity"]
            sale_price = market_data["price"]
            sale_value = quantity * sale_price

            pnl = sale_value - (quantity * position["avg_price"])
            pnl_percent = (
                (pnl / (quantity * position["avg_price"])) * 100
                if position["avg_price"] > 0
                else 0
            )

            pre_trade_balance = self.balance
            position_snapshot = deepcopy(position)

            ensemble_block = {}
            if isinstance(ml_predictions, dict):
                ensemble_block = (
                    ml_predictions.get(
                        self.indicator_block_key,
                        ml_predictions.get("ultimate_ensemble", {}),
                    )
                    or {}
                )

            trade_data = {
                "symbol": symbol,
                "side": "SELL",
                "quantity": quantity,
                "price": sale_price,
                "total": sale_value,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "signal": trade_signal,
                "confidence": avg_confidence,
                "type": self.trade_type_label,
                "strategy": self.strategy_label,
                "market_regime": market_regime,
                "indicators_used": ensemble_block.get("indicators_total", 0),
                "data_source": ensemble_block.get("data_source", "UNKNOWN"),
                "ensemble_agreement": ensemble_signal.get("sell_ratio", 0)
                if ensemble_signal
                else 0,
                "risk_adjustment": self.risk_manager.get_risk_multiplier(),
                "market_stress": market_stress,
                "advanced_stops_used": True,
                "crt_signal": crt_signal,  # NEW: Include CRT signal data
                "position_size_percent": (
                    position["quantity"] * position["avg_price"] / self.initial_balance
                )
                * 100,
                "profile": self.profile_prefix,
            }

            execution_mode = "paper"
            real_order_id = None
            real_response = None

            log_component_event(
                "TRADE_EXECUTION",
                "Executing SELL trade",
                level=logging.INFO,
                details={
                    "symbol": symbol,
                    "quantity": round(float(quantity), 6)
                    if isinstance(quantity, (int, float))
                    else quantity,
                    "price": round(float(sale_price), 4)
                    if isinstance(sale_price, (int, float))
                    else sale_price,
                    "signal": trade_signal,
                    "pnl_percent": round(float(pnl_percent), 3)
                    if isinstance(pnl_percent, (int, float))
                    else pnl_percent,
                },
            )

            if self.futures_trading_enabled:
                self._cancel_auto_take_profit(symbol)
                trade_data["reason"] = ensemble_block.get("reason")
                trade_data["execution_mode"] = "futures"
                real_response = self._submit_futures_order(
                    symbol,
                    "SELL",
                    quantity,
                    leverage=None,
                    reason=ensemble_block.get("reason"),
                    details=trade_data
                )
                execution_mode = "futures"
            elif self.real_trading_enabled:
                self._cancel_auto_take_profit(symbol)
                trade_data["reason"] = ensemble_block.get("reason")
                trade_data["execution_mode"] = "real"
                real_response = self._submit_real_order(
                    symbol, 
                    "SELL", 
                    quantity, 
                    price=sale_price,
                    reason=ensemble_block.get("reason"),
                    details=trade_data
                )
                if (
                    isinstance(real_response, dict)
                    and real_response.get("status") == "SKIPPED"
                ):
                    skip_reason = real_response.get("reason")
                    skip_message = (
                        real_response.get("message") or skip_reason or "Skipped"
                    )
                    log_component_event(
                        "TRADE_EXECUTION",
                        "Real SELL skipped",
                        level=logging.WARNING,
                        details={
                            "symbol": symbol,
                            "reason": skip_reason,
                            "details": real_response,
                        },
                    )
                    if skip_reason in {"min_notional", "insufficient_quantity"}:
                        self.positions.pop(symbol, None)
                    else:
                        self.positions[symbol] = position_snapshot
                    return False, f"Real SELL skipped: {skip_message}"
                if real_response is None:
                    self.balance = pre_trade_balance
                    self.positions[symbol] = position_snapshot
                    failure_reason = getattr(self.real_trader, "last_error", "unknown")
                    log_component_event(
                        "TRADE_EXECUTION",
                        "Real SELL order failed, reverting trade",
                        level=logging.WARNING,
                        details={
                            "symbol": symbol,
                            "quantity": round(float(quantity), 6)
                            if isinstance(quantity, (int, float))
                            else quantity,
                            "reason": failure_reason,
                        },
                    )
                    return False, f"Real SELL order failed: {failure_reason}"

                execution_mode = "real"
                real_order_id = (
                    real_response.get("orderId")
                    if isinstance(real_response, dict)
                    else None
                )
                # compute actual quote received and commissions
                executed_qty = self._extract_filled_quantity(real_response, quantity)
                quote_received = self._calculate_quote_spent(
                    real_response, executed_qty, sale_price
                )
                commissions = self._extract_commissions(real_response)
                quote_asset = self._determine_quote_asset(symbol)
                quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
                net_credit = quote_received - quote_commission
                # apply net credit to balance
                self.balance = pre_trade_balance + net_credit
                # update recorded sale_value to actual received for reporting
                sale_value = quote_received
                # Recompute realized PnL from actual net proceeds (provably required for REAL exits).
                invested = quantity * position["avg_price"]
                pnl = net_credit - invested
                pnl_percent = (pnl / invested) * 100 if invested > 0 else 0
                trade_data["commissions"] = commissions
                trade_data["quote_received"] = quote_received
                trade_data["quote_commission"] = quote_commission
                trade_data["total"] = sale_value
                trade_data["pnl"] = pnl
                trade_data["pnl_percent"] = pnl_percent
            else:
                # paper trading: apply theoretical sale_value
                self.balance += sale_value

            self.safety_manager.register_trade_result(symbol, pnl)

            # Update performance tracking
            self.daily_pnl += pnl
            current_total = self.balance + sum(
                pos["quantity"] * market_data["price"]
                for pos in self.positions.values()
            )
            self.peak_balance = max(self.peak_balance, current_total)
            drawdown = (
                (self.peak_balance - current_total) / self.peak_balance
                if self.peak_balance > 0
                else 0
            )
            self.max_drawdown = max(self.max_drawdown, drawdown)
            
            # Sync rolling history
            self._update_balance_history(current_total)

            # Update bot efficiency
            self.bot_efficiency["total_trades"] += 1
            if pnl > 0:
                self.bot_efficiency["successful_trades"] += 1
            self.bot_efficiency["total_profit"] += pnl

            trade_data["execution_mode"] = execution_mode
            if real_order_id:
                trade_data["real_order_id"] = real_order_id
            if self.app:
                with self.app.app_context():
                    self.trade_history.add_trade(trade_data)
            else:
                self.trade_history.add_trade(trade_data)
            # Optionally persist system (automated) trades to the DB
            try:
                self._maybe_record_system_trade(trade_data)
            except Exception:
                pass

            # REMOVE position from in-memory tracking after successful exit
            self.positions.pop(symbol, None)

            action_msg = (
                f"🎯 {self.profile_prefix} SELL"
                if trade_signal == "SELL"
                else f"🎯💥 {self.profile_prefix} STRONG SELL"
            )
            return (
                True,
                f"{action_msg}: {quantity:.4f} {symbol} at ${sale_price:.2f} (P&L: {pnl_percent:+.2f}%)",
            )

        log_component_debug(
            "TRADE_EXECUTION",
            "No execution action taken",
            {"symbol": symbol, "trade_signal": trade_signal},
        )
        return False, f"No action: {trade_signal}"

    def calculate_volatility(self, prices, period=20):
        """Calculate volatility from price data"""
        if len(prices) < period:
            return 0.02

        returns = np.diff(np.log(prices[-period:]))
        return np.std(returns) if len(returns) > 0 else 0.02

    def calculate_atr(self, prices, period=14):
        """Calculate Average True Range"""
        if len(prices) < period:
            return 0.02

        # Simplified ATR calculation
        price_changes = np.diff(prices[-period:])
        return np.mean(np.abs(price_changes)) if len(price_changes) > 0 else 0.02

    def calculate_portfolio_health(self):
        """Calculate portfolio health indicator using rolling 24h window"""
        try:
            # Factor 1: Rolling Drawdown
            # Calculate current total value for rolling check
            current_total = self.balance + sum(
                pos.get("quantity", 0) * (pos.get("avg_price") or pos.get("entry_price", 0))
                for pos in self.positions.values()
            )
            self._update_balance_history(current_total)
            rolling_dd = self._get_rolling_max_drawdown(current_total)
            
            # Use rolling_dd for penalty (max_drawdown is retained for session stats but not gating)
            drawdown_penalty = min(rolling_dd * 3, 0.5)

            # Factor 2: Concentration (Gated by position count)
            # We only penalize concentration if we have multiple positions.
            # This prevents the "single-asset deadlock" where low health from one
            # position prevents opening the diversifying 2nd trade.
            if len(self.positions) > 1:
                position_values = [
                    pos.get("quantity", 0) * (pos.get("avg_price") or pos.get("entry_price", 0))
                    for pos in self.positions.values()
                ]
                total_val = sum(position_values)
                concentration = (max(position_values) / total_val) if total_val > 0 else 0
                concentration_penalty = concentration * 0.3
            else:
                concentration_penalty = 0

            # Factor 3: Recent performance
            recent_trades = [
                t
                for t in self.trade_history.get_trade_history()[-10:]
                if "pnl_percent" in t
            ]
            if recent_trades:
                recent_performance = (
                    np.mean([t["pnl_percent"] for t in recent_trades]) / 100
                )
                performance_penalty = max(-recent_performance, 0) * 2
            else:
                performance_penalty = 0

            health = (
                1.0 - drawdown_penalty - concentration_penalty - performance_penalty
            )

            # Enhanced logging for portfolio health diagnostics
            if random.random() < 0.05: # Log 5% of calculations to avoid noise
                log_component_event(
                    "PORTFOLIO",
                    f"[HEALTH_REPORT] Score={health:.2f} (DD={drawdown_penalty:.2f}, Conc={concentration_penalty:.2f}, Perf={performance_penalty:.2f}) Positions={len(self.positions)}",
                    level=logging.INFO
                )

            return max(0.3, min(1.5, health))

        except Exception as e:
            print(f"❌ Portfolio health calculation error: {e}")
            log_component_event(
                "PORTFOLIO",
                f"Portfolio health calculation error: {e}",
                level=logging.ERROR,
            )
            bot_logger.exception("Portfolio health calculation error")
            return 1.0

    def generate_technical_signals(self, symbol, market_data, historical_prices):
        """Enhanced technical signals with multiple timeframes"""
        signals = []

        if len(historical_prices) < 20:
             return signals

        # DEBUG: Force signal to verify execution pipeline
        if symbol == "BTCUSDT":
             signals.append({
                "symbol": symbol,
                "signal_type": "DEBUG_FORCED",
                "confidence_score": 0.99,
                "timestamp": datetime.now().isoformat(),
                "current_price": float(market_data.get("price", 0)),
                "target_price": float(market_data.get("price", 0)) * 1.05,
                "stop_loss": float(market_data.get("price", 0)) * 0.98,
                "time_frame": "1m",
                "model_version": "DEBUG",
                "reason_code": "FORCE_TEST",
                "strategy": "DEBUG_STRATEGY",
                "signal": "STRONG_BUY",
                "confidence": 0.99,
                "price_target": float(market_data.get("price", 0)) * 1.05,
             })

        prices = np.array(historical_prices)
        current_price = market_data["price"]

        try:
            # Multi-timeframe RSI
            for period in [7, 14, 21]:
                rsi = talib.RSI(prices, timeperiod=period)
                if len(rsi) > 0 and not np.isnan(rsi[-1]):
                    current_rsi = rsi[-1]

                    if current_rsi < 20:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.80,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 1.20),
                                "stop_loss": float(current_price * 0.95),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_EXTREME_OVERSOLD",
                                "strategy": f"RSI_{period}_EXTREME_OVERSOLD",
                                "signal": "STRONG_BUY",
                                "confidence": 0.80,
                                "price_target": current_price * 1.20,
                            }
                        )
                    elif current_rsi < 25:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.75,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 1.15),
                                "stop_loss": float(current_price * 0.96),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_STRONG_OVERSOLD",
                                "strategy": f"RSI_{period}_STRONG_OVERSOLD",
                                "signal": "STRONG_BUY",
                                "confidence": 0.75,
                                "price_target": current_price * 1.15,
                            }
                        )
                    elif current_rsi < 30:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.65,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 1.08),
                                "stop_loss": float(current_price * 0.97),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_OVERSOLD",
                                "strategy": f"RSI_{period}_OVERSOLD",
                                "signal": "BUY",
                                "confidence": 0.65,
                                "price_target": current_price * 1.08,
                            }
                        )
                    elif current_rsi > 80:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.80,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 0.82),
                                "stop_loss": float(current_price * 1.05),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_EXTREME_OVERBOUGHT",
                                "strategy": f"RSI_{period}_EXTREME_OVERBOUGHT",
                                "signal": "STRONG_SELL",
                                "confidence": 0.80,
                                "price_target": current_price * 0.82,
                            }
                        )
                    elif current_rsi > 75:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.75,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 0.85),
                                "stop_loss": float(current_price * 1.04),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_STRONG_OVERBOUGHT",
                                "strategy": f"RSI_{period}_STRONG_OVERBOUGHT",
                                "signal": "STRONG_SELL",
                                "confidence": 0.75,
                                "price_target": current_price * 0.85,
                            }
                        )
                    elif current_rsi > 70:
                        signals.append(
                            {
                                "symbol": symbol,
                                "signal_type": "TECHNICAL_RSI",
                                "confidence_score": 0.65,
                                "timestamp": datetime.now().isoformat(),
                                "current_price": float(current_price),
                                "target_price": float(current_price * 0.92),
                                "stop_loss": float(current_price * 1.03),
                                "time_frame": f"{period}D",
                                "model_version": "RSI_v1.0",
                                "reason_code": f"RSI_{period}_OVERBOUGHT",
                                "strategy": f"RSI_{period}_OVERBOUGHT",
                                "signal": "SELL",
                                "confidence": 0.65,
                                "price_target": current_price * 0.92,
                            }
                        )
        except Exception as e:
            print(f"❌ RSI calculation error for {symbol}: {e}")
            log_component_event(
                "SIGNALS",
                f"RSI calculation error for {symbol}: {e}",
                level=logging.ERROR,
            )
            bot_logger.exception("RSI calculation error for %s", symbol)

        try:
            # Enhanced MACD with histogram analysis
            macd, macd_signal, macd_hist = talib.MACD(prices)
            if len(macd_hist) > 0:
                current_hist = macd_hist[-1]
                prev_hist = macd_hist[-2] if len(macd_hist) > 1 else 0
                prev_prev_hist = macd_hist[-3] if len(macd_hist) > 2 else 0

                # Strong bullish: histogram positive and accelerating
                if (
                    current_hist > 0
                    and current_hist > prev_hist
                    and prev_hist > prev_prev_hist
                ):
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "TECHNICAL_MACD",
                            "confidence_score": 0.75,
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": float(current_price * 1.05),
                            "stop_loss": float(current_price * 0.97),
                            "time_frame": "1D",
                            "model_version": "MACD_v1.0",
                            "reason_code": "MACD_STRONG_BULLISH_ACCEL",
                            "strategy": "MACD_STRONG_BULLISH_ACCEL",
                            "signal": "STRONG_BUY",
                            "confidence": 0.75,
                        }
                    )
                elif current_hist > 0 and current_hist > prev_hist:
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "TECHNICAL_MACD",
                            "confidence_score": 0.65,
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": float(current_price * 1.03),
                            "stop_loss": float(current_price * 0.98),
                            "time_frame": "1D",
                            "model_version": "MACD_v1.0",
                            "reason_code": "MACD_BULLISH",
                            "strategy": "MACD_BULLISH",
                            "signal": "BUY",
                            "confidence": 0.65,
                        }
                    )
                # Strong bearish: histogram negative and accelerating
                elif (
                    current_hist < 0
                    and current_hist < prev_hist
                    and prev_hist < prev_prev_hist
                ):
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "TECHNICAL_MACD",
                            "confidence_score": 0.75,
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": float(current_price * 0.95),
                            "stop_loss": float(current_price * 1.03),
                            "time_frame": "1D",
                            "model_version": "MACD_v1.0",
                            "reason_code": "MACD_STRONG_BEARISH_ACCEL",
                            "strategy": "MACD_STRONG_BEARISH_ACCEL",
                            "signal": "STRONG_SELL",
                            "confidence": 0.75,
                        }
                    )
                elif current_hist < 0 and current_hist < prev_hist:
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "TECHNICAL_MACD",
                            "confidence_score": 0.65,
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": float(current_price * 0.97),
                            "stop_loss": float(current_price * 1.02),
                            "time_frame": "1D",
                            "model_version": "MACD_v1.0",
                            "reason_code": "MACD_BEARISH",
                            "strategy": "MACD_BEARISH",
                            "signal": "SELL",
                            "confidence": 0.65,
                        }
                    )
        except Exception as e:
            print(f"❌ MACD calculation error for {symbol}: {e}")
            log_component_event(
                "SIGNALS",
                f"MACD calculation error for {symbol}: {e}",
                level=logging.ERROR,
            )
            bot_logger.exception("MACD calculation error for %s", symbol)

        if getattr(self, "qfm_engine", None):
            try:
                self.qfm_engine.compute_realtime_features(
                    symbol, market_data
                )
                qfm_signal = self.qfm_engine.generate_signal(symbol)
                if qfm_signal:
                    signals.append(
                        {
                            "symbol": symbol,
                            "signal_type": "QFM",
                            "confidence_score": qfm_signal.get("confidence", 0.6),
                            "timestamp": datetime.now().isoformat(),
                            "current_price": float(current_price),
                            "target_price": qfm_signal.get(
                                "target_price", float(current_price * 1.02)
                            ),
                            "stop_loss": qfm_signal.get(
                                "stop_loss", float(current_price * 0.98)
                            ),
                            "time_frame": "MULTI_TIMEFRAME",
                            "model_version": "QFM_v1.0",
                            "reason_code": qfm_signal.get(
                                "reason_code", f'QFM_{qfm_signal.get("signal", "HOLD")}'
                            ),
                            "strategy": qfm_signal.get(
                                "strategy", "QUANTUM_FUSION_MOMENTUM"
                            ),
                            "signal": qfm_signal.get("signal", "HOLD"),
                            "confidence": qfm_signal.get("confidence", 0.6),
                            "score": qfm_signal.get("score"),
                            "metrics": qfm_signal.get("metrics"),
                            "type": "QFM",  # Add type field for proper weighting
                        }
                    )
                    try:
                        if "dashboard_data" in globals():
                            profile_key = (
                                "optimized_qfm_signals"
                                if str(getattr(self, "profile_prefix", ""))
                                .upper()
                                .startswith("OPTIMIZED")
                                else "qfm_signals"
                            )
                            dashboard_data.setdefault(profile_key, {})
                            dashboard_data[profile_key][symbol] = {
                                "symbol": symbol,
                                "signal": qfm_signal.get("signal", "HOLD"),
                                "confidence": float(
                                    qfm_signal.get("confidence", 0.0) or 0.0
                                ),
                                "score": float(qfm_signal.get("score", 0.0) or 0.0),
                                "metrics": qfm_signal.get("metrics", {}),
                                "price": _safe_float(market_data.get("price"))
                                if isinstance(market_data, dict)
                                else None,
                                "updated_at": datetime.utcnow().isoformat(),
                            }
                    except Exception as dash_exc:
                        bot_logger.warning(
                            "Failed to update QFM dashboard data for %s: %s",
                            symbol,
                            dash_exc,
                        )
            except Exception as e:
                print(f"❌ QFM signal generation error for {symbol}: {e}")
                log_component_event(
                    "SIGNALS",
                    f"QFM signal generation error for {symbol}: {e}",
                    level=logging.ERROR,
                )
                bot_logger.exception("QFM signal generation error for %s", symbol)

        return signals

    def check_advanced_stop_loss(self, current_prices):
        """Check and execute advanced stop-loss mechanisms"""
        closed_positions = []
        for symbol, position in list(self.positions.items()):
            if symbol in current_prices:
                current_price = current_prices[symbol]

                # Check traditional stop-loss first
                if current_price <= position.get("stop_loss", 0):
                    self.execute_stop_loss(
                        symbol,
                        position,
                        current_price,
                        "TRADITIONAL_SL",
                        closed_positions,
                    )
                    continue

                # Check take profit
                if current_price >= position.get("take_profit", 0):
                    self.execute_take_profit(
                        symbol, position, current_price, closed_positions
                    )
                    continue

                # Check advanced stop-loss if enabled
                if (
                    TRADING_CONFIG["advanced_stop_loss"]
                    and "advanced_stops" in position
                ):
                    stops = position["advanced_stops"]
                    triggered_stop = self.stop_loss_system.should_trigger_stop_loss(
                        symbol, current_price, position, stops
                    )

                    if triggered_stop:
                        stop_type, stop_price = triggered_stop
                        self.execute_stop_loss(
                            symbol,
                            position,
                            current_price,
                            f"ADVANCED_{stop_type}",
                            closed_positions,
                        )

        return closed_positions

    def execute_stop_loss(
        self, symbol, position, current_price, stop_type, closed_positions
    ):
        """Execute stop-loss trade"""
        quantity = position["quantity"]
        sale_value = quantity * current_price
        pre_trade_balance = self.balance

        pnl = sale_value - (quantity * position["avg_price"])
        pnl_percent = (
            (pnl / (quantity * position["avg_price"])) * 100
            if position["avg_price"] > 0
            else 0
        )

        del self.positions[symbol]

        # NEW: Enhanced trade recording
        trade_data = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": current_price,
            "total": sale_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "signal": stop_type,
            "confidence": 1.0,
            "type": f"ADVANCED_{stop_type}",
            "strategy": "STOP_LOSS",
            "market_regime": self.ensemble_system.market_regime,
            "risk_adjustment": self.risk_manager.get_risk_multiplier(),
            "market_stress": self.risk_manager.market_stress_indicator,
            "advanced_stops_used": True,
            "position_size_percent": (
                position["quantity"] * position["avg_price"] / self.initial_balance
            )
            * 100,
            "profile": self.profile_prefix,
        }
        execution_mode = "paper"
        real_order_id = None

        if self.futures_trading_enabled:
            self._cancel_auto_take_profit(symbol)
            trade_data["reason"] = f"Stop Loss ({stop_type})"
            trade_data["execution_mode"] = "futures"
            response = self._submit_futures_order(
                symbol,
                "SELL",
                quantity,
                leverage=None,
                reduce_only=True,
                reason=trade_data["reason"],
                details=trade_data
            )
            execution_mode = "futures"
        elif self.real_trading_enabled:
            self._cancel_auto_take_profit(symbol)
            trade_data["reason"] = f"Stop Loss ({stop_type})"
            response = self._submit_real_order(
                symbol, 
                "SELL", 
                quantity, 
                price=current_price,
                reason=trade_data["reason"],
                details=trade_data
            )
            if response is None:
                self.positions[symbol] = position
                log_component_event(
                    "STOP_LOSS",
                    "Real SELL order failed, stop-loss reverted",
                    level=logging.WARNING,
                    details={
                        "symbol": symbol,
                        "quantity": round(float(quantity), 6)
                        if isinstance(quantity, (int, float))
                        else quantity,
                    },
                )
                return
            execution_mode = "real"
            if isinstance(response, dict):
                real_order_id = response.get("orderId")
            executed_qty = self._extract_filled_quantity(response, quantity)
            quote_received = self._calculate_quote_spent(
                response, executed_qty, current_price
            )
            commissions = self._extract_commissions(response)
            quote_asset = self._determine_quote_asset(symbol)
            quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
            net_credit = quote_received - quote_commission
            self.balance = pre_trade_balance + net_credit
            trade_data["commissions"] = commissions
            trade_data["quote_received"] = quote_received
            trade_data["quote_commission"] = quote_commission
        else:
            self.balance += sale_value

        trade_data["execution_mode"] = execution_mode
        if real_order_id:
            trade_data["real_order_id"] = real_order_id
        self.trade_history.add_trade(trade_data)
        # Optionally persist system (automated) trades to the DB
        try:
            self._maybe_record_system_trade(trade_data)
        except Exception:
            pass
        # Optionally persist system (automated) trades to the DB
        try:
            self._maybe_record_system_trade(trade_data)
        except Exception:
            pass

        self.safety_manager.register_trade_result(symbol, pnl)

        closed_positions.append(
            f"🛑 {stop_type}: {symbol} at ${current_price:.2f} (P&L: {pnl_percent:+.2f}%)"
        )

        # Update efficiency
        self.bot_efficiency["total_trades"] += 1
        if pnl > 0:
            self.bot_efficiency["successful_trades"] += 1
        self.bot_efficiency["total_profit"] += pnl

    def execute_take_profit(self, symbol, position, current_price, closed_positions):
        """Execute take profit trade"""
        quantity = position["quantity"]
        sale_value = quantity * current_price
        pre_trade_balance = self.balance

        pnl = sale_value - (quantity * position["avg_price"])
        pnl_percent = (
            (pnl / (quantity * position["avg_price"])) * 100
            if position["avg_price"] > 0
            else 0
        )

        del self.positions[symbol]

        # NEW: Enhanced trade recording
        trade_data = {
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": current_price,
            "total": sale_value,
            "pnl": pnl,
            "pnl_percent": pnl_percent,
            "signal": "TAKE_PROFIT",
            "confidence": 1.0,
            "type": "ADVANCED_TAKE_PROFIT",
            "strategy": "TAKE_PROFIT",
            "market_regime": self.ensemble_system.market_regime,
            "risk_adjustment": self.risk_manager.get_risk_multiplier(),
            "market_stress": self.risk_manager.market_stress_indicator,
            "advanced_stops_used": True,
            "position_size_percent": (
                position["quantity"] * position["avg_price"] / self.initial_balance
            )
            * 100,
            "profile": self.profile_prefix,
        }
        execution_mode = "paper"
        real_order_id = None

        if self.futures_trading_enabled:
            self._cancel_auto_take_profit(symbol)
            trade_data["reason"] = "Take Profit"
            trade_data["execution_mode"] = "futures"
            response = self._submit_futures_order(
                symbol,
                "SELL",
                quantity,
                leverage=None,
                reduce_only=True,
                reason="Take Profit",
                details=trade_data
            )
            execution_mode = "futures"
        elif self.real_trading_enabled:
            self._cancel_auto_take_profit(symbol)
            trade_data["reason"] = "Take Profit"
            response = self._submit_real_order(
                symbol, 
                "SELL", 
                quantity, 
                price=current_price,
                reason="Take Profit",
                details=trade_data
            )
            if response is None:
                self.positions[symbol] = position
                log_component_event(
                    "TAKE_PROFIT",
                    "Real SELL order failed, take-profit reverted",
                    level=logging.WARNING,
                    details={
                        "symbol": symbol,
                        "quantity": round(float(quantity), 6)
                        if isinstance(quantity, (int, float))
                        else quantity,
                    },
                )
                return
            execution_mode = "real"
            if isinstance(response, dict):
                real_order_id = response.get("orderId")
            executed_qty = self._extract_filled_quantity(response, quantity)
            quote_received = self._calculate_quote_spent(
                response, executed_qty, current_price
            )
            commissions = self._extract_commissions(response)
            quote_asset = self._determine_quote_asset(symbol)
            quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
            net_credit = quote_received - quote_commission
            self.balance = pre_trade_balance + net_credit
            trade_data["commissions"] = commissions
            trade_data["quote_received"] = quote_received
            trade_data["quote_commission"] = quote_commission
        else:
            self.balance += sale_value

        trade_data["execution_mode"] = execution_mode
        if real_order_id:
            trade_data["real_order_id"] = real_order_id
        self.trade_history.add_trade(trade_data)

        self.safety_manager.register_trade_result(symbol, pnl)

        closed_positions.append(
            f"✅ ADVANCED TP: {symbol} at ${current_price:.2f} (P&L: {pnl_percent:+.2f}%)"
        )

        # Update efficiency
        self.bot_efficiency["total_trades"] += 1
        if pnl > 0:
            self.bot_efficiency["successful_trades"] += 1
        self.bot_efficiency["total_profit"] += pnl

    def force_close_all_positions(self, reason="EMERGENCY", current_prices=None):
        """Liquidate all open positions immediately."""
        if current_prices is None:
            current_prices = {}
        if not current_prices and self.latest_market_data:
            current_prices = {
                sym: data.get("price")
                for sym, data in self.latest_market_data.items()
                if isinstance(data, dict)
            }

        closed = []
        for symbol, position in list(self.positions.items()):
            sale_price = current_prices.get(symbol, position["avg_price"])
            quantity = position["quantity"]
            sale_value = quantity * sale_price
            invested = quantity * position["avg_price"]
            pnl = sale_value - invested
            pnl_percent = (pnl / invested) * 100 if invested > 0 else 0

            trade_data = {
                "symbol": symbol,
                "side": "SELL",
                "quantity": quantity,
                "price": sale_price,
                "total": sale_value,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "signal": reason,
                "confidence": 1.0,
                "type": "EMERGENCY_EXIT",
                "strategy": "EMERGENCY_STOP",
                "market_regime": self.ensemble_system.market_regime,
                "risk_adjustment": self.risk_manager.get_risk_multiplier(),
                "market_stress": self.risk_manager.market_stress_indicator,
                "advanced_stops_used": False,
                "position_size_percent": (invested / self.initial_balance) * 100
                if self.initial_balance
                else 0,
                "profile": self.profile_prefix,
            }
            execution_mode = "paper"
            real_order_id = None

            if self.real_trading_enabled:
                self._cancel_auto_take_profit(symbol)
                response = self._submit_real_order(
                    symbol, "SELL", quantity, price=sale_price
                )
                if response is None:
                    log_component_event(
                        "EMERGENCY_EXIT",
                        "Real emergency SELL failed, skipping trade",
                        level=logging.ERROR,
                        details={
                            "symbol": symbol,
                            "quantity": round(float(quantity), 6)
                            if isinstance(quantity, (int, float))
                            else quantity,
                        },
                    )
                    continue
                execution_mode = "real"
                if isinstance(response, dict):
                    real_order_id = response.get("orderId")
                executed_qty = self._extract_filled_quantity(response, quantity)
                quote_received = self._calculate_quote_spent(
                    response, executed_qty, sale_price
                )
                commissions = self._extract_commissions(response)
                quote_asset = self._determine_quote_asset(symbol)
                quote_commission = _safe_float(commissions.get(quote_asset), 0.0)
                net_credit = quote_received - quote_commission
                self.balance += net_credit
            self.safety_manager.register_trade_result(symbol, pnl)
            trade_data["execution_mode"] = execution_mode
            if real_order_id:
                trade_data["real_order_id"] = real_order_id
            self.trade_history.add_trade(trade_data)

            closed.append(
                f"⚠️ Emergency exit {symbol}: {quantity:.4f} @ ${sale_price:.2f} (P&L: {pnl_percent:+.2f}%)"
            )
            del self.positions[symbol]

        if hasattr(self.trade_history, "log_journal_event") and closed:
            self.trade_history.log_journal_event(
                "EMERGENCY_EXIT",
                {
                    "reason": reason,
                    "closed_positions": closed,
                    "timestamp": datetime.now().isoformat(),
                },
            )

        return closed

    def improve_bot_efficiency_ultimate(self):
        """Ultimate self-improvement with all systems"""
        cfg = self._get_trading_config()
        self.bot_efficiency["learning_cycles"] += 1
        self.bot_efficiency["last_improvement"] = datetime.now().isoformat()

        # Calculate current performance
        trades = self.trade_history.get_trade_history()
        closed_trades = [t for t in trades if t.get("status") == "CLOSED"]
        if closed_trades:
            success_rate = (
                len([t for t in closed_trades if t.get("pnl", 0) > 0])
                / len(closed_trades)
            ) * 100
        else:
            success_rate = 0

        # Update risk manager
        portfolio_performance = (
            self.balance
            + sum(pos["quantity"] * 100 for pos in self.positions.values())
            - self.initial_balance
        ) / self.initial_balance

        risk_adjustment = self.risk_manager.adjust_risk_profile(
            portfolio_performance,
            self.max_drawdown,
            {"market_stress": self.risk_manager.market_stress_indicator},
        )

        # Store market stress history
        self.bot_efficiency["market_stress_history"].append(
            {
                "timestamp": datetime.now().isoformat(),
                "stress_level": self.risk_manager.market_stress_indicator,
                "risk_profile": self.risk_manager.current_risk_profile,
            }
        )

        # Keep only last 50 entries
        if len(self.bot_efficiency["market_stress_history"]) > 50:
            self.bot_efficiency["market_stress_history"].pop(0)

        # Advanced strategy adjustment
        if success_rate < 30:
            cfg["confidence_threshold"] = max(
                0.45, cfg["confidence_threshold"] - 0.04
            )
            print(
                f"🤖 {self.profile_prefix} Learning: Lowering confidence to {cfg['confidence_threshold']}"
            )

        elif success_rate > 70:
            cfg["risk_per_trade"] = min(
                0.025, cfg["risk_per_trade"] + 0.004
            )
            print(
                f"🤖 {self.profile_prefix} Learning: Increasing risk to {cfg['risk_per_trade']}"
            )

        print(
            f"🤖 {self.profile_prefix} Learning: Success Rate: {success_rate:.1f}%, Risk Profile: {self.risk_manager.current_risk_profile}"
        )
        return success_rate

    def get_portfolio_summary(self, current_prices):
        """Ultimate portfolio summary"""
        positions = []
        total_invested = 0
        total_current = 0

        for symbol, position in self.positions.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                quantity = position["quantity"]
                avg_price = position["avg_price"]
                invested = quantity * avg_price
                current_value = quantity * current_price
                pnl = current_value - invested
                pnl_percent = (pnl / invested) * 100 if invested > 0 else 0

                tp_price = position.get("take_profit", current_price)
                sl_price = position.get("stop_loss", current_price)
                tp_percent = ((tp_price / avg_price) - 1) * 100
                sl_percent = ((sl_price / avg_price) - 1) * 100

                positions.append(
                    {
                        "symbol": symbol,
                        "quantity": quantity,
                        "avg_price": avg_price,
                        "current_price": current_price,
                        "invested": invested,
                        "current_value": current_value,
                        "pnl": pnl,
                        "pnl_percent": pnl_percent,
                        "take_profit_percent": tp_percent,
                        "stop_loss_percent": sl_percent,
                        "entry_time": position["entry_time"],
                        "signal_strength": position.get("signal_strength", "BUY"),
                        "advanced_stops": position.get("advanced_stops", {}),
                    }
                )
                total_invested += invested
                total_current += current_value

        paper_total_value = self.balance + total_current
        total_pnl = paper_total_value - self.initial_balance
        total_return_percent = (
            (total_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0
        )

        # [PORTFOLIO_AUDIT] Detailed logging for portfolio calculation tracing
        log_component_debug(
            "[PORTFOLIO_CALC]",
            f"{getattr(self, 'profile_prefix', 'UNKNOWN')} Portfolio Breakdown: "
            f"cash_balance=${self.balance:.2f}, "
            f"position_count={len(positions)}, "
            f"position_value=${total_current:.2f}, "
            f"initial_balance=${self.initial_balance:.2f}, "
            f"computed_total=${paper_total_value:.2f}, "
            f"pnl=${total_pnl:.2f} ({total_return_percent:+.2f}%)"
        )

        paper_snapshot = {
            "balance": self.balance,
            "total_invested": total_invested,
            "total_current_value": total_current,
            "total_value": paper_total_value,
            "total_pnl": total_pnl,
            "total_return_percent": total_return_percent,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Calculate ultimate efficiency metrics
        trades = self.trade_history.get_trade_history()
        closed_trades = [t for t in trades if t.get("status") == "CLOSED"]
        if closed_trades:
            efficiency = (
                len([t for t in closed_trades if t.get("pnl", 0) > 0])
                / len(closed_trades)
            ) * 100
        else:
            efficiency = 0

        summary = {
            "balance": self.balance,
            "paper_balance": self.balance,
            "total_invested": total_invested,
            "total_current_value": total_current,
            "paper_total_value": paper_total_value,
            "total_portfolio_value": paper_total_value,
            "total_pnl": total_pnl,
            "total_return_percent": total_return_percent,
            "positions": positions,
            "initial_balance": self.initial_balance,
            "trading_enabled": self.trading_enabled,
            "max_drawdown": self.max_drawdown,
            "market_regime": self.ensemble_system.market_regime,
            "risk_adjustment": self.risk_manager.get_risk_multiplier(),
            "market_stress": self.risk_manager.market_stress_indicator,
            "risk_profile": self.risk_manager.current_risk_profile,
            "portfolio_health": self.calculate_portfolio_health(),
            "mode": "paper",
            "data_source": "paper_simulated",
            "real_holdings": [],
            "real_cash": None,
            "cash_breakdown": [],
            "real_equity": None,
            "bot_efficiency": {
                "success_rate": efficiency,
                "total_trades": self.bot_efficiency["total_trades"],
                "successful_trades": self.bot_efficiency["successful_trades"],
                "total_profit": self.bot_efficiency["total_profit"],
                "learning_cycles": self.bot_efficiency["learning_cycles"],
                "risk_adjustment": self.risk_manager.get_risk_multiplier(),
                "market_stress": self.risk_manager.market_stress_indicator,
                "last_improvement": self.bot_efficiency["last_improvement"],
            },
            "paper_snapshot": paper_snapshot,
            "real_account_snapshot": None,
        }
        real_snapshot = self._get_real_account_snapshot(current_prices)
        summary["real_account_snapshot"] = real_snapshot
        if real_snapshot and real_snapshot.get("total_equity") is not None:
            if self.real_equity_baseline is None:
                self.real_equity_baseline = real_snapshot["total_equity"]

            baseline = self.real_equity_baseline or 0.0
            real_pnl = 0.0
            real_return = 0.0
            if baseline:
                real_pnl = real_snapshot["total_equity"] - baseline
                real_return = (real_pnl / baseline) * 100 if baseline else 0.0

            summary.update(
                {
                    "balance": real_snapshot["cash"],
                    "total_invested": real_snapshot["asset_value"],
                    "total_current_value": real_snapshot["asset_value"],
                    "total_portfolio_value": real_snapshot["total_equity"],
                    "total_pnl": real_pnl,
                    "total_return_percent": real_return,
                    "mode": "real",
                    "data_source": "binance_spot",
                    "real_holdings": real_snapshot["holdings"],
                    "real_cash": real_snapshot["cash"],
                    "cash_breakdown": real_snapshot["cash_breakdown"],
                    "real_equity": real_snapshot["total_equity"],
                    "real_equity_baseline": baseline,
                    "real_account_can_trade": real_snapshot.get("can_trade"),
                    "real_account_updated_at": real_snapshot.get("updated_at"),
                    "paper_balance": None,
                    "paper_total_value": None,
                }
            )

        return summary

    # NEW: Get comprehensive trade statistics
    def get_trade_statistics(self):
        """Get comprehensive trade statistics"""
        return self.trade_history.get_trade_statistics()


# ==================== OPTIMIZED AI TRADER ====================
class OptimizedAIAutoTrader(UltimateAIAutoTrader):
    def __init__(self, initial_balance=10000):
        self.profile_prefix = "OPTIMIZED"
        self.trade_type_label = "OPTIMIZED_TRADE"
        self.strategy_label = "20_INDICATORS_OPTIMIZED"
        self.indicator_block_key = "optimized_ensemble"
        super().__init__(initial_balance=initial_balance)
        self.trade_history = ComprehensiveTradeHistory(
            data_dir="optimized_trade_data",
            log_callback=log_component_event,
        )
        self.optimized_config = OPTIMIZED_TRADING_CONFIG.copy()
        # [PORTFOLIO_AUDIT] Log initialization to trace balance source
        log_component_event(
            "[PORTFOLIO_INIT]",
            f"{self.profile_prefix} Trader initialized: "
            f"initial_balance=${initial_balance:.2f}, "
            f"balance=${self.balance:.2f}, "
            f"source=constructor"
        )
        print(
            f"🧠 {self.profile_prefix} Trader configured with curated indicator blueprint"
        )


# ==================== ENHANCED TRADE HISTORY WITH CLEAR HISTORY ====================
# [MODULARIZATION] Moved to app.legacy.history_shim
# Note: This class is now replaced by ComprehensiveTradeHistory but kept for compatibility
from app.legacy.history_shim import EnhancedTradeHistory

# Inject logger into shim since it was a local dependency
def _create_history_shim(data_dir="trade_data"):
    return EnhancedTradeHistory(data_dir=data_dir, log_callback=log_component_event)

# Patch the constructor if needed, or we typically just use the class
# Since EnhancedTradeHistory is a class, we can swap it or subclass it
# But imports are usually "from X import Y", so this name usage is consistent.
# For strict compatibility, we need the __init__ to accept just data_dir arg if that's what callers do.
# The shim's __init__ has default log_callback=None which uses default logger.
# If we want to inject log_component_event, callers need to pass it OR we wrap it.
# However, callers likely do `EnhancedTradeHistory()`.
# To preserve exact behavior, we should monkeypatch the class's default logic or subclass it here.

class EnhancedTradeHistory(EnhancedTradeHistory):
    def __init__(self, data_dir="trade_data"):
         super().__init__(data_dir=data_dir, log_callback=log_component_event)


# ==================== MARKET DATA FUNCTIONS ====================

_binance_market_helper: Optional[BinanceMarketDataHelper] = None


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _ensure_binance_market_helper() -> BinanceMarketDataHelper:
    if _binance_market_helper is None:
        raise RuntimeError("Binance market data helper not initialized yet")
    return _binance_market_helper


def fetch_binance_24hr_ticker(symbol=None, timeout=10):
    """Compatibility wrapper for legacy callers."""
    helper = _ensure_binance_market_helper()
    return helper.fetch_24hr_ticker(symbol=symbol, timeout=timeout)


def get_trending_pairs():
    helper = _ensure_binance_market_helper()
    trending_data = helper.get_trending_pairs()
    return [pair.get("symbol", "") for pair in trending_data if pair.get("symbol")]


def get_real_market_data(symbol):
    helper = _ensure_binance_market_helper()
    return helper.get_real_market_data(symbol)


def get_emergency_predictions(symbol, market_data):
    """Emergency fallback predictions"""
    if not market_data:
        return None
    price_change = market_data.get("change", 0)
    if price_change > 2:
        signal, confidence = "BUY", 0.65
    elif price_change < -2:
        signal, confidence = "SELL", 0.65
    elif price_change > 0:
        signal, confidence = "BUY", 0.55
    elif price_change < 0:
        signal, confidence = "SELL", 0.55
    else:
        signal, confidence = "HOLD", 0.5
    return {
        "emergency_model": {
            "signal": signal,
            "confidence": confidence,
            "prediction": 2 if signal == "BUY" else 0,
        }
    }


def _detect_testnet_exchange_session() -> bool:
    try:
        for trader_name in ("ultimate_trader", "optimized_trader"):
            trader = globals().get(trader_name)
            if not trader:
                continue
            for attr in ("real_trader", "futures_trader"):
                client = getattr(trader, attr, None)
                if client and getattr(client, "testnet", False):
                    return True
    except Exception:
        pass
    return False


def _iter_active_traders_for_binance_hooks():
    """Return active trader instances for applying Binance API hooks.

    In multi-user auto-trading mode, MarketDataService maintains per-user trader
    instances. We prefer those so that API failure/cooldown flags remain
    user-scoped. Fall back to the global singleton traders otherwise.
    """
    service = globals().get("market_data_service")
    user_traders = getattr(service, "_user_traders", None)
    seen: set[int] = set()
    resolved = []
    if isinstance(user_traders, dict) and user_traders:
        for pair in user_traders.values():
            if not pair:
                continue
            for trader in pair:
                if trader is None:
                    continue
                ident = id(trader)
                if ident in seen:
                    continue
                seen.add(ident)
                resolved.append(trader)
        return resolved

    for trader_name in ("ultimate_trader", "optimized_trader"):
        trader = globals().get(trader_name)
        if trader is None:
            continue
        ident = id(trader)
        if ident in seen:
            continue
        seen.add(ident)
        resolved.append(trader)
    return resolved


def _binance_api_success_hook() -> None:
    for trader in _iter_active_traders_for_binance_hooks():
        safety_manager = getattr(trader, "safety_manager", None)
        clear_api_failures = getattr(safety_manager, "clear_api_failures", None)
        if callable(clear_api_failures):
            try:
                clear_api_failures()
            except Exception:
                continue


def _binance_api_failure_hook(message: str) -> None:
    for trader in _iter_active_traders_for_binance_hooks():
        safety_manager = getattr(trader, "safety_manager", None)
        log_api_failure = getattr(safety_manager, "log_api_failure", None)
        if callable(log_api_failure):
            try:
                log_api_failure(message)
            except Exception:
                continue


# ==================== CONSTANTS AND HELPERS ====================
BINANCE_WARNING_COOLDOWN = 180.0  # seconds
_TALIB_IMPORT_ERROR = None  # Track TA-Lib import errors
MISSING_TALIB_FUNCTIONS = []  # Track missing TA-Lib functions
OPTIMIZED_TRADING_CONFIG = TRADING_CONFIG.copy()  # Optimized trading configuration

# Health check configuration
HEALTH_CHECK_CONFIG = {
    "min_total_return_pct": 5.0,
    "min_sharpe_ratio": 0.5,
    "max_drawdown_pct": 20.0,
    "report_path": "health_report.json",
}

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float safely."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def _detect_testnet_exchange_session() -> bool:
    """Detect if testnet mode is enabled."""
    return TRADING_CONFIG.get("testnet", True)

def _binance_api_success_hook():
    """Hook called on successful Binance API calls."""
    pass

def _binance_api_failure_hook(message: str):
    """Hook called on failed Binance API calls."""
    pass

# ==================== BINANCE MARKET HELPER ====================
_binance_market_helper: Optional[BinanceMarketDataHelper] = None

def _initialize_binance_market_helper() -> None:
    global _binance_market_helper
    _binance_market_helper = BinanceMarketDataHelper(
        bot_logger=bot_logger,
        safe_float=_safe_float,
        testnet_detector=_detect_testnet_exchange_session,
        binance_log_manager=binance_log_manager,
        warning_cooldown=BINANCE_WARNING_COOLDOWN,
        api_success_hooks=[_binance_api_success_hook],
        api_failure_hooks=[_binance_api_failure_hook],
    )


# ==================== INITIALIZE ULTIMATE COMPONENTS ====================
ml_services = create_ml_services(
    ultimate_factory=UltimateMLTrainingSystem,
    optimized_factory=OptimizedMLTrainingSystem,
    futures_factory=FuturesMLTrainingSystem,
)


# Trading services initialization moved after persistence runtime setup
# to ensure bot_logger and other dependencies are available
trading_runtime = None
trading_services = None
trade_history = None
ultimate_trader = None
optimized_trader = None
parallel_engine = None

ultimate_ml_system = ml_services.ultimate_ml_system
optimized_ml_system = ml_services.optimized_ml_system
futures_ml_system = ml_services.futures_ml_system


# get_user_trader will be assigned after trading_runtime is initialized
get_user_trader = None

# Initialize real manager
indicator_selection_manager = IndicatorSelectionManager()

# Helper Functions for Indicators (Delegated to Manager)
def get_all_indicator_selections():
    return indicator_selection_manager.snapshot()

def get_indicator_selection(profile_key: str):
    return indicator_selection_manager.get_selection(profile_key)

def set_indicator_selection(profile_key: str, indicator: str, enabled: bool):
    current = set(indicator_selection_manager.get_selection(profile_key))
    if enabled:
        current.add(indicator)
    else:
        current.discard(indicator)
    indicator_selection_manager.set_selection(profile_key, current)

def refresh_indicator_dashboard_state():
    """Placeholder - overwritten by runtime services."""
    pass

strategy_manager = StrategyManager()

indicator_snapshot = get_all_indicator_selections()

futures_dashboard_state = {
    "enabled": TRADING_CONFIG.get("futures_enabled", False),
    "last_update": None,
    "market_data": {},
    "predictions": {},
    "signals": {},
    "recommended_leverage": {},
    "position_sizing": {},
    "positions": {},
    "portfolio": {
        "balance": float(TRADING_CONFIG.get("futures_initial_balance", 1000)),
        "equity": float(TRADING_CONFIG.get("futures_initial_balance", 1000)),
        "used_margin": 0.0,
        "available_margin": float(TRADING_CONFIG.get("futures_initial_balance", 1000)),
        "unrealized_pnl": 0.0,
        "positions": [],
    },
    "metrics": {
        "average_funding_rate": 0.0,
        "high_risk_symbols": [],
        "funding_alerts": [],
    },
    "config": {},
    "indicator_selection": indicator_snapshot.get("futures", []),
}

futures_data_lock = threading.Lock()

futures_dashboard_state["config"] = dict(
    futures_ml_system.futures_module.futures_config
)

_default_futures_symbol = TRADING_CONFIG.get("futures_selected_symbol")
if _default_futures_symbol and _default_futures_symbol not in FUTURES_SYMBOLS:
    _default_futures_symbol = FUTURES_SYMBOLS[0] if FUTURES_SYMBOLS else None
    TRADING_CONFIG["futures_selected_symbol"] = _default_futures_symbol

futures_manual_service = FuturesManualService(
    trading_config=TRADING_CONFIG,
    initial_selected_symbol=_default_futures_symbol,
    futures_symbols_provider=lambda: list(FUTURES_SYMBOLS),
    top_symbols_provider=lambda: list(TOP_SYMBOLS),
    dashboard_data_provider=lambda: globals().get("dashboard_data") or {},
    safe_float=_safe_float,
)
futures_manual_lock = futures_manual_service.lock
futures_manual_settings = futures_manual_service.settings


def _ensure_futures_manual_defaults(update_dashboard=False):
    return futures_manual_service.ensure_defaults(update_dashboard=update_dashboard)

# Start the service explicitly
futures_manual_service.start()


def _get_futures_manual_settings():
    return futures_manual_service.ensure_defaults(update_dashboard=False)


def _set_futures_manual_settings(settings):
    futures_manual_service.apply_restored_settings(settings)


def _handle_manual_futures_trading(symbol, market_data, prediction, sizing):
    try:
        futures_manual_service.handle_manual_trading(
            symbol,
            market_data,
            prediction,
            sizing,
            ultimate_trader,
        )
    except Exception as exc:
        print(f"❌ Manual futures trading error for {symbol}: {exc}")


def _ensure_logger_handlers_open(logger):
    try:
        handlers = list(getattr(logger, "handlers", []))
    except Exception:
        return
    for handler in handlers:
        stream = getattr(handler, "stream", None)
        if stream is not None and getattr(stream, "closed", False):
            try:
                logger.removeHandler(handler)
            except Exception:
                continue


def _disable_logger(logger):
    try:
        if logger is None:
            return
        logger.disabled = True
    except Exception:
        pass


persistence_runtime = build_persistence_runtime(
    market_cap_weights_provider=lambda: MARKET_CAP_WEIGHTS,
    futures_settings_getter=_get_futures_manual_settings,
    futures_settings_setter=_set_futures_manual_settings,
    ultimate_trader=ultimate_trader,
    optimized_trader=optimized_trader,
    futures_manual_lock=futures_manual_lock,
    futures_manual_settings=futures_manual_settings,
    coerce_bool=_coerce_bool,
    log_event=log_component_event,
    log_debug=log_component_debug,
    logger_factory=setup_application_logging,
    bot_profile=BOT_PROFILE,
)
persistence_manager = persistence_runtime.persistence_manager
persistence_scheduler = persistence_runtime.persistence_scheduler
bot_logger = persistence_runtime.bot_logger
binance_credentials_store = persistence_runtime.binance_credentials_store
binance_credential_service = persistence_runtime.binance_credential_service
binance_log_manager = persistence_runtime.binance_log_manager
live_portfolio_scheduler = None
_initialize_binance_market_helper()

if _TALIB_IMPORT_ERROR is not None:
    bot_logger.warning(
        "TA-Lib import failed; using fallback indicator implementations (error: %s)",
        _TALIB_IMPORT_ERROR,
    )
elif MISSING_TALIB_FUNCTIONS:
    bot_logger.warning(
        "TA-Lib missing functions %s; using fallback implementations",
        ", ".join(sorted(set(MISSING_TALIB_FUNCTIONS))),
    )
backtest_manager = BacktestManager(
    symbol_normalizer=_normalize_symbol,
    active_universe_provider=lambda: get_active_trading_universe(),
    top_symbols_provider=lambda: list(TOP_SYMBOLS),
    resolve_profile_path=resolve_profile_path,
    ultimate_system_factory=UltimateMLTrainingSystem,
    optimized_system_factory=OptimizedMLTrainingSystem,
    ultimate_live_system=ultimate_ml_system,
    optimized_live_system=optimized_ml_system,
)

# Initialize trading services now that bot_logger is available
trading_runtime = create_trading_services(
    trade_history_factory=lambda: ComprehensiveTradeHistory(
        log_callback=log_component_event
    ),
    ultimate_trader_factory=lambda: UltimateAIAutoTrader(initial_balance=1000),
    optimized_trader_factory=lambda: OptimizedAIAutoTrader(initial_balance=1000),
    parallel_engine_factory=ParallelPredictionEngine,
)

attach_trading_ml_dependencies(trading_runtime, ml_services)

trading_services = trading_runtime
trade_history = trading_services.trade_history
ultimate_trader = trading_services.ultimate_trader
optimized_trader = trading_services.optimized_trader
parallel_engine = trading_services.parallel_engine

# Assign get_user_trader now that trading_runtime is available
if hasattr(trading_runtime, 'get_user_trader'):
    get_user_trader = trading_runtime.get_user_trader


binance_credential_service.initialize_all()
binance_credential_snapshot = persistence_runtime.snapshot_credentials(
    include_connection=True,
    include_logs=True,
)

health_data_lock = threading.Lock()
health_report_service = None

# Ultimate dashboard data
dashboard_data = {
    "market_data": {},
    "ml_predictions": {},
    "ai_signals": {},
    "portfolio": {},
    "optimized_ml_predictions": {},
    "optimized_ai_signals": {},
    "optimized_portfolio": {},
    "trending_pairs": [],
    "ensemble_predictions": {},
    "optimized_ensemble_predictions": {},
    "performance": {
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "total_pnl": 0,
        "win_rate": 0,
        "sharpe_ratio": 0,
        "max_drawdown": 0,
    },
    "system_status": {
        "trading_enabled": False,
        "last_trade": None,
        "models_loaded": False,
        "ml_system_available": True,
        "paper_trading": True,
        "total_symbols": len(get_all_known_symbols()),
        "active_symbols": len(get_active_trading_universe()),
        "performance_tracking": True,
        "models_training": False,
        "total_indicators": len(BEST_INDICATORS),
        "indicators_used": 0,
        "bot_efficiency": 0,
        "learning_cycles": 0,
        "ensemble_active": True,
        "market_regime": "NEUTRAL",
        "risk_adjustment": 1.0,
        "professional_mode": True,
        "parallel_processing": True,
        "advanced_stop_loss": True,
        "adaptive_risk_management": True,
        "periodic_rebuilding": True,
        "continuous_training": False,  # DEPRECATED: Use BrainService/RQ
        "market_stress": 0.0,
        "risk_profile": "moderate",
        "crt_module_active": "CRT"
        in indicator_snapshot.get("ultimate", []),  # NEW: CRT module status
        "ict_module_active": "ICT" in indicator_snapshot.get("ultimate", []),
        "smc_module_active": "SMC" in indicator_snapshot.get("ultimate", []),
        "comprehensive_history": True,  # NEW: Comprehensive history status
        "persistence_enabled": True,  # NEW: Persistence status
        "futures_enabled": TRADING_CONFIG.get("futures_enabled", False),
        "real_trading_ready": False,
        "futures_trading_ready": False,
        "futures_manual_auto_trade": TRADING_CONFIG.get(
            "futures_manual_auto_trade", False
        ),
    },
    "optimized_system_status": {
        "trading_enabled": False,
        "models_loaded": False,
        "models_training": False,
        "total_indicators": len(BEST_INDICATORS),
        "indicators_used": 0,
        "bot_efficiency": 0,
        "learning_cycles": 0,
        "market_regime": "NEUTRAL",
        "risk_adjustment": 1.0,
        "market_stress": 0.0,
        "risk_profile": "moderate",
        "ensemble_active": False,
        "crt_module_active": "CRT" in indicator_snapshot.get("optimized", []),
        "ict_module_active": "ICT" in indicator_snapshot.get("optimized", []),
        "smc_module_active": "SMC" in indicator_snapshot.get("optimized", []),
        "paper_trading": True,
        "real_trading_ready": False,
    },
    "last_update": time.time(),
    "optimized_last_update": time.time(),
    "crt_signals": {},  # NEW: CRT signals data
    "optimized_crt_signals": {},
    "qfm_signals": {},
    "optimized_qfm_signals": {},
    "trade_statistics": {},  # NEW: Trade statistics
    "optimized_trade_statistics": {},
    "binance_credentials": binance_credential_snapshot,
    "binance_logs": binance_credential_snapshot.get("logs", []),
    "optimized_performance": {},
    "safety_status": {},
    "optimized_safety_status": {},
    "real_trading_status": {},
    "optimized_real_trading_status": {},
    "ml_telemetry": {
        "ultimate": {"summary": {}, "models": [], "history": []},
        "optimized": {"summary": {}, "models": [], "history": []},
    },
    "journal_events": [],
    "backtest_results": {},
    "backtest_jobs": {"active": None, "history": []},
    "health_report": {
        "status": "unknown",
        "last_refresh": None,
        "generated_at": None,
        "thresholds": {
            "min_total_return_pct": HEALTH_CHECK_CONFIG["min_total_return_pct"],
            "min_sharpe_ratio": HEALTH_CHECK_CONFIG["min_sharpe_ratio"],
            "max_drawdown_pct": HEALTH_CHECK_CONFIG["max_drawdown_pct"],
        },
        "aggregate": {},
        "symbols": [],
        "breaches": [],
        "top_by_return": [],
        "top_by_sharpe": [],
        "errors": [],
        "source": HEALTH_CHECK_CONFIG["report_path"],
    },
    "futures_dashboard": futures_dashboard_state,
    "futures_manual": futures_manual_settings,
    "indicator_selections": indicator_snapshot,
}

attach_dashboard_data(dashboard_data)

persistence_runtime.attach_dashboard_data(lambda: dashboard_data)

dashboard_data["system_status"][
    "futures_manual_auto_trade"
] = futures_manual_settings.get("auto_trade_enabled", False)
dashboard_data["system_status"]["futures_trading_ready"] = bool(
    getattr(ultimate_trader, "futures_trading_enabled", False)
)

# Auto-enable futures trading if environment variables are set
if TRADING_CONFIG.get("futures_enabled", False):
    final_hammer = os.getenv("FINAL_HAMMER", "false").lower() in ("1", "true", "yes")
    if final_hammer:
        try:
            print(
                "🔄 Auto-enabling futures trading based on environment configuration..."
            )
            ultimate_trader.futures_trading_enabled = True
            optimized_trader.futures_trading_enabled = True
            dashboard_data["system_status"]["futures_trading_enabled"] = True
            dashboard_data["system_status"]["futures_trading_ready"] = True
            dashboard_data["optimized_system_status"]["futures_trading_enabled"] = True
            dashboard_data["optimized_system_status"]["futures_trading_ready"] = True
            print("✅ Futures trading auto-enabled successfully")
        except Exception as exc:
            print(f"⚠️ Failed to auto-enable futures trading: {exc}")
    else:
        print(
            "⚠️ Futures trading not auto-enabled: FINAL_HAMMER environment variable not set"
        )

# Add circuit breaker status to system status
if hasattr(ultimate_trader, "get_circuit_breaker_status"):
    dashboard_data["system_status"][
        "circuit_breaker"
    ] = ultimate_trader.get_circuit_breaker_status()
else:
    dashboard_data["system_status"]["circuit_breaker"] = {
        "state": "UNKNOWN",
        "is_open": False,
    }

health_report_service = HealthReportService(
    config=HEALTH_CHECK_CONFIG,
    project_root=PROJECT_ROOT,
    dashboard_data=dashboard_data,
    summary_evaluator=evaluate_health_payload,
    lock=health_data_lock,
)

service_runtime = build_service_runtime(
    dashboard_data=dashboard_data,
    indicator_selection_manager=indicator_selection_manager,
    trading_config=TRADING_CONFIG,
    ultimate_trader=ultimate_trader,
    optimized_trader=optimized_trader,
    ultimate_ml_system=ultimate_ml_system,
    optimized_ml_system=optimized_ml_system,
    futures_ml_system=futures_ml_system,
    parallel_engine=parallel_engine,
    futures_manual_settings=futures_manual_settings,
    binance_credential_service=binance_credential_service,
    get_active_trading_universe=get_active_trading_universe,
    get_real_market_data=get_real_market_data,
    get_trending_pairs=get_trending_pairs,
    refresh_symbol_counters=refresh_symbol_counters,
    handle_manual_futures_trading=_handle_manual_futures_trading,
    futures_dashboard_state=futures_dashboard_state,
    futures_symbols=FUTURES_SYMBOLS,
    futures_data_lock=futures_data_lock,
    socketio=socketio,
    safe_float=_safe_float,
    bot_logger=bot_logger,
    persistence_manager=persistence_manager,
    symbols_for_persistence=get_active_trading_universe(),
    auto_user_id_provider=lambda: sorted(
        set(_get_auto_user_ids_from_db())
        & set(getattr(binance_credentials_store, "list_user_ids", lambda: [])() or [])
    )
    or sorted(_get_auto_user_ids_from_db())
    or sorted(getattr(binance_credentials_store, "list_user_ids", lambda: [])() or []),
)

historical_data = service_runtime.historical_data
refresh_indicator_dashboard_state = service_runtime.refresh_indicator_dashboard_state
market_data_service = service_runtime.market_data_service
futures_market_data_service = service_runtime.futures_market_data_service
futures_safety_service = getattr(service_runtime, "futures_safety_service", None)
realtime_update_service = service_runtime.realtime_update_service
model_training_worker = service_runtime.model_training_worker
self_improvement_worker = service_runtime.self_improvement_worker

refresh_indicator_dashboard_state()


# ==================== GRACEFUL SHUTDOWN HANDLING ====================
def _persist_multiuser_states_on_shutdown() -> int:
    """Persist user-scoped trader state when multi-user auto trading is active."""
    service = globals().get("market_data_service")
    user_traders = getattr(service, "_user_traders", None)
    if not isinstance(user_traders, dict) or not user_traders:
        return 0

    saved = 0
    profile_name = getattr(service, "_user_profile_name", None)
    for user_id, traders in list(user_traders.items()):
        if not traders or len(traders) < 1:
            continue
        user_ultimate = traders[0]
        try:
            profile = (
                str(profile_name(int(user_id)))
                if callable(profile_name)
                else f"user_{int(user_id)}"
            )

            """
            # PHASE 5: DISABLED - State is in DB
            persistence_manager.save_complete_state(
                user_ultimate,
                ultimate_ml_system,
                TRADING_CONFIG,
                TOP_SYMBOLS,
                historical_data,
                profile=profile,
            )
            """
            saved += 1
        except Exception:
            continue
    return saved


def graceful_shutdown():
    """Save state on application shutdown"""
    print("\n🛑 Shutdown detected - saving bot state...")
    _ensure_logger_handlers_open(bot_logger)
    _disable_logger(bot_logger)
    try:
        background_task_manager.stop_background_tasks()
    except Exception as exc:
        print(f"⚠️ Failed to stop background tasks cleanly: {exc}")
    try:
        background_task_manager.stop_live_portfolio_updates()
    except Exception as exc:
        print(f"⚠️ Failed to stop live portfolio scheduler cleanly: {exc}")
    _ensure_logger_handlers_open(bot_logger)
    saved_users = _persist_multiuser_states_on_shutdown()
    if saved_users <= 0:
        persistence_scheduler.manual_save(
            ultimate_trader,
            ultimate_ml_system,
            TRADING_CONFIG,
            TOP_SYMBOLS,
            historical_data,
        )
    print("✅ Bot state saved. Goodbye!")


# Register shutdown handler
atexit.register(graceful_shutdown)

# Global shutdown flag
shutdown_requested = False


def signal_handler(signum, frame):
    """Handle termination signals"""
    global shutdown_requested
    print(f"\n📡 Received signal {signum} - initiating graceful shutdown...")
    shutdown_requested = True


# Signal handlers will be registered after initialization to prevent premature shutdown
# signal.signal(signal.SIGINT, signal_handler)
# signal.signal(signal.SIGTERM, signal_handler)


# ==================== AUTHENTICATION TEMPLATES ====================
# ==================== FLASK ROUTES ====================
# ==================== USER PORTFOLIO MANAGEMENT ====================
def record_user_trade(
    user_id,
    symbol,
    side,
    quantity,
    price,
    trade_type="manual_spot",
    signal_source=None,
    confidence_score=None,
    market_type="SPOT",
    profile="OPTIMIZED",
):
    """Record a user trade and update portfolio"""
    context_manager = None
    try:
        # [PERSISTENCE_FIX] Create Flask app context if not present (for background threads)
        from flask import has_app_context
        if not has_app_context():
            try:
                from app import create_app
                app = create_app()
                context_manager = app.app_context()
                context_manager.__enter__()
            except Exception as ctx_err:
                print(f"[TRADE_HISTORY] Failed to create app context: {ctx_err}")
                return False

        # [PERSISTENCE_FIX] Ensure user_id is UUID and numeric types are Python natives
        import uuid as uuid_lib
        
        # Convert user_id to UUID if needed
        if isinstance(user_id, int):
            # Legacy int - need to lookup user by int (shouldn't happen with new schema)
            from app.models import User
            user = User.query.first()
            if user:
                resolved_user_id = user.id
            else:
                print(f"[TRADE_HISTORY] No user found in DB to resolve int user_id")
                return False
        elif isinstance(user_id, uuid_lib.UUID):
            resolved_user_id = user_id
        elif isinstance(user_id, str):
            try:
                resolved_user_id = uuid_lib.UUID(user_id)
            except ValueError:
                # Not a valid UUID string - lookup first user
                from app.models import User
                user = User.query.first()
                if user:
                    resolved_user_id = user.id
                else:
                    print(f"[TRADE_HISTORY] Cannot resolve user_id={user_id}")
                    return False
        else:
            resolved_user_id = user_id

        # Verify the user exists in DB, if not fall back to first user
        from app.models import User
        user_exists = User.query.filter_by(id=resolved_user_id).first()
        if not user_exists:
            print(f"[TRADE_HISTORY] UUID {resolved_user_id} not found in DB, using first user")
            first_user = User.query.first()
            if first_user:
                resolved_user_id = first_user.id
            else:
                print(f"[TRADE_HISTORY] No users in database, cannot record trade")
                return False

        # Convert numpy types to Python natives for Postgres
        def to_python_float(val):
            if val is None:
                return None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        # Create trade record with proper types
        trade = UserTrade(
            user_id=resolved_user_id,
            symbol=symbol,
            trade_type=trade_type,
            side=side,
            quantity=to_python_float(quantity),
            entry_price=to_python_float(price),
            status="open" if side == "BUY" else "closed",
            signal_source=signal_source,
            confidence_score=to_python_float(confidence_score),
            market_type=market_type,
            profile=profile,
        )
        db.session.add(trade)

        # Update or create user portfolio
        portfolio = UserPortfolio.query.filter_by(user_id=resolved_user_id).first()
        if not portfolio:
            portfolio = UserPortfolio(user_id=resolved_user_id)
            db.session.add(portfolio)

        # Update portfolio based on trade
        if side == "BUY":
            # Calculate cost
            cost = quantity * price
            # Ensure balance is not None before comparison
            if portfolio.available_balance is None:
                portfolio.available_balance = 10000.0  # Default starting balance for paper trading
            
            if portfolio.available_balance >= cost:
                portfolio.available_balance -= cost
                # Update open positions
                positions = portfolio.open_positions or {}
                if symbol not in positions:
                    positions[symbol] = {
                        "quantity": 0,
                        "entry_price": 0,
                        "current_pnl": 0,
                    }
                # Simple average price calculation
                current_qty = positions[symbol]["quantity"]
                current_avg = positions[symbol]["entry_price"]
                new_qty = current_qty + quantity
                new_avg = (
                    ((current_qty * current_avg) + (quantity * price)) / new_qty
                    if new_qty > 0
                    else 0
                )
                positions[symbol]["quantity"] = new_qty
                positions[symbol]["entry_price"] = new_avg
                portfolio.open_positions = positions
            else:
                db.session.rollback()
                return False
        elif side == "SELL":
            # Handle sell logic - simplified for now
            positions = portfolio.open_positions or {}
            if symbol in positions and positions[symbol]["quantity"] >= quantity:
                # Calculate P&L
                entry_price = positions[symbol]["entry_price"]
                pnl = (price - entry_price) * quantity
                portfolio.total_profit_loss += pnl
                portfolio.available_balance += quantity * price
                # Update position
                positions[symbol]["quantity"] -= quantity
                if positions[symbol]["quantity"] <= 0:
                    del positions[symbol]
                portfolio.open_positions = positions
                # Update trade with exit info
                trade.exit_price = price
                trade.pnl = pnl
                trade.status = "closed"
            else:
                db.session.rollback()
                return False

        # Update totals
        portfolio.total_balance = portfolio.available_balance + sum(
            pos["quantity"] * pos["entry_price"] for pos in positions.values()  # type: ignore
        )
        portfolio.updated_at = datetime.utcnow()

        db.session.commit()
        return True

    except Exception as e:
        db.session.rollback()
        print(f"Error recording user trade: {e}")
        return False
    finally:
        # Clean up app context if we created one
        if context_manager:
            context_manager.__exit__(None, None, None)


def update_portfolio_daily_pnl(user_id=None):
    """Update UserPortfolio daily_pnl from trader daily_pnl accumulation"""
    def _resolve_user_traders(user_id_value: int):
        from typing import Any, Optional, Tuple

        service: Any = globals().get("market_data_service")
        getter = getattr(service, "_get_or_create_user_traders", None)
        if not callable(getter):
            return None
        try:
            res: Any = getter(int(user_id_value))
        except Exception:
            return None

        if isinstance(res, tuple) and len(res) == 2:
            return res  # type: ignore[return-value]
        if isinstance(res, list) and len(res) == 2:
            return (res[0], res[1])
        return None

    try:
        # Get all users or specific user
        if user_id:
            users = User.query.filter_by(id=user_id).all()
        else:
            users = User.query.all()

        updated_users = []

        for user in users:
            try:
                # Get user's current portfolio daily_pnl
                user_portfolio = UserPortfolio.query.filter_by(user_id=user.id).first()
                if not user_portfolio:
                    continue

                traders = _resolve_user_traders(int(user.id))
                if traders is None:
                    # Without user-scoped traders, we cannot safely compute per-user P&L.
                    continue

                ultimate_trader_for_user, optimized_trader_for_user = traders

                # Get trader daily_pnl (sum from both ultimate and optimized traders)
                ultimate_daily_pnl = getattr(ultimate_trader_for_user, "daily_pnl", 0)
                optimized_daily_pnl = getattr(optimized_trader_for_user, "daily_pnl", 0)
                total_daily_pnl = ultimate_daily_pnl + optimized_daily_pnl

                # Update portfolio daily_pnl
                user_portfolio.daily_pnl = total_daily_pnl
                user_portfolio.updated_at = datetime.utcnow()

                updated_users.append(
                    {
                        "user_id": user.id,
                        "username": user.username,
                        "daily_pnl": total_daily_pnl,
                        "ultimate_daily_pnl": ultimate_daily_pnl,
                        "optimized_daily_pnl": optimized_daily_pnl,
                    }
                )

            except Exception as e:
                print(f"Error updating daily P&L for user {user.id}: {e}")
                continue

        db.session.commit()

        return {
            "success": True,
            "updated_users": len(updated_users),
            "user_details": updated_users,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        db.session.rollback()
        print(f"Error updating portfolio daily P&L: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


def update_live_portfolio_pnl(user_id=None):
    """Update live portfolio P&L calculations for all users or specific user"""
    try:
        # Get market data for current prices
        market_data = dashboard_data.get("market_data", {})

        # Query users to update
        if user_id:
            users = User.query.filter_by(id=user_id).all()
        else:
            users = User.query.all()

        updated_users = []

        for user in users:
            try:
                # Get user's portfolio positions
                user_portfolios = UserPortfolio.query.filter_by(user_id=user.id).all()

                total_portfolio_value = 0
                total_pnl = 0
                total_cost_basis = 0

                for position in user_portfolios:
                    symbol = position.symbol
                    quantity = position.quantity or 0

                    if quantity == 0:
                        continue

                    # Get current price from market data or use last known price
                    current_price = None
                    if symbol in market_data:
                        current_price = market_data[symbol].get("price") or market_data[
                            symbol
                        ].get("close")

                    if current_price is None or current_price <= 0:
                        current_price = position.current_price or position.avg_price

                    if current_price and current_price > 0:
                        # Update current price
                        position.current_price = current_price

                        # Calculate P&L for this position
                        cost_basis = quantity * (position.avg_price or 0)
                        current_value = quantity * current_price
                        position_pnl = current_value - cost_basis
                        position_pnl_percent = (
                            (position_pnl / cost_basis * 100) if cost_basis > 0 else 0
                        )

                        # Update position P&L
                        position.pnl = position_pnl
                        position.pnl_percent = position_pnl_percent

                        total_portfolio_value += current_value
                        total_pnl += position_pnl
                        total_cost_basis += cost_basis

                # Update user's total portfolio metrics
                if user_portfolios:
                    # Calculate overall portfolio P&L percentage
                    total_pnl_percent = (
                        (total_pnl / total_cost_basis * 100)
                        if total_cost_basis > 0
                        else 0
                    )

                    # Update portfolio totals
                    for portfolio in user_portfolios:
                        if hasattr(portfolio, "total_balance"):
                            portfolio.total_balance = total_portfolio_value
                        portfolio.updated_at = datetime.utcnow()

                    updated_users.append(
                        {
                            "user_id": user.id,
                            "username": user.username,
                            "total_value": total_portfolio_value,
                            "total_pnl": total_pnl,
                            "total_pnl_percent": total_pnl_percent,
                            "positions_count": len(
                                [
                                    p
                                    for p in user_portfolios
                                    if p.quantity and p.quantity > 0
                                ]
                            ),
                        }
                    )

            except Exception as e:
                print(f"Error updating portfolio for user {user.id}: {e}")
                continue

        # Update daily P&L for all users
        update_portfolio_daily_pnl()

        db.session.commit()

        return {
            "success": True,
            "updated_users": len(updated_users),
            "user_details": updated_users,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        db.session.rollback()
        print(f"Error updating live portfolio P&L: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


background_runtime = build_background_runtime(
    update_callback=update_live_portfolio_pnl,
    bot_logger=bot_logger,
    market_data_service=market_data_service,
    futures_market_data_service=futures_market_data_service,
    futures_safety_service=futures_safety_service,
    realtime_update_service=realtime_update_service,
    persistence_scheduler=persistence_scheduler,
    self_improvement_worker=self_improvement_worker,
    model_training_worker=model_training_worker,
    trading_config=TRADING_CONFIG,
    flask_app=None,
    update_interval_seconds=30,
    tick_interval_seconds=10,
)
live_portfolio_scheduler = background_runtime.live_portfolio_scheduler
background_task_manager = background_runtime.background_task_manager


# ==================== SOCKETIO ENDPOINTS FOR REAL-TIME DASHBOARD ====================
@socketio.on("connect")
def handle_connect():
    """Handle client connection for real-time updates"""
    print(f"Client connected: {request.sid}")  # type: ignore
    emit(
        "connected",
        {"status": "success", "message": "Connected to real-time dashboard"},
    )


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection"""
    print(f"Client disconnected: {request.sid}")  # type: ignore


@socketio.on("subscribe_portfolio")
def handle_portfolio_subscription():
    """Subscribe to real-time portfolio updates"""
    emit(
        "portfolio_update",
        {
            "portfolio": dashboard_data.get("portfolio", {}),
            "user_portfolio": get_user_portfolio_data(
                current_user.id if current_user else None
            ),
            "timestamp": time.time(),
        },
    )


@socketio.on("subscribe_market_data")
def handle_market_data_subscription():
    """Subscribe to real-time market data updates"""
    active_symbols = get_active_trading_universe()
    market_data = {}
    for symbol in active_symbols:
        if symbol in dashboard_data.get("market_data", {}):
            market_data[symbol] = dashboard_data["market_data"][symbol]

    emit("market_data_update", {"market_data": market_data, "timestamp": time.time()})


@socketio.on("subscribe_pnl")
def handle_pnl_subscription():
    """Subscribe to real-time P&L updates"""
    portfolio = dashboard_data.get("portfolio", {})
    pnl_data = {
        "total_pnl": portfolio.get("total_pnl", 0),
        "daily_pnl": portfolio.get("daily_pnl", 0),
        "open_positions_pnl": sum(
            pos.get("pnl", 0) for pos in portfolio.get("positions", [])
        ),
        "timestamp": time.time(),
    }
    emit("pnl_update", pnl_data)


@socketio.on("subscribe_performance")
def handle_performance_subscription():
    """Subscribe to real-time performance metrics"""
    performance = dashboard_data.get("performance", {})
    emit("performance_update", {"performance": performance, "timestamp": time.time()})


def get_user_portfolio_data(user_id):
    """Get user-specific portfolio data for real-time updates"""
    if not user_id:
        return {}

    try:
        # Get user portfolio from database
        user_portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
        if not user_portfolio:
            return {}

        # Get recent trades
        recent_trades = (
            UserTrade.query.filter_by(user_id=user_id)
            .order_by(UserTrade.timestamp.desc())
            .limit(10)
            .all()
        )
        trades_data = []
        for trade in recent_trades:
            trades_data.append(
                {
                    "id": trade.id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "entry_price": trade.entry_price,
                    "pnl": trade.pnl,
                    "status": trade.status,
                    "timestamp": trade.timestamp.isoformat()
                    if trade.timestamp
                    else None,
                }
            )

        return {
            "total_balance": user_portfolio.total_balance,
            "available_balance": user_portfolio.available_balance,
            "total_pnl": user_portfolio.total_profit_loss,
            "daily_pnl": user_portfolio.daily_pnl,
            "open_positions": user_portfolio.open_positions or {},
            "recent_trades": trades_data,
            "last_updated": user_portfolio.updated_at.isoformat()
            if user_portfolio.updated_at
            else None,
        }
    except Exception as e:
        print(f"Error getting user portfolio data: {e}")
        return {}


# ==================== POLLING FALLBACK ENDPOINTS ====================
# REST API endpoints for browsers that don't support WebSocket


# ==================== INITIALIZE ULTIMATE SYSTEM WITH PERSISTENCE ====================
def initialize_ultimate_system():
    """Initialize the complete ultimate trading system with persistence."""
    context = None
    flask_app = globals().get("app")
    if flask_app is not None:
        context = flask_app.extensions.get("ai_bot_context")
    if context is None:
        context = _build_ai_bot_context()
    initialize_runtime_from_context(context)


# ==================== DASHBOARD TEMPLATE ====================
# Template moved to app/templates/dashboard.html


def _build_ai_bot_context():
    indicator_profiles = indicator_selection_manager.profiles()
    
    # Resolve system user ID for global bot credential loading
    system_user_id = TRADING_CONFIG.get("system_trade_user_id")

    # Construct persistence runtime
    # We construct it *before* building managers that depend on logging/persistence
    persistence_runtime = build_persistence_runtime(
        market_cap_weights_provider=market_data_service.get_market_cap_weights,
        futures_settings_getter=futures_manual_service.get_settings,
        futures_settings_setter=futures_manual_service.update_settings,
        ultimate_trader=ultimate_trader,
        optimized_trader=optimized_trader,
        futures_manual_lock=futures_manual_lock,
        futures_manual_settings=futures_manual_settings,
        coerce_bool=_coerce_bool,
        log_event=log_component_event,
        log_debug=log_component_debug,
        logger_factory=setup_logger,
        bot_profile=BOT_PROFILE,
        system_trade_user_id=system_user_id,
    )
    
    # Auto-Discovery Fallback: 
    # If no system user ID was configured, but credentials exist for SOME user, 
    # try to auto-discover a valid user ID to prevent "Real Trader NOT READY" errors.
    if not system_user_id:
        try:
            available_users = persistence_runtime.binance_credentials_store.list_user_ids()
            if available_users:
                # Pick the first one (usually the Admin/First User)
                discovered_id = available_users[0]
                print(f"⚠️ System Trade User ID not configured. Auto-discovered fallback user: {discovered_id}")
                
                # Re-initialize the credential service with this ID
                persistence_runtime.binance_credential_service.initialize_all(user_id=discovered_id)
        except Exception as e:
            print(f"⚠️ Failed to auto-discover system user credentials: {e}")

    persistence_manager = persistence_runtime.persistence_manager # Keep local ref for payload

    return build_ai_bot_context_payload(
        dashboard_data=dashboard_data,
        health_data_lock=health_data_lock,
        health_report_service=health_report_service,
        indicator_signal_options=INDICATOR_SIGNAL_OPTIONS,
        indicator_profiles=indicator_profiles,
        get_indicator_selection=get_indicator_selection,
        get_all_indicator_selections=get_all_indicator_selections,
        set_indicator_selection=set_indicator_selection,
        refresh_indicator_dashboard_state=refresh_indicator_dashboard_state,
        ultimate_trader=ultimate_trader,
        optimized_trader=optimized_trader,
        ultimate_ml_system=ultimate_ml_system,
        optimized_ml_system=optimized_ml_system,
        futures_ml_system=futures_ml_system,
        parallel_engine=parallel_engine,
        strategy_manager=strategy_manager,
        backtest_manager=backtest_manager,
        get_active_trading_universe=get_active_trading_universe,
        get_real_market_data=get_real_market_data,
        get_trending_pairs=get_trending_pairs,
        get_user_trader=get_user_trader,
        get_user_portfolio_data=get_user_portfolio_data,
        update_live_portfolio_pnl=update_live_portfolio_pnl,
        trade_history=trade_history,
        apply_binance_credentials=binance_credential_service.apply_credentials,
        get_binance_credential_status=binance_credential_service.get_status,
        binance_credentials_store=binance_credentials_store,
        binance_credential_service=binance_credential_service,
        binance_log_manager=binance_log_manager,
        futures_dashboard_state=futures_dashboard_state,
        futures_manual_service=futures_manual_service,
        futures_manual_settings=futures_manual_settings,
        futures_manual_lock=futures_manual_lock,
        futures_data_lock=futures_data_lock,
        futures_symbols=FUTURES_SYMBOLS,
        ensure_futures_manual_defaults=_ensure_futures_manual_defaults,
        trading_config=TRADING_CONFIG,
        coerce_bool=_coerce_bool,
        qfm_engine=getattr(ultimate_ml_system, "qfm_engine", None),
        persistence_manager=persistence_manager,
        persistence_scheduler=persistence_scheduler,
        persistence_runtime=persistence_runtime,
        background_runtime=background_runtime,
        background_task_manager=background_task_manager,
        service_runtime=service_runtime,
        realtime_update_service=realtime_update_service,
        market_data_service=market_data_service,
        futures_market_data_service=futures_market_data_service,
        live_portfolio_scheduler=live_portfolio_scheduler,
        historical_data=historical_data,
        top_symbols=TOP_SYMBOLS,
        disabled_symbols=DISABLED_SYMBOLS,  # type: ignore
        get_all_known_symbols=get_all_known_symbols,
        get_disabled_symbols=get_disabled_symbols,
        refresh_symbol_counters=refresh_symbol_counters,
        clear_symbol_from_dashboard=clear_symbol_from_dashboard,
        is_symbol_disabled=is_symbol_disabled,
        disable_symbol=disable_symbol,
        enable_symbol=enable_symbol,
        save_symbol_state=save_symbol_state,
        normalize_symbol=_normalize_symbol,
        signal_handler=signal_handler,
        version_label=AI_BOT_VERSION,
    )


def register_ai_bot_context(flask_app=None, force=False):
    """Attach the AI bot runtime context to the provided Flask app."""
    flask_app = flask_app or app
    if flask_app is None:
        raise RuntimeError(
            "Flask application instance is required to register ai_bot_context"
        )

    new_context = _build_ai_bot_context()
    existing = flask_app.extensions.get("ai_bot_context")
    if existing and not force:
        existing.update(new_context)
        context = existing
    else:
        flask_app.extensions["ai_bot_context"] = new_context
        context = new_context

    # Inject app into traders for context-aware operations (like DB sync)
    ult_trader = context.get("ultimate_trader")
    if ult_trader:
        logging.getLogger("ai_trading_bot").warning(f"DEBUG: register_ai_bot_context - Injecting app into ultimate_trader ID={id(ult_trader)}")
        ult_trader.app = flask_app
    else:
        logging.getLogger("ai_trading_bot").warning("DEBUG: register_ai_bot_context - ultimate_trader NOT FOUND in context")
        
    opt_trader = context.get("optimized_trader")
    if opt_trader:
        logging.getLogger("ai_trading_bot").warning(f"DEBUG: register_ai_bot_context - Injecting app into optimized_trader ID={id(opt_trader)}")
        opt_trader.app = flask_app

    scheduler = context.get("live_portfolio_scheduler")
    if scheduler is not None:
        try:
            scheduler.app = flask_app
        except Exception:
            pass
    background_runtime = context.get("background_runtime")
    if background_runtime is not None:
        attach = getattr(background_runtime, "attach_app", None)
        if callable(attach):
            try:
                attach(flask_app)
            except Exception:
                pass
    return context


# Initialize AI bot context for Flask routes (needed for WSGI deployment)
import sys

# During pytest runs or when the module is imported in test contexts, avoid
# performing heavyweight runtime initialization that expects an application
# context. Skip auto-initialization when pytest is detected in the environment
# to prevent side-effects during test collection.
# Also skip when running under Gunicorn/WWSGI (when not __main__)



def initialize_runtime_from_context(context: dict):
    """Initialize global runtime variables from the registered context."""
    global ultimate_trader, ultimate_ml_system, historical_data, background_task_manager
    
    if not context:
        return
        
    ultimate_trader = context.get("ultimate_trader")
    ultimate_ml_system = context.get("ultimate_ml_system")
    historical_data = context.get("historical_data", {})
    bg_runtime = context.get("background_runtime")
    background_task_manager = getattr(bg_runtime, "background_task_manager", None) if bg_runtime else None
    
    if background_task_manager:
        # Determine Role
        bot_role = os.getenv("AI_BOT_ROLE", "api")
        
        if bot_role != "api":
            # Worker Role: Start Everything
            # Start all background services (Market Data, Futures Loop, Realtime Socket)
            # We disable heavy training on startup to prevent slow boot/OOM
            background_task_manager.start_background_tasks(
                start_ultimate_training=False,
                start_optimized_training=False,
                persistence_inputs=None
            )
            print("✅ Background tasks started via runtime initialization (Worker Role)")
        else:
            # API Role: Start only Read-Only services
            background_task_manager.start_api_mode_tasks()


    print("✅ Runtime initialized from context")
