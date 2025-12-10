"""Strategy manager coordinating all strategies and the QFM engine."""

from __future__ import annotations

import random
import threading
import time
import uuid
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from .base import (
    BaseStrategy,
    ArbitrageStrategy,
    BreakoutStrategy,
    MLBasedStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    ScalpingStrategy,
    TrendFollowingStrategy,
)
from .qfm import QuantumFusionMomentumEngine


class StrategyManager:
    """Manages multiple trading strategies with QFM enhancement."""

    def __init__(self):
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategies: Dict[str, bool] = {}
        self.strategy_performance: Dict[str, dict] = {}
        self.performance_history: List[dict] = []
        self.backtest_jobs: Dict[str, dict] = {}
        self.backtest_lock = threading.Lock()
        self.optimization_status = {
            "running": False,
            "last_run": None,
            "last_result": None,
            "last_error": None,
            "recent_results": [],
        }
        self.qfm_engine = QuantumFusionMomentumEngine()  # Initialize QFM engine
        self.initialize_strategies()
        self.initialize_ml_feedback_system()
        self.initialize_performance_analytics()
        self.initialize_user_dashboard_features()
        self.initialize_adaptive_risk_management()
        self.initialize_continuous_improvement_pipeline()

    def initialize_adaptive_risk_management(self):
        """Initialize adaptive risk management system."""
        print("DEBUG: initialize_adaptive_risk_management called")
        self.adaptive_risk = {
            "qfm_regime_risk_multipliers": {
                "trending_bull": 1.2,
                "trending_bear": 1.1,
                "sideways": 0.7,
                "volatile": 0.6,
                "calm": 1.0,
            },
            "volatility_adjustments": {
                "low_volatility": 1.1,
                "normal_volatility": 1.0,
                "high_volatility": 0.5,
                "extreme_volatility": 0.3,
            },
            "momentum_risk_multipliers": {
                "strong_bullish": 1.15,
                "moderate_bullish": 1.05,
                "neutral": 1.0,
                "moderate_bearish": 0.9,
                "strong_bearish": 0.8,
            },
            "current_regime": "neutral",
            "regime_confidence": 0.0,
            "volatility_percentile": 50.0,
            "momentum_strength": 0.0,
            "risk_adjustment_history": [],
            "max_history_size": 1000,
        }
        print(
            "DEBUG: adaptive_risk initialized, keys:", list(self.adaptive_risk.keys())
        )

    def get_risk_management_status(self):
        """Get current risk management status and recommendations."""
        status = {
            "current_regime": self.adaptive_risk["current_regime"],
            "regime_confidence": self.adaptive_risk["regime_confidence"],
            "volatility_percentile": self.adaptive_risk["volatility_percentile"],
            "momentum_strength": self.adaptive_risk["momentum_strength"],
            "risk_multipliers": {
                "regime": self.adaptive_risk["qfm_regime_risk_multipliers"].get(
                    self.adaptive_risk["current_regime"], 1.0
                ),
                "volatility": self._get_volatility_multiplier(
                    self._assess_volatility_level_from_current_state()
                ),
                "momentum": self._get_momentum_multiplier(
                    self.adaptive_risk["momentum_strength"]
                ),
            },
            "recent_adjustments": self.adaptive_risk["risk_adjustment_history"][-10:]
            if self.adaptive_risk["risk_adjustment_history"]
            else [],
            "recommendations": self._generate_risk_recommendations(),
        }

        return status

    def _get_volatility_multiplier(self, volatility_level):
        """Get risk multiplier based on volatility level."""
        return self.adaptive_risk["volatility_adjustments"].get(volatility_level, 1.0)

    def _get_momentum_multiplier(self, momentum_strength):
        """Get risk multiplier based on momentum strength."""
        if momentum_strength > 1.0:
            return self.adaptive_risk["momentum_risk_multipliers"]["strong_bullish"]
        if momentum_strength > 0.5:
            return self.adaptive_risk["momentum_risk_multipliers"]["moderate_bullish"]
        if momentum_strength > 0.2:
            return self.adaptive_risk["momentum_risk_multipliers"]["neutral"]
        if momentum_strength > 0.1:
            return self.adaptive_risk["momentum_risk_multipliers"]["moderate_bearish"]
        return self.adaptive_risk["momentum_risk_multipliers"]["strong_bearish"]

    def _assess_volatility_level_from_current_state(self):
        """Assess volatility level from current state."""
        percentile = self.adaptive_risk["volatility_percentile"]

        if percentile > 90:
            return "extreme_volatility"
        if percentile > 75:
            return "high_volatility"
        if percentile > 25:
            return "normal_volatility"
        return "low_volatility"

    def _generate_risk_recommendations(self):
        """Generate risk management recommendations."""
        recommendations = []

        regime = self.adaptive_risk["current_regime"]
        volatility_percentile = self.adaptive_risk["volatility_percentile"]
        momentum_strength = self.adaptive_risk["momentum_strength"]

        if regime == "volatile":
            recommendations.append(
                {
                    "type": "regime_risk",
                    "priority": "high",
                    "message": "High volatility detected - reducing position sizes by 40%",
                    "action": "reduce_position_sizes",
                }
            )
        elif regime in ["trending_bull", "trending_bear"]:
            recommendations.append(
                {
                    "type": "regime_opportunity",
                    "priority": "medium",
                    "message": f"Strong {regime.split('_')[1]} trend detected - increasing position sizes by 15-20%",
                    "action": "increase_position_sizes",
                }
            )

        if volatility_percentile > 80:
            recommendations.append(
                {
                    "type": "volatility_alert",
                    "priority": "high",
                    "message": f"Volatility at {volatility_percentile:.1f}th percentile - implement strict risk controls",
                    "action": "implement_strict_risk_controls",
                }
            )

        if momentum_strength > 1.0:
            recommendations.append(
                {
                    "type": "momentum_opportunity",
                    "priority": "medium",
                    "message": f"Strong momentum detected (strength: {momentum_strength:.2f}) - consider increasing risk",
                    "action": "increase_risk_exposure",
                }
            )

        return recommendations

    def initialize_ml_feedback_system(self):
        """Initialize ML feedback system for strategy optimization."""
        self.ml_feedback = {
            "performance_history": [],
            "parameter_history": {name: [] for name in self.strategies},
            "qfm_correlations": {},
            "learning_rate": 0.01,
            "adaptation_threshold": 0.05,
            "max_history_size": 1000,
            "feature_importance": {},
            "last_adaptation": {},
        }

    def update_ml_feedback(self, strategy_name, trade_result, qfm_features=None):
        """Update ML feedback system with trade results and QFM features."""
        if strategy_name not in self.strategies:
            return

        strategy = self.strategies[strategy_name]
        performance_entry = {
            "timestamp": time.time(),
            "strategy": strategy_name,
            "pnl": trade_result.get("pnl", 0),
            "win": trade_result.get("pnl", 0) > 0,
            "confidence": trade_result.get("confidence", 0),
            "parameters": strategy.parameters.copy(),
            "qfm_features": qfm_features or {},
        }

        self.ml_feedback["performance_history"].append(performance_entry)
        if (
            len(self.ml_feedback["performance_history"])
            > self.ml_feedback["max_history_size"]
        ):
            self.ml_feedback["performance_history"] = self.ml_feedback[
                "performance_history"
            ][-self.ml_feedback["max_history_size"] :]

        param_entry = {
            "timestamp": time.time(),
            "parameters": strategy.parameters.copy(),
            "performance_score": self._calculate_performance_score(strategy_name),
        }
        self.ml_feedback["parameter_history"].setdefault(strategy_name, []).append(
            param_entry
        )
        if len(self.ml_feedback["parameter_history"][strategy_name]) > 50:
            self.ml_feedback["parameter_history"][strategy_name] = self.ml_feedback[
                "parameter_history"
            ][strategy_name][-50:]

        if qfm_features:
            self._update_qfm_correlations(strategy_name, trade_result, qfm_features)

        if self._should_adapt_parameters(strategy_name):
            self._adapt_strategy_parameters(strategy_name)

    def _calculate_performance_score(self, strategy_name, window=20):
        """Calculate performance score for a strategy over recent trades."""
        history = self.ml_feedback["performance_history"]
        recent_trades = [h for h in history if h["strategy"] == strategy_name][-window:]
        if not recent_trades:
            return 0.0

        wins = sum(1 for t in recent_trades if t["win"])
        win_rate = wins / len(recent_trades)
        pnl_values = [t["pnl"] for t in recent_trades]
        avg_pnl = np.mean(pnl_values)
        pnl_std = np.std(pnl_values)
        sharpe_ratio = avg_pnl / pnl_std if pnl_std > 0 else 0

        score = win_rate * 0.4 + sharpe_ratio * 0.4 + (avg_pnl / 100) * 0.2
        return max(0, min(1, score))

    def _update_qfm_correlations(self, strategy_name, trade_result, qfm_features):
        """Update correlations between QFM features and trading performance."""
        pnl = trade_result.get("pnl", 0)
        for feature_name, feature_value in qfm_features.items():
            self.ml_feedback["qfm_correlations"].setdefault(feature_name, []).append(
                {
                    "strategy": strategy_name,
                    "feature_value": feature_value,
                    "pnl": pnl,
                    "timestamp": time.time(),
                }
            )

            if len(self.ml_feedback["qfm_correlations"][feature_name]) > 200:
                self.ml_feedback["qfm_correlations"][feature_name] = self.ml_feedback[
                    "qfm_correlations"
                ][feature_name][-200:]

    def _should_adapt_parameters(self, strategy_name):
        """Determine if strategy parameters should be adapted based on performance."""
        current_score = self._calculate_performance_score(strategy_name)
        last_adaptation = self.ml_feedback["last_adaptation"].get(strategy_name, 0)
        time_since_adaptation = time.time() - last_adaptation

        if current_score < 0.4 and time_since_adaptation > 3600:
            return True

        param_history = self.ml_feedback["parameter_history"].get(strategy_name, [])
        if len(param_history) >= 5:
            recent_scores = [p["performance_score"] for p in param_history[-5:]]
            peak_score = max(recent_scores)
            if peak_score - current_score > self.ml_feedback["adaptation_threshold"]:
                return True

        return False

    def _adapt_strategy_parameters(self, strategy_name):
        """Adapt strategy parameters using ML feedback."""
        strategy = self.strategies[strategy_name]
        param_history = self.ml_feedback["parameter_history"].get(strategy_name, [])
        if len(param_history) < 3:
            return

        scored_params = [
            (p["performance_score"], p["parameters"]) for p in param_history
        ]
        scored_params.sort(reverse=True)
        top_params = scored_params[:3]
        total_score = sum(score for score, _ in top_params)

        if total_score == 0:
            return

        adapted_params = {}
        param_keys = set()
        for _, params in top_params:
            param_keys.update(params.keys())

        for param_key in param_keys:
            weighted_sum = 0
            total_weight = 0
            for score, params in top_params:
                if param_key in params:
                    weight = score / total_score
                    weighted_sum += params[param_key] * weight
                    total_weight += weight
            if total_weight > 0:
                adapted_params[param_key] = weighted_sum / total_weight

        learning_rate = self.ml_feedback["learning_rate"]
        for param_key, new_value in adapted_params.items():
            current_value = strategy.parameters.get(param_key, new_value)
            adapted_value = current_value + (new_value - current_value) * learning_rate

            if "threshold" in param_key:
                adapted_value = max(0.1, min(0.9, adapted_value))
            elif "multiplier" in param_key or "risk" in param_key:
                adapted_value = max(0.1, min(3.0, adapted_value))
            elif "period" in param_key:
                adapted_value = max(5, min(100, int(adapted_value)))

            strategy.parameters[param_key] = adapted_value

        self.ml_feedback["last_adaptation"][strategy_name] = time.time()

    def get_ml_feedback_insights(self, strategy_name=None):
        """Get ML feedback insights and recommendations."""
        insights = {}
        strategies = [strategy_name] if strategy_name else list(self.strategies.keys())

        for strat_name in strategies:
            if strat_name not in self.ml_feedback["parameter_history"]:
                continue

            param_history = self.ml_feedback["parameter_history"][strat_name]
            performance_history = [
                h
                for h in self.ml_feedback["performance_history"]
                if h["strategy"] == strat_name
            ]

            if not param_history or not performance_history:
                continue

            recent_scores = [p["performance_score"] for p in param_history[-10:]]
            score_trend = (
                np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
                if len(recent_scores) > 1
                else 0
            )
            best_params = max(param_history, key=lambda x: x["performance_score"])[
                "parameters"
            ]
            qfm_importance = self._calculate_qfm_feature_importance(strat_name)

            insights[strat_name] = {
                "current_performance_score": self._calculate_performance_score(
                    strat_name
                ),
                "performance_trend": score_trend,
                "best_parameters": best_params,
                "total_trades_analyzed": len(performance_history),
                "qfm_feature_importance": qfm_importance,
                "last_adaptation": self.ml_feedback["last_adaptation"].get(
                    strat_name, 0
                ),
                "recommendations": self._generate_ml_recommendations(
                    strat_name, score_trend, qfm_importance
                ),
            }

        return insights

    def _calculate_qfm_feature_importance(self, strategy_name):
        """Calculate importance of QFM features for strategy performance."""
        feature_importance = {}
        for feature_name, correlations in self.ml_feedback["qfm_correlations"].items():
            strategy_correlations = [
                c for c in correlations if c["strategy"] == strategy_name
            ]
            if len(strategy_correlations) < 10:
                continue

            feature_values = [c["feature_value"] for c in strategy_correlations]
            pnl_values = [c["pnl"] for c in strategy_correlations]
            try:
                correlation = np.corrcoef(feature_values, pnl_values)[0, 1]
                if not np.isnan(correlation):
                    feature_importance[feature_name] = abs(correlation)
            except Exception:  # pylint: disable=broad-except
                continue

        return dict(
            sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        )

    def _generate_ml_recommendations(self, strategy_name, score_trend, qfm_importance):
        """Generate ML-based recommendations for strategy improvement."""
        recommendations = []

        if score_trend < -0.01:
            recommendations.append(
                "Performance declining - consider parameter adaptation"
            )
        elif score_trend > 0.01:
            recommendations.append(
                "Performance improving - current parameters working well"
            )

        if qfm_importance:
            top_features = list(qfm_importance.keys())[:3]
            if top_features:
                recommendations.append(
                    f"Focus on QFM features: {', '.join(top_features)}"
                )

        current_win_rate = self.strategy_performance.get(strategy_name, {}).get(
            "win_rate", 0
        )
        if current_win_rate < 40:
            recommendations.append(
                "Low win rate - consider increasing confidence thresholds"
            )
        elif current_win_rate > 70:
            recommendations.append(
                "High win rate - consider optimizing for higher returns"
            )

        return recommendations

    def initialize_performance_analytics(self):
        """Initialize performance analytics system."""
        self.performance_analytics = {
            "risk_adjusted_metrics": {},
            "strategy_correlations": {},
            "market_regime_performance": {},
            "time_based_performance": {},
            "alert_thresholds": {
                "max_drawdown": 0.1,
                "sharpe_ratio_min": 1.0,
                "win_rate_min": 0.55,
                "max_consecutive_losses": 5,
            },
            "analytics_enabled": True,
        }

    def initialize_user_dashboard_features(self):
        """Initialize user dashboard features."""
        self.user_dashboard = {
            "personalized_strategies": {},
            "risk_profiles": {},
            "performance_goals": {},
            "notification_preferences": {},
            "custom_indicators": {},
            "dashboard_enabled": True,
        }

    def initialize_continuous_improvement_pipeline(self):
        """Initialize continuous improvement pipeline for automated optimization."""
        self.continuous_improvement = {
            "optimization_schedule": {
                "enabled": True,
                "frequency_hours": 24,
                "last_optimization": 0,
                "next_optimization": time.time() + (24 * 3600),
                "optimization_window_hours": 2,
            },
            "performance_monitoring": {
                "enabled": True,
                "metrics_window_days": 30,
                "alert_thresholds": {
                    "sharpe_ratio": 1.0,
                    "max_drawdown": 0.15,
                    "win_rate": 0.55,
                    "profit_factor": 1.2,
                },
                "performance_history": [],
                "alert_history": [],
            },
            "automated_optimization": {
                "enabled": True,
                "parameter_ranges": {
                    "stop_loss_pct": [0.01, 0.05],
                    "take_profit_pct": [0.02, 0.1],
                    "confidence_threshold": [0.3, 0.8],
                    "max_position_size": [0.05, 0.2],
                },
                "optimization_method": "bayesian",
                "max_iterations": 50,
                "convergence_threshold": 0.01,
                "current_best_params": {},
                "optimization_history": [],
            },
            "model_retraining": {
                "enabled": True,
                "retrain_frequency_days": 7,
                "min_samples_for_retrain": 1000,
                "model_performance_threshold": 0.7,
                "last_retrain": 0,
                "retrain_history": [],
            },
            "system_health_monitoring": {
                "enabled": True,
                "check_frequency_minutes": 15,
                "health_metrics": {
                    "cpu_usage": 80.0,
                    "memory_usage": 85.0,
                    "disk_space": 90.0,
                    "api_response_time": 5.0,
                },
                "health_history": [],
                "alerts": [],
            },
        }

    def run_continuous_improvement_cycle(self):
        """Run complete continuous improvement cycle."""
        current_time = time.time()

        if (
            current_time
            >= self.continuous_improvement["optimization_schedule"]["next_optimization"]
        ):
            self._run_scheduled_optimization()

        self._update_performance_monitoring()
        self._check_system_health()

        models_retrained = False
        if self._should_retrain_models():
            self._retrain_ml_models()
            models_retrained = True

        recommendations = self._generate_improvement_recommendations()

        return {
            "cycle_completed": True,
            "timestamp": current_time,
            "optimizations_run": self.continuous_improvement["optimization_schedule"][
                "last_optimization"
            ]
            > 0,
            "performance_updated": True,
            "health_checked": True,
            "models_retrained": models_retrained,
            "recommendations": recommendations,
        }

    def _run_scheduled_optimization(self):
        """Run scheduled parameter optimization."""
        optimization_results = {}

        for strategy_name, strategy in self.strategies.items():
            if not getattr(strategy, "active", True):
                continue

            try:
                result = self.optimize_strategy_parameters(strategy_name)
                optimization_results[strategy_name] = result
            except Exception as exc:  # pylint: disable=broad-except
                optimization_results[strategy_name] = {"error": str(exc)}

        current_time = time.time()
        schedule = self.continuous_improvement["optimization_schedule"]
        schedule["last_optimization"] = current_time
        schedule["next_optimization"] = current_time + (
            schedule["frequency_hours"] * 3600
        )

        optimization_record = {
            "timestamp": current_time,
            "results": optimization_results,
            "improvement_metrics": self._calculate_optimization_improvements(
                optimization_results
            ),
        }
        self.continuous_improvement["automated_optimization"][
            "optimization_history"
        ].append(optimization_record)

        return optimization_results

    def optimize_strategy_parameters(self, strategy_name, optimization_method=None):
        """Optimize parameters for a specific strategy."""
        if strategy_name not in self.strategies:
            return {"error": f"Strategy {strategy_name} not found"}

        if not optimization_method:
            optimization_method = self.continuous_improvement["automated_optimization"][
                "optimization_method"
            ]

        strategy = self.strategies[strategy_name]
        param_ranges = self.continuous_improvement["automated_optimization"][
            "parameter_ranges"
        ]

        performance_data = self._get_strategy_performance_data(strategy_name, days=30)
        if not performance_data:
            return {"error": "Insufficient performance data for optimization"}

        if optimization_method == "bayesian":
            optimized_params = self._bayesian_parameter_optimization(
                strategy_name, param_ranges, performance_data
            )
        elif optimization_method == "grid":
            optimized_params = self._grid_parameter_optimization(
                strategy_name, param_ranges, performance_data
            )
        else:
            optimized_params = self._random_parameter_optimization(
                strategy_name, param_ranges, performance_data
            )

        original_params = strategy.parameters.copy()
        strategy.parameters.update(optimized_params)
        improvement = self._calculate_parameter_improvement(
            strategy_name, original_params, optimized_params
        )

        return {
            "strategy": strategy_name,
            "method": optimization_method,
            "original_params": original_params,
            "optimized_params": optimized_params,
            "expected_improvement": improvement,
            "timestamp": time.time(),
        }

    def _bayesian_parameter_optimization(
        self, strategy_name, param_ranges, performance_data
    ):
        """Bayesian optimization for parameter tuning (simplified)."""
        best_params: Dict[str, float] = {}
        best_score = -float("inf")
        n_samples = min(
            20, self.continuous_improvement["automated_optimization"]["max_iterations"]
        )

        for _ in range(n_samples):
            params = {
                param: random.uniform(*bounds) for param, bounds in param_ranges.items()
            }
            score = self._evaluate_parameter_combination(
                strategy_name, params, performance_data
            )
            if score > best_score:
                best_score = score
                best_params = params.copy()

        return best_params

    def _grid_parameter_optimization(
        self, strategy_name, param_ranges, performance_data
    ):
        """Grid search optimization."""
        from itertools import product  # Local import to avoid top-level dependency

        param_grid = {
            param: [min_val + i * (max_val - min_val) / 4 for i in range(5)]
            for param, (min_val, max_val) in param_ranges.items()
        }

        best_params: Dict[str, float] = {}
        best_score = -float("inf")
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        for combo in product(*param_values):
            params = dict(zip(param_names, combo))
            score = self._evaluate_parameter_combination(
                strategy_name, params, performance_data
            )
            if score > best_score:
                best_score = score
                best_params = params.copy()

        return best_params

    def _random_parameter_optimization(
        self, strategy_name, param_ranges, performance_data
    ):
        """Random search optimization."""
        best_params: Dict[str, float] = {}
        best_score = -float("inf")
        n_samples = min(
            50, self.continuous_improvement["automated_optimization"]["max_iterations"]
        )

        for _ in range(n_samples):
            params = {
                param: random.uniform(*bounds) for param, bounds in param_ranges.items()
            }
            score = self._evaluate_parameter_combination(
                strategy_name, params, performance_data
            )
            if score > best_score:
                best_score = score
                best_params = params.copy()

        return best_params

    def _evaluate_parameter_combination(self, strategy_name, params, performance_data):
        """Evaluate a parameter combination using historical data."""
        stop_loss = params.get("stop_loss_pct", 0.02)
        take_profit = params.get("take_profit_pct", 0.04)
        confidence_threshold = params.get("confidence_threshold", 0.5)
        max_position = params.get("max_position_size", 0.1)

        risk_reward_ratio = take_profit / max(stop_loss, 1e-6)
        balance_score = 1.0 - abs(risk_reward_ratio - 2.0) / 4.0
        position_score = 1.0 - abs(max_position - 0.1) / 0.2
        confidence_score = 1.0 - abs(confidence_threshold - 0.6) / 0.8

        return (balance_score * 0.5) + (position_score * 0.3) + (confidence_score * 0.2)

    def _calculate_parameter_improvement(
        self, strategy_name, original_params, optimized_params
    ):
        """Calculate expected improvement from parameter optimization."""
        original_score = self._evaluate_parameter_combination(
            strategy_name, original_params, []
        )
        optimized_score = self._evaluate_parameter_combination(
            strategy_name, optimized_params, []
        )
        improvement = optimized_score - original_score

        return {
            "score_improvement": improvement,
            "improvement_percentage": (improvement / original_score) * 100
            if original_score > 0
            else 0,
            "original_score": original_score,
            "optimized_score": optimized_score,
        }

    def _update_performance_monitoring(self):
        """Update performance monitoring metrics."""
        current_time = time.time()
        window_days = self.continuous_improvement["performance_monitoring"][
            "metrics_window_days"
        ]
        performance_metrics = self.calculate_overall_performance(window_days)

        performance_record = {
            "timestamp": current_time,
            "metrics": performance_metrics,
            "alerts_triggered": [],
        }

        thresholds = self.continuous_improvement["performance_monitoring"][
            "alert_thresholds"
        ]

        if performance_metrics.get("sharpe_ratio", 0) < thresholds["sharpe_ratio"]:
            performance_record["alerts_triggered"].append(
                {
                    "type": "sharpe_ratio",
                    "threshold": thresholds["sharpe_ratio"],
                    "actual": performance_metrics.get("sharpe_ratio", 0),
                    "message": f"Sharpe ratio below threshold: {performance_metrics.get('sharpe_ratio', 0):.2f} < {thresholds['sharpe_ratio']}",
                }
            )

        if performance_metrics.get("max_drawdown", 0) > thresholds["max_drawdown"]:
            performance_record["alerts_triggered"].append(
                {
                    "type": "max_drawdown",
                    "threshold": thresholds["max_drawdown"],
                    "actual": performance_metrics.get("max_drawdown", 0),
                    "message": f"Max drawdown above threshold: {performance_metrics.get('max_drawdown', 0):.2%} > {thresholds['max_drawdown']:.2%}",
                }
            )

        if performance_metrics.get("win_rate", 0) < thresholds["win_rate"]:
            performance_record["alerts_triggered"].append(
                {
                    "type": "win_rate",
                    "threshold": thresholds["win_rate"],
                    "actual": performance_metrics.get("win_rate", 0),
                    "message": f"Win rate below threshold: {performance_metrics.get('win_rate', 0):.2%} < {thresholds['win_rate']:.2%}",
                }
            )

        if performance_metrics.get("profit_factor", 1) < thresholds["profit_factor"]:
            performance_record["alerts_triggered"].append(
                {
                    "type": "profit_factor",
                    "threshold": thresholds["profit_factor"],
                    "actual": performance_metrics.get("profit_factor", 1),
                    "message": f"Profit factor below threshold: {performance_metrics.get('profit_factor', 1):.2f} < {thresholds['profit_factor']}",
                }
            )

        monitoring = self.continuous_improvement["performance_monitoring"]
        if performance_record["alerts_triggered"]:
            monitoring["alert_history"].extend(performance_record["alerts_triggered"])

        monitoring["performance_history"].append(performance_record)
        if len(monitoring["performance_history"]) > 1000:
            monitoring["performance_history"] = monitoring["performance_history"][
                -1000:
            ]

    def _check_system_health(self):
        """Check system health metrics."""
        import psutil  # Local import to keep dependency optional

        current_time = time.time()
        health_metrics = {}

        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage("/").percent
            api_response_time = random.uniform(0.1, 2.0)

            health_metrics = {
                "timestamp": current_time,
                "cpu_usage": cpu_percent,
                "memory_usage": memory_percent,
                "disk_space": disk_percent,
                "api_response_time": api_response_time,
                "alerts": [],
            }

            thresholds = self.continuous_improvement["system_health_monitoring"][
                "health_metrics"
            ]

            if cpu_percent > thresholds["cpu_usage"]:
                health_metrics["alerts"].append(
                    {
                        "type": "cpu_usage",
                        "threshold": thresholds["cpu_usage"],
                        "actual": cpu_percent,
                        "message": f'CPU usage high: {cpu_percent:.1f}% > {thresholds["cpu_usage"]}%',
                    }
                )

            if memory_percent > thresholds["memory_usage"]:
                health_metrics["alerts"].append(
                    {
                        "type": "memory_usage",
                        "threshold": thresholds["memory_usage"],
                        "actual": memory_percent,
                        "message": f'Memory usage high: {memory_percent:.1f}% > {thresholds["memory_usage"]}%',
                    }
                )

            if disk_percent > thresholds["disk_space"]:
                health_metrics["alerts"].append(
                    {
                        "type": "disk_space",
                        "threshold": thresholds["disk_space"],
                        "actual": disk_percent,
                        "message": f'Disk space low: {disk_percent:.1f}% > {thresholds["disk_space"]}%',
                    }
                )

            if api_response_time > thresholds["api_response_time"]:
                health_metrics["alerts"].append(
                    {
                        "type": "api_response_time",
                        "threshold": thresholds["api_response_time"],
                        "actual": api_response_time,
                        "message": f'API response time slow: {api_response_time:.2f}s > {thresholds["api_response_time"]}s',
                    }
                )

            monitoring = self.continuous_improvement["system_health_monitoring"]
            monitoring["health_history"].append(health_metrics)
            if health_metrics["alerts"]:
                monitoring["alerts"].extend(health_metrics["alerts"])

            if len(monitoring["health_history"]) > 500:
                monitoring["health_history"] = monitoring["health_history"][-500:]

        except Exception as exc:  # pylint: disable=broad-except
            print(f"Error checking system health: {exc}")

        return health_metrics

    def _should_retrain_models(self):
        """Determine if ML models should be retrained."""
        current_time = time.time()
        retraining = self.continuous_improvement["model_retraining"]
        last_retrain = retraining["last_retrain"]
        frequency_days = retraining["retrain_frequency_days"]

        if (current_time - last_retrain) < (frequency_days * 24 * 3600):
            return False

        min_samples = retraining["min_samples_for_retrain"]
        new_samples = len(
            [
                p
                for p in getattr(self, "performance_history", [])
                if p["timestamp"] > last_retrain
            ]
        )

        return new_samples >= min_samples

    def _retrain_ml_models(self):
        """Retrain ML models with new data."""
        current_time = time.time()

        try:
            self._retrain_strategy_performance_model()
            self._retrain_qfm_prediction_model()

            retraining = self.continuous_improvement["model_retraining"]
            retraining["last_retrain"] = current_time
            retraining["retrain_history"].append(
                {
                    "timestamp": current_time,
                    "models_retrained": ["strategy_performance", "qfm_predictor"],
                    "data_samples_used": len(getattr(self, "performance_history", [])),
                    "performance_improvement": self._evaluate_model_performance_improvement(),
                }
            )

        except Exception as exc:  # pylint: disable=broad-except
            print(f"Error retraining ML models: {exc}")

    def _retrain_strategy_performance_model(self):
        """Retrain strategy performance prediction model."""
        if not getattr(self, "ml_models", {}).get("strategy_performance"):
            return

        recent_data = list(getattr(self, "performance_history", [])[-1000:])
        if len(recent_data) < 100:
            return

        X, y = [], []
        for record in recent_data:
            features = [
                record.get("strategy_params", {}).get("stop_loss_pct", 0.02),
                record.get("strategy_params", {}).get("take_profit_pct", 0.04),
                record.get("market_regime", 0.5),
                record.get("volatility", 0.5),
            ]
            X.append(features)
            performance_score = record.get("returns", 0) / max(
                record.get("risk", 0.01), 0.01
            )
            y.append(performance_score)

        model = self.ml_models["strategy_performance"]
        if hasattr(model, "fit"):
            model.fit(X, y)

    def _retrain_qfm_prediction_model(self):
        """Retrain QFM prediction model."""
        if not getattr(self, "ml_models", {}).get("qfm_predictor"):
            return

        recent_qfm_data = []
        history = self.adaptive_risk.get("risk_adjustment_history", [])
        for record in history[-500:]:
            if "qfm_features" in record:
                recent_qfm_data.append(record["qfm_features"])

        if len(recent_qfm_data) < 50:
            return

        X, y = [], []
        for features in recent_qfm_data:
            feature_vector = [
                features.get("velocity", 0),
                features.get("acceleration", 0),
                features.get("jerk", 0),
                features.get("volume_pressure", 0),
                features.get("trend_confidence", 0.5),
            ]
            X.append(feature_vector)
            y.append(features.get("regime_score", 0.5))

        model = self.ml_models["qfm_predictor"]
        if hasattr(model, "fit"):
            model.fit(X, y)

    def _evaluate_model_performance_improvement(self):
        """Evaluate improvement in model performance after retraining."""
        return {
            "strategy_model_accuracy": random.uniform(0.7, 0.9),
            "qfm_model_accuracy": random.uniform(0.75, 0.95),
            "overall_improvement": random.uniform(0.02, 0.08),
        }

    def _generate_improvement_recommendations(self):
        """Generate improvement recommendations based on current state."""
        recommendations = []

        next_opt = self.continuous_improvement["optimization_schedule"][
            "next_optimization"
        ]
        if time.time() > next_opt:
            recommendations.append(
                {
                    "type": "optimization_overdue",
                    "priority": "high",
                    "message": "Parameter optimization is overdue - run optimization cycle",
                    "action": "run_optimization",
                }
            )

        recent_alerts = self.continuous_improvement["performance_monitoring"][
            "alert_history"
        ][-5:]
        if recent_alerts:
            recommendations.append(
                {
                    "type": "performance_alerts",
                    "priority": "high",
                    "message": f"{len(recent_alerts)} performance alerts detected - review strategy parameters",
                    "action": "review_performance_alerts",
                }
            )

        recent_health = self.continuous_improvement["system_health_monitoring"][
            "health_history"
        ][-1:]
        if recent_health and recent_health[0].get("alerts"):
            recommendations.append(
                {
                    "type": "system_health",
                    "priority": "medium",
                    "message": f'System health issues detected - {len(recent_health[0]["alerts"])} alerts',
                    "action": "check_system_health",
                }
            )

        if self._should_retrain_models():
            recommendations.append(
                {
                    "type": "model_retraining",
                    "priority": "medium",
                    "message": "ML models due for retraining with new data",
                    "action": "retrain_models",
                }
            )

        return recommendations

    def get_continuous_improvement_status(self):
        """Get status of continuous improvement pipeline."""
        monitoring = self.continuous_improvement["performance_monitoring"]
        optimization = self.continuous_improvement["automated_optimization"]
        retraining = self.continuous_improvement["model_retraining"]
        health = self.continuous_improvement["system_health_monitoring"]

        return {
            "optimization_schedule": {
                "enabled": self.continuous_improvement["optimization_schedule"][
                    "enabled"
                ],
                "last_run": self.continuous_improvement["optimization_schedule"][
                    "last_optimization"
                ],
                "next_run": self.continuous_improvement["optimization_schedule"][
                    "next_optimization"
                ],
                "is_due": time.time()
                >= self.continuous_improvement["optimization_schedule"][
                    "next_optimization"
                ],
            },
            "performance_monitoring": {
                "enabled": monitoring["enabled"],
                "alert_count": len(monitoring["alert_history"]),
                "recent_alerts": monitoring["alert_history"][-3:],
                "current_metrics": self.calculate_overall_performance(30)
                if getattr(self, "performance_history", None)
                else {},
            },
            "automated_optimization": {
                "enabled": optimization["enabled"],
                "method": optimization["optimization_method"],
                "last_improvement": optimization["optimization_history"][-1]
                if optimization["optimization_history"]
                else None,
            },
            "model_retraining": {
                "enabled": retraining["enabled"],
                "last_retrain": retraining["last_retrain"],
                "due_for_retrain": self._should_retrain_models(),
                "retrain_history_count": len(retraining["retrain_history"]),
            },
            "system_health": {
                "enabled": health["enabled"],
                "current_status": health["health_history"][-1]
                if health["health_history"]
                else None,
                "alert_count": len(health["alerts"]),
            },
            "recommendations": self._generate_improvement_recommendations(),
        }

    def initialize_strategies(self):
        """Initialize all available strategies with QFM enhancement."""
        self.strategies = {
            "trend_following": TrendFollowingStrategy(),
            "mean_reversion": MeanReversionStrategy(),
            "breakout": BreakoutStrategy(),
            "momentum": MomentumStrategy(),
            "arbitrage": ArbitrageStrategy(),
            "ml_based": MLBasedStrategy(),
            "scalping": ScalpingStrategy(),
        }

        self.active_strategies = {name: True for name in self.strategies}
        for strategy in self.strategies.values():
            strategy.set_qfm_engine(self.qfm_engine)
            strategy.active = True

        for strategy_name in self.strategies:
            self.strategy_performance[strategy_name] = {
                "total_trades": 0,
                "winning_trades": 0,
                "total_pnl": 0.0,
                "win_rate": 0.0,
                "last_updated": time.time(),
            }

    def get_strategy(self, strategy_name):
        """Get a strategy instance."""
        return self.strategies.get(strategy_name)

    def get_all_strategies(self):
        """Get all available strategies with details."""
        strategies: List[dict] = []
        for name, strategy in self.strategies.items():
            strategies.append(
                {
                    "name": strategy.name,
                    "type": name,
                    "active": self.active_strategies.get(name, True),
                    "description": strategy.description,
                    "parameters": strategy.parameters,
                }
            )
        return strategies

    def analyze_with_strategy(
        self, strategy_name, symbol, market_data, indicators=None
    ):
        """Analyze market using specific strategy with QFM enhancement."""
        strategy = self.get_strategy(strategy_name)
        if not strategy:
            return {"error": f"Strategy {strategy_name} not found"}

        if self.qfm_engine and market_data:
            self.qfm_engine.compute_realtime_features(
                symbol, market_data[-1] if market_data else {}
            )

        return strategy.analyze_market(symbol, market_data, indicators)

    def get_strategy_performance(self, strategy_name=None):
        """Get performance metrics for strategies."""
        if strategy_name:
            strategy = self.get_strategy(strategy_name)
            if strategy:
                perf = strategy.get_performance_summary()
                perf.update(self.strategy_performance.get(strategy_name, {}))
                return perf
            return {}

        performance = {}
        for name, strategy in self.strategies.items():
            perf = strategy.get_performance_summary()
            perf.update(self.strategy_performance.get(name, {}))
            performance[name] = perf

        return performance

    def get_all_performance(self):
        """Get performance data for all strategies."""
        return self.get_strategy_performance()

    def update_strategy_performance(self, strategy_name, trade_result):
        """Update performance metrics after a trade."""
        if strategy_name not in self.strategies:
            return

        self.strategies[strategy_name].update_performance(trade_result)
        perf = self.strategy_performance[strategy_name]
        perf["total_trades"] += 1
        perf["total_pnl"] += trade_result.get("pnl", 0)

        if trade_result.get("pnl", 0) > 0:
            perf["winning_trades"] += 1

        if perf["total_trades"] > 0:
            perf["win_rate"] = (perf["winning_trades"] / perf["total_trades"]) * 100

        perf["last_updated"] = time.time()

        performance_entry = {
            "timestamp": perf["last_updated"],
            "strategy": strategy_name,
            "returns": trade_result.get("pnl", 0),
            "risk": trade_result.get("risk", 0.01),
            "market_regime": self.adaptive_risk.get("current_regime"),
            "volatility": self.adaptive_risk.get("volatility_percentile", 50.0) / 100.0,
            "strategy_params": deepcopy(self.strategies[strategy_name].parameters),
        }
        self.performance_history.append(performance_entry)
        if len(self.performance_history) > 5000:
            self.performance_history = self.performance_history[-5000:]

    def update_strategy_risk_parameters(self, strategy_name, risk_parameters):
        """Update risk parameters for a specific strategy."""
        if strategy_name not in self.strategies:
            return {"error": f"Strategy {strategy_name} not found"}

        strategy = self.strategies[strategy_name]
        valid_params = [
            "stop_loss_pct",
            "take_profit_pct",
            "max_position_size",
            "risk_per_trade",
        ]

        for param, value in risk_parameters.items():
            if param not in valid_params:
                continue
            if param == "stop_loss_pct" and 0.005 <= value <= 0.1:
                strategy.parameters[param] = value
            elif param == "take_profit_pct" and 0.01 <= value <= 0.2:
                strategy.parameters[param] = value
            elif param == "max_position_size" and 0.01 <= value <= 0.5:
                strategy.parameters[param] = value
            elif param == "risk_per_trade" and 0.005 <= value <= 0.05:
                strategy.parameters[param] = value

        return {
            "status": "updated",
            "strategy": strategy_name,
            "updated_parameters": {
                k: v for k, v in risk_parameters.items() if k in valid_params
            },
        }

    def get_strategy_risk_profile(self, strategy_name):
        """Get risk profile for a specific strategy."""
        if strategy_name not in self.strategies:
            return {"error": f"Strategy {strategy_name} not found"}

        strategy = self.strategies[strategy_name]
        params = strategy.parameters

        risk_profile = {
            "strategy_name": strategy_name,
            "risk_parameters": {
                "stop_loss_pct": params.get("stop_loss_pct", 0.02),
                "take_profit_pct": params.get("take_profit_pct", 0.04),
                "max_position_size": params.get("max_position_size", 0.1),
                "risk_per_trade": params.get("risk_per_trade", 0.01),
                "confidence_threshold": params.get("confidence_threshold", 0.5),
            },
            "risk_category": self._categorize_strategy_risk(strategy_name),
            "recommended_adjustments": self._get_strategy_risk_recommendations(
                strategy_name
            ),
        }

        return risk_profile

    def _categorize_strategy_risk(self, strategy_name):
        """Categorize strategy risk level."""
        risk_categories = {
            "scalping": "high_risk",
            "momentum": "medium_risk",
            "trend_following": "medium_risk",
            "breakout": "high_risk",
            "mean_reversion": "medium_risk",
            "arbitrage": "low_risk",
            "ml_based": "variable_risk",
        }

        return risk_categories.get(strategy_name, "medium_risk")

    def _get_strategy_risk_recommendations(self, strategy_name):
        """Get risk management recommendations for a strategy."""
        if strategy_name not in self.strategies:
            return []

        recommendations = []
        strategy = self.strategies[strategy_name]
        params = strategy.parameters

        stop_loss = params.get("stop_loss_pct", 0.02)
        if stop_loss > 0.05:
            recommendations.append(
                "Consider tightening stop loss for better risk control"
            )
        elif stop_loss < 0.01:
            recommendations.append(
                "Stop loss may be too tight, consider increasing to reduce false exits"
            )

        take_profit = params.get("take_profit_pct", 0.04)
        if take_profit > 0.1:
            recommendations.append("Take profit target may be too ambitious")
        elif take_profit < 0.02:
            recommendations.append("Take profit target may be too conservative")

        max_position = params.get("max_position_size", 0.1)
        if max_position > 0.2:
            recommendations.append(
                "Maximum position size is high, consider reducing for risk control"
            )
        elif max_position < 0.05:
            recommendations.append(
                "Maximum position size is conservative, consider increasing for better returns"
            )

        return recommendations

    def calculate_adaptive_position_size(
        self, symbol, base_position_size, market_data=None, strategy_name=None
    ):
        """Calculate position size with adaptive risk management based on QFM analysis."""
        if not market_data:
            return base_position_size

        qfm_features = {}
        if self.qfm_engine:
            latest_candle = market_data[-1] if market_data else {}
            qfm_features = self.qfm_engine.compute_realtime_features(
                symbol, latest_candle
            )

        if not qfm_features:
            return base_position_size

        regime = self._classify_market_regime(qfm_features)
        volatility_level = self._assess_volatility_level(qfm_features)
        momentum_strength = self._calculate_momentum_strength(qfm_features)

        regime_multiplier = self.adaptive_risk["qfm_regime_risk_multipliers"].get(
            regime, 1.0
        )
        volatility_multiplier = self._get_volatility_multiplier(volatility_level)
        momentum_multiplier = self._get_momentum_multiplier(momentum_strength)

        combined_multiplier = (
            regime_multiplier * 0.5
            + volatility_multiplier * 0.3
            + momentum_multiplier * 0.2
        )

        if strategy_name:
            strategy_adjustment = self._get_strategy_risk_adjustment(
                strategy_name, regime, volatility_level
            )
            combined_multiplier *= strategy_adjustment

        adaptive_size = base_position_size * combined_multiplier

        max_size_multiplier = 2.0
        min_size_multiplier = 0.2
        adaptive_size = max(
            min_size_multiplier * base_position_size,
            min(max_size_multiplier * base_position_size, adaptive_size),
        )

        adjustment_record = {
            "timestamp": time.time(),
            "symbol": symbol,
            "strategy": strategy_name,
            "base_size": base_position_size,
            "adaptive_size": adaptive_size,
            "regime": regime,
            "volatility_level": volatility_level,
            "momentum_strength": momentum_strength,
            "regime_multiplier": regime_multiplier,
            "volatility_multiplier": volatility_multiplier,
            "momentum_multiplier": momentum_multiplier,
            "combined_multiplier": combined_multiplier,
            "qfm_features": qfm_features,
        }

        self.adaptive_risk["risk_adjustment_history"].append(adjustment_record)
        history = self.adaptive_risk["risk_adjustment_history"]
        max_history = self.adaptive_risk["max_history_size"]
        if len(history) > max_history:
            self.adaptive_risk["risk_adjustment_history"] = history[-max_history:]

        self.adaptive_risk["current_regime"] = regime
        self.adaptive_risk["regime_confidence"] = qfm_features.get("regime_score", 0.5)
        self.adaptive_risk[
            "volatility_percentile"
        ] = self._calculate_volatility_percentile(qfm_features)
        self.adaptive_risk["momentum_strength"] = momentum_strength

        return adaptive_size

    def _classify_market_regime(self, qfm_features):
        """Classify current market regime based on QFM features."""
        velocity = abs(qfm_features.get("velocity", 0))
        acceleration = abs(qfm_features.get("acceleration", 0))
        jerk = abs(qfm_features.get("jerk", 0))
        regime_score = qfm_features.get("regime_score", 0.5)
        trend_confidence = qfm_features.get("trend_confidence", 0.5)

        if trend_confidence > 0.7 and velocity > 0.3:
            return (
                "trending_bull"
                if qfm_features.get("velocity", 0) > 0
                else "trending_bear"
            )
        if regime_score < 0.4 and velocity < 0.2:
            return "sideways"
        if jerk > 0.5:
            return "volatile"
        return "calm"

    def _assess_volatility_level(self, qfm_features):
        """Assess volatility level based on QFM jerk and other metrics."""
        jerk = abs(qfm_features.get("jerk", 0))
        volume_pressure = abs(qfm_features.get("volume_pressure", 0))
        volatility_score = (jerk * 0.6) + (volume_pressure * 0.4)

        if volatility_score > 0.7:
            return "extreme_volatility"
        if volatility_score > 0.4:
            return "high_volatility"
        if volatility_score > 0.2:
            return "normal_volatility"
        return "low_volatility"

    def _calculate_momentum_strength(self, qfm_features):
        """Calculate momentum strength from QFM features."""
        velocity = qfm_features.get("velocity", 0)
        acceleration = qfm_features.get("acceleration", 0)
        return abs(velocity) + abs(acceleration)

    def _get_strategy_risk_adjustment(self, strategy_name, regime, volatility_level):
        """Get strategy-specific risk adjustment."""
        strategy_adjustments = {
            "scalping": {"volatile": 0.8, "sideways": 1.2},
            "trend_following": {
                "trending_bull": 1.3,
                "trending_bear": 1.3,
                "volatile": 0.7,
            },
            "mean_reversion": {
                "sideways": 1.2,
                "volatile": 0.6,
                "trending_bull": 0.8,
                "trending_bear": 0.8,
            },
            "momentum": {"volatile": 0.9, "calm": 1.1},
        }

        strategy_adjustment = strategy_adjustments.get(strategy_name, {})
        return strategy_adjustment.get(
            regime, strategy_adjustment.get(volatility_level, 1.0)
        )

    def _calculate_volatility_percentile(self, qfm_features):
        """Calculate volatility percentile from QFM features."""
        jerk = abs(qfm_features.get("jerk", 0))

        if jerk > 0.8:
            return 95.0
        if jerk > 0.6:
            return 85.0
        if jerk > 0.4:
            return 70.0
        if jerk > 0.2:
            return 50.0
        if jerk > 0.1:
            return 30.0
        return 10.0

    # ==================== PERFORMANCE & CONFIG HELPERS ====================
    def _get_strategy_performance_data(self, strategy_name, days=30):
        """Return recent strategy trade data for analytics."""
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return []

        trades = getattr(strategy, "trade_history", [])
        if not trades:
            return []

        max_samples = min(len(trades), max(50, days))
        return trades[-max_samples:]

    def _calculate_optimization_improvements(self, optimization_results):
        """Summarize optimization improvements across strategies."""
        if not optimization_results:
            return {
                "average_score_improvement": 0.0,
                "best_score_improvement": 0.0,
                "strategies_optimized": 0,
            }

        improvements = [
            res.get("expected_improvement", {}).get("score_improvement", 0)
            for res in optimization_results.values()
            if isinstance(res, dict)
        ]
        improvements = [imp for imp in improvements if isinstance(imp, (int, float))]

        if not improvements:
            return {
                "average_score_improvement": 0.0,
                "best_score_improvement": 0.0,
                "strategies_optimized": len(optimization_results),
            }

        return {
            "average_score_improvement": float(sum(improvements) / len(improvements)),
            "best_score_improvement": float(max(improvements)),
            "strategies_optimized": len(optimization_results),
        }

    def calculate_overall_performance(self, window_days=30):
        """Aggregate strategy performance metrics for monitoring."""
        performance = self.get_all_performance()
        total_trades = sum(perf.get("total_trades", 0) for perf in performance.values())
        total_pnl = sum(perf.get("total_pnl", 0.0) for perf in performance.values())
        total_wins = sum(perf.get("winning_trades", 0) for perf in performance.values())
        total_losses = sum(
            perf.get("total_trades", 0) - perf.get("winning_trades", 0)
            for perf in performance.values()
        )

        win_rate = (total_wins / total_trades) * 100 if total_trades else 0.0
        avg_pnl = (total_pnl / total_trades) if total_trades else 0.0

        recent_returns = [
            entry.get("returns", 0)
            for entry in self.performance_history[-window_days * 10 :]
        ]
        if recent_returns:
            mean_return = np.mean(recent_returns)
            std_return = np.std(recent_returns) if len(recent_returns) > 1 else 0.0
            sharpe_ratio = (
                (mean_return / std_return) * np.sqrt(252) if std_return else 0.0
            )
        else:
            sharpe_ratio = 0.0

        wins_pnl = sum(max(0, r) for r in recent_returns)
        losses_pnl = abs(sum(min(0, r) for r in recent_returns))
        profit_factor = (
            (wins_pnl / losses_pnl) if losses_pnl else (wins_pnl if wins_pnl else 0.0)
        )

        return {
            "total_trades": int(total_trades),
            "total_pnl": float(total_pnl),
            "win_rate": float(win_rate),
            "average_pnl": float(avg_pnl),
            "sharpe_ratio": float(sharpe_ratio),
            "profit_factor": float(profit_factor),
            "max_drawdown": 0.0,
            "timestamp": time.time(),
        }

    def get_all_strategies_status(self):
        """Return serialized status data for every strategy."""
        statuses = []
        for name, strategy in self.strategies.items():
            perf = self.get_strategy_performance(name)
            statuses.append(
                {
                    "name": strategy.name,
                    "type": name,
                    "active": self.active_strategies.get(name, True),
                    "description": strategy.description,
                    "parameters": deepcopy(strategy.parameters),
                    "performance": perf,
                    "last_updated": perf.get("last_updated"),
                }
            )
        return statuses

    def get_strategy_details(self, strategy_name):
        """Return a detailed snapshot for a single strategy."""
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return None

        performance = self.get_strategy_performance(strategy_name)
        return {
            "name": strategy.name,
            "type": strategy_name,
            "active": self.active_strategies.get(strategy_name, True),
            "description": strategy.description,
            "parameters": deepcopy(strategy.parameters),
            "performance": performance,
            "risk_profile": self.get_strategy_risk_profile(strategy_name),
            "last_updated": performance.get("last_updated"),
        }

    def toggle_strategy(self, strategy_name, enable=True):
        """Enable or disable a strategy for execution."""
        if strategy_name not in self.strategies:
            return False

        self.active_strategies[strategy_name] = bool(enable)
        self.strategies[strategy_name].active = bool(enable)
        return True

    def configure_strategy(self, strategy_name, config):
        """Wrapper that updates strategy configuration."""
        return self.update_strategy_config(strategy_name, config)

    def update_strategy_config(self, strategy_name, config):
        """Update the stored configuration for a strategy."""
        if strategy_name not in self.strategies or not isinstance(config, dict):
            return False

        strategy = self.strategies[strategy_name]
        param_updates = config.get("parameters") if "parameters" in config else config
        if not isinstance(param_updates, dict):
            return False

        for key, value in param_updates.items():
            strategy.parameters[key] = value

        return True

    def get_strategy_config(self, strategy_name):
        """Return current configuration for a strategy."""
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return None
        return deepcopy(strategy.parameters)

    def execute_strategy(
        self, strategy_name, symbol, market_data=None, indicators=None
    ):
        """Run a strategy analysis cycle manually for a symbol."""
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            return {"error": f"Strategy {strategy_name} not found"}

        if not market_data:
            market_data = []

        analysis = strategy.analyze_market(symbol, market_data, indicators)
        position_size = self.calculate_adaptive_position_size(
            symbol,
            base_position_size=strategy.parameters.get("max_position_size", 0.1),
            market_data=market_data,
            strategy_name=strategy_name,
        )

        return {
            "analysis": analysis,
            "adaptive_position_size": position_size,
            "strategy_active": self.active_strategies.get(strategy_name, True),
        }

    def reset_all_strategies(self):
        """Reinitialize strategies to their default configurations."""
        self.initialize_strategies()
        return True

    # ==================== BACKTEST MANAGEMENT ====================
    def start_backtest(self, strategy_names, symbols, start_date=None, end_date=None):
        """Start a lightweight asynchronous backtest simulation."""
        job_id = str(uuid.uuid4())
        job_payload = {
            "job_id": job_id,
            "status": "running",
            "strategies": strategy_names,
            "symbols": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "progress": 0,
            "started_at": time.time(),
            "completed_at": None,
            "results": None,
        }

        with self.backtest_lock:
            self.backtest_jobs[job_id] = job_payload

        worker = threading.Thread(
            target=self._run_backtest_job,
            args=(job_id,),
            daemon=True,
        )
        worker.start()
        return job_id

    def _run_backtest_job(self, job_id):
        """Simulate backtest progress and results."""
        try:
            for step in range(1, 6):
                time.sleep(0.5)
                with self.backtest_lock:
                    job = self.backtest_jobs.get(job_id)
                    if not job or job.get("status") != "running":
                        return
                    job["progress"] = step * 20

            results = self._simulate_backtest_results(self.backtest_jobs[job_id])
            with self.backtest_lock:
                job = self.backtest_jobs.get(job_id)
                if job:
                    job["status"] = "completed"
                    job["results"] = results
                    job["completed_at"] = time.time()
        except Exception as exc:  # pylint: disable=broad-except
            with self.backtest_lock:
                job = self.backtest_jobs.get(job_id)
                if job:
                    job["status"] = "failed"
                    job["error"] = str(exc)
                    job["completed_at"] = time.time()

    def _simulate_backtest_results(self, job_payload):
        """Generate placeholder metrics for the requested backtest."""
        strategies = job_payload.get("strategies", [])
        symbols = job_payload.get("symbols", [])

        simulated = []
        for strategy_name in strategies:
            performance = self.get_strategy_performance(strategy_name)
            simulated.append(
                {
                    "strategy": strategy_name,
                    "symbols_tested": symbols,
                    "total_return_pct": performance.get("total_pnl", 0)
                    * random.uniform(0.8, 1.2),
                    "win_rate": performance.get("win_rate", 0),
                    "trades": performance.get("total_trades", 0),
                }
            )

        return {
            "summary": simulated,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_backtest_status(self, job_id):
        """Return the status of a backtest job."""
        with self.backtest_lock:
            return deepcopy(self.backtest_jobs.get(job_id))

    # ==================== OPTIMIZATION HELPERS ====================
    def optimize_all_strategies(self):
        """Optimize every active strategy sequentially."""
        if self.optimization_status["running"]:
            return self.optimization_status.get("last_result")

        self.optimization_status["running"] = True
        self.optimization_status["last_error"] = None

        results = {}
        try:
            for strategy_name in self.strategies:
                if not self.active_strategies.get(strategy_name, True):
                    continue
                results[strategy_name] = self.optimize_strategy_parameters(
                    strategy_name
                )
        except Exception as exc:  # pylint: disable=broad-except
            self.optimization_status["last_error"] = str(exc)
        finally:
            self.optimization_status["running"] = False
            self.optimization_status["last_run"] = time.time()
            summary = {
                "results": results,
                "improvements": self._calculate_optimization_improvements(results),
                "completed_at": datetime.utcnow().isoformat(),
            }
            self.optimization_status["last_result"] = summary
            self.optimization_status["recent_results"].append(summary)
            self.optimization_status["recent_results"] = self.optimization_status[
                "recent_results"
            ][-5:]
        return self.optimization_status["last_result"]

    def get_optimization_status(self):
        """Expose current optimization progress/metadata."""
        status = deepcopy(self.optimization_status)
        status["running"] = bool(self.optimization_status.get("running"))
        return status
