"""Admin analytics, reporting, and monitoring endpoints."""
from __future__ import annotations

import time
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify

from app.auth.decorators import admin_required
from app.extensions import db
from app.models import User, UserPortfolio, UserTrade


admin_analytics_bp = Blueprint("admin_analytics", __name__, url_prefix="/api/admin")


def _ctx() -> dict:
    ctx = current_app.extensions.get("ai_bot_context")
    if ctx is None:
        raise RuntimeError("AI bot context is not initialized")
    return ctx


def _dashboard_data(ctx: dict) -> dict:
    data = ctx.get("dashboard_data")
    if data is None:
        raise RuntimeError("Dashboard data is unavailable")
    return data


@admin_analytics_bp.route("/risk_assessment")
@admin_required
def api_admin_risk_assessment():
    """Advanced risk assessment across the entire user base."""
    try:
        all_portfolios = UserPortfolio.query.all()
        all_trades = UserTrade.query.all()
        all_users = User.query.all()

        if not all_portfolios and not all_trades:
            return (
                jsonify(
                    {
                        "error": "No portfolio or trade data available for risk assessment",
                        "risk_levels": {},
                        "system_risks": {},
                        "recommendations": [],
                        "timestamp": time.time(),
                    }
                ),
                404,
            )

        risk_report = {
            "system_overview": {
                "total_users": len(all_users),
                "active_users": len([u for u in all_users if u.is_active]),
                "total_portfolio_value": 0.0,
                "total_exposure": 0.0,
                "system_risk_score": 0.0,
                "risk_distribution": {"low": 0, "medium": 0, "high": 0, "extreme": 0},
            },
            "portfolio_concentration": {
                "symbol_exposure": {},
                "user_concentration": {},
                "sector_exposure": {},
                "geographic_exposure": {},
            },
            "volatility_analysis": {
                "user_volatility": {},
                "symbol_volatility": {},
                "system_volatility": 0.0,
                "volatility_clusters": {},
            },
            "correlation_risks": {
                "user_correlations": {},
                "symbol_correlations": {},
                "strategy_correlations": {},
                "system_correlation_matrix": {},
            },
            "value_at_risk": {
                "daily_var_95": 0.0,
                "daily_var_99": 0.0,
                "monthly_var_95": 0.0,
                "expected_shortfall_95": 0.0,
                "stress_test_losses": {},
            },
            "liquidity_risks": {
                "large_position_risk": {},
                "low_liquidity_symbols": [],
                "withdrawal_concerns": {},
                "market_impact_risk": {},
            },
            "operational_risks": {
                "system_reliability": {},
                "user_behavior_risks": {},
                "strategy_concentration": {},
                "technical_risks": {},
            },
            "recommendations": [],
            "risk_alerts": [],
            "timestamp": time.time(),
        }

        total_portfolio_value = sum(
            (p.total_balance or 0) + (p.available_balance or 0) for p in all_portfolios
        )
        total_exposure = sum(p.total_balance or 0 for p in all_portfolios)
        risk_report["system_overview"]["total_portfolio_value"] = total_portfolio_value
        risk_report["system_overview"]["total_exposure"] = total_exposure

        symbol_exposure = {}
        for portfolio in all_portfolios:
            exposure_value = portfolio.total_balance or 0
            major_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT"]
            if not major_symbols:
                continue
            exposure_per_symbol = exposure_value / len(major_symbols)
            for symbol in major_symbols:
                symbol_exposure[symbol] = (
                    symbol_exposure.get(symbol, 0) + exposure_per_symbol
                )

        for symbol, exposure in symbol_exposure.items():
            percentage = (exposure / total_exposure) * 100 if total_exposure > 0 else 0
            risk_report["portfolio_concentration"]["symbol_exposure"][symbol] = {
                "exposure_value": exposure,
                "percentage": percentage,
                "risk_level": "high"
                if percentage > 20
                else "medium"
                if percentage > 10
                else "low",
            }

        user_exposure = {}
        for portfolio in all_portfolios:
            user = db.session.get(User, portfolio.user_id)
            username = user.username if user else f"User_{portfolio.user_id}"
            exposure = portfolio.total_balance or 0
            user_exposure[username] = {
                "exposure_value": exposure,
                "percentage": (exposure / total_exposure) * 100
                if total_exposure > 0
                else 0,
                "trade_count": len(
                    [t for t in all_trades if t.user_id == portfolio.user_id]
                ),
            }
        risk_report["portfolio_concentration"]["user_concentration"] = user_exposure

        user_volatility = {}
        for user in all_users:
            user_trades = [
                t for t in all_trades if t.user_id == user.id and t.pnl is not None
            ]
            if len(user_trades) > 1:
                returns = [trade.pnl or 0 for trade in user_trades]
                avg_return = sum(returns) / len(returns)
                volatility = (
                    sum((r - avg_return) ** 2 for r in returns) / len(returns)
                ) ** 0.5
                user_volatility[user.id] = {
                    "volatility": volatility,
                    "avg_return": avg_return,
                    "trade_count": len(user_trades),
                }
        risk_report["volatility_analysis"] = user_volatility

        risk_report["correlation_analysis"] = {
            "user_correlations": {},
            "system_correlation": 0.0,
            "correlation_matrix": {},
        }

        if all_trades:
            returns = sorted([trade.pnl or 0 for trade in all_trades])
            var_95_index = int(len(returns) * 0.05) if returns else 0
            var_99_index = int(len(returns) * 0.01) if returns else 0
            var_95 = returns[var_95_index] if returns else 0
            var_99 = returns[var_99_index] if returns else 0
            tail = returns[: max(1, var_95_index)] if returns else []
            expected_shortfall = sum(tail) / len(tail) if tail else 0
            risk_report["value_at_risk"] = {
                "var_95": var_95,
                "var_99": var_99,
                "expected_shortfall": expected_shortfall,
            }

        return jsonify(risk_report)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error in /api/admin/risk_assessment: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_analytics_bp.route("/performance_benchmarking")
@admin_required
def api_admin_performance_benchmarking():
    """System-wide benchmarking versus indices and peers."""
    try:
        all_trades = UserTrade.query.all()
        if not all_trades:
            return (
                jsonify(
                    {
                        "error": "No trade data available for benchmarking",
                        "benchmarks": {},
                        "comparisons": {},
                        "timestamp": time.time(),
                    }
                ),
                404,
            )

        benchmarks = {
            "market_indices": {
                "btc_performance": 0.0,
                "crypto_market_avg": 0.0,
                "traditional_indices": {"sp500": 0.0, "nasdaq": 0.0, "dow_jones": 0.0},
            },
            "historical_performance": {
                "system_performance": {},
                "benchmark_comparison": {},
                "rolling_performance": {},
            },
            "peer_comparison": {
                "top_performers": [],
                "average_performance": {},
                "performance_distribution": {},
            },
            "risk_adjusted_returns": {
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "information_ratio": 0.0,
                "alpha": 0.0,
                "beta": 0.0,
            },
            "timestamp": time.time(),
        }

        total_pnl = sum((t.pnl or 0) for t in all_trades)
        total_investment = sum(
            (t.quantity or 0) * (t.entry_price or 0) for t in all_trades
        )

        if total_investment > 0:
            total_return = (total_pnl / total_investment) * 100
            oldest_trade = min(
                (t.timestamp for t in all_trades if t.timestamp), default=datetime.now()
            )
            trading_days = max(1, (datetime.now() - oldest_trade).days or 1)
            annualized_return = total_return * (365 / trading_days)
            benchmarks["historical_performance"]["system_performance"] = {
                "total_return_pct": total_return,
                "annualized_return": annualized_return,
                "volatility": 0.0,
                "max_drawdown": 0.0,
            }

        now = datetime.now()
        monthly_performance = {}
        for i in range(12):
            month_start = now - timedelta(days=30 * (i + 1))
            month_end = now - timedelta(days=30 * i)
            month_trades = [
                t
                for t in all_trades
                if t.timestamp and month_start <= t.timestamp < month_end
            ]
            if month_trades:
                month_pnl = sum((t.pnl or 0) for t in month_trades)
                monthly_performance[f"month_{i + 1}"] = month_pnl
        benchmarks["historical_performance"][
            "rolling_performance"
        ] = monthly_performance

        user_performance = {}
        for user in User.query.all():
            user_trades = UserTrade.query.filter_by(user_id=user.id).all()
            if user_trades:
                user_pnl = sum((t.pnl or 0) for t in user_trades)
                user_investment = sum(
                    (t.quantity or 0) * (t.entry_price or 0) for t in user_trades
                )
                user_return = (
                    (user_pnl / user_investment * 100) if user_investment > 0 else 0
                )
                user_performance[user.username] = {
                    "total_pnl": user_pnl,
                    "total_return_pct": user_return,
                    "trade_count": len(user_trades),
                }
        sorted_users = sorted(
            user_performance.items(),
            key=lambda x: x[1]["total_return_pct"],
            reverse=True,
        )
        benchmarks["peer_comparison"]["top_performers"] = sorted_users[:10]

        if user_performance:
            avg_return = sum(
                u["total_return_pct"] for u in user_performance.values()
            ) / len(user_performance)
            medians = sorted(u["total_return_pct"] for u in user_performance.values())
            median_return = medians[len(medians) // 2]
            benchmarks["peer_comparison"]["average_performance"] = {
                "average_return_pct": avg_return,
                "median_return_pct": median_return,
                "total_participants": len(user_performance),
            }

        if len(all_trades) > 1:
            returns = [t.pnl or 0 for t in all_trades]
            avg_return = sum(returns) / len(returns)
            std_dev = (
                sum((r - avg_return) ** 2 for r in returns) / len(returns)
            ) ** 0.5
            downside_returns = [r for r in returns if r < 0]
            downside_std = (
                sum(r**2 for r in downside_returns) / max(1, len(downside_returns))
            ) ** 0.5
            risk_free_rate = 0.02
            sharpe = (avg_return - risk_free_rate) / std_dev if std_dev > 0 else 0
            sortino = (
                (avg_return - risk_free_rate) / downside_std if downside_std > 0 else 0
            )
            benchmarks["risk_adjusted_returns"]["sharpe_ratio"] = sharpe
            benchmarks["risk_adjusted_returns"]["sortino_ratio"] = sortino

        return jsonify(benchmarks)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error in /api/admin/performance_benchmarking: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_analytics_bp.route("/automated_strategy_optimization")
@admin_required
def api_admin_automated_strategy_optimization():
    """Provide automated strategy optimization recommendations."""
    try:
        all_trades = UserTrade.query.all()
        if not all_trades:
            return (
                jsonify(
                    {
                        "error": "No trade data available for optimization analysis",
                        "recommendations": {},
                        "optimization_plan": {},
                        "timestamp": time.time(),
                    }
                ),
                404,
            )

        optimization = {
            "current_system_analysis": {
                "overall_performance": {},
                "strategy_effectiveness": {},
                "risk_exposure": {},
                "market_conditions": {},
            },
            "optimization_recommendations": {
                "strategy_adjustments": [],
                "risk_management_changes": [],
                "portfolio_rebalancing": [],
                "market_adaptation": [],
            },
            "implementation_plan": {
                "priority_actions": [],
                "phased_rollout": {},
                "expected_improvements": {},
                "monitoring_metrics": [],
            },
            "timestamp": time.time(),
        }

        total_trades = len(all_trades)
        winning_trades = len([t for t in all_trades if (t.pnl or 0) > 0])
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = sum((t.pnl or 0) for t in all_trades)
        avg_trade_pnl = total_pnl / total_trades if total_trades > 0 else 0
        total_wins = sum((t.pnl or 0) for t in all_trades if (t.pnl or 0) > 0)
        total_losses = abs(sum((t.pnl or 0) for t in all_trades if (t.pnl or 0) < 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

        optimization["current_system_analysis"]["overall_performance"] = {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_trade_pnl": avg_trade_pnl,
            "profit_factor": profit_factor,
        }

        strategy_performance = {}
        for trade in all_trades:
            strategy = trade.signal_source or "unknown"
            stats = strategy_performance.setdefault(
                strategy, {"trades": 0, "wins": 0, "pnl": 0.0, "avg_pnl": 0.0}
            )
            stats["trades"] += 1
            stats["pnl"] += trade.pnl or 0
            if (trade.pnl or 0) > 0:
                stats["wins"] += 1
        for strategy, stats in strategy_performance.items():
            stats["win_rate"] = (
                (stats["wins"] / stats["trades"]) * 100 if stats["trades"] > 0 else 0
            )
            stats["avg_pnl"] = (
                stats["pnl"] / stats["trades"] if stats["trades"] > 0 else 0
            )
        optimization["current_system_analysis"][
            "strategy_effectiveness"
        ] = strategy_performance

        recommendations = []
        if strategy_performance:
            best_strategy = max(
                strategy_performance.items(), key=lambda x: x[1]["win_rate"]
            )
            worst_strategy = min(
                strategy_performance.items(), key=lambda x: x[1]["win_rate"]
            )
            if best_strategy[1]["win_rate"] > 60:
                recommendations.append(
                    {
                        "type": "strategy",
                        "action": "increase_allocation",
                        "target": best_strategy[0],
                        "reason": f"High win rate of {best_strategy[1]['win_rate']:.1f}%",
                        "expected_impact": "Increase overall system win rate",
                    }
                )
            if worst_strategy[1]["win_rate"] < 40:
                recommendations.append(
                    {
                        "type": "strategy",
                        "action": "reduce_allocation",
                        "target": worst_strategy[0],
                        "reason": f"Low win rate of {worst_strategy[1]['win_rate']:.1f}%",
                        "expected_impact": "Reduce drag on overall performance",
                    }
                )

        if win_rate < 50:
            recommendations.append(
                {
                    "type": "risk_management",
                    "action": "implement_stricter_stops",
                    "reason": f"Current win rate of {win_rate:.1f}% below target",
                    "expected_impact": "Reduce losses and improve risk-adjusted returns",
                }
            )

        recent_trades = sorted(
            all_trades, key=lambda x: x.timestamp or datetime.min, reverse=True
        )[:100]
        recent_win_rate = (
            len([t for t in recent_trades if (t.pnl or 0) > 0])
            / len(recent_trades)
            * 100
            if recent_trades
            else 0
        )
        if recent_win_rate < win_rate * 0.8:
            recommendations.append(
                {
                    "type": "market_adaptation",
                    "action": "reduce_position_sizes",
                    "reason": f"Recent performance ({recent_win_rate:.1f}%) significantly below average ({win_rate:.1f}%)",
                    "expected_impact": "Adapt to changing market conditions",
                }
            )

        optimization["optimization_recommendations"][
            "strategy_adjustments"
        ] = recommendations
        optimization["implementation_plan"]["priority_actions"] = [
            "Review and adjust strategy allocations based on performance data",
            "Implement recommended risk management changes",
            "Monitor market conditions and adapt position sizing",
            "Regular performance reviews and strategy optimization",
        ]
        optimization["implementation_plan"]["expected_improvements"] = {
            "win_rate_improvement": 5.0,
            "risk_reduction": 10.0,
            "pnl_improvement": 15.0,
        }

        return jsonify(optimization)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error in /api/admin/automated_strategy_optimization: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_analytics_bp.route("/user_activity_monitoring")
@admin_required
def api_admin_user_activity_monitoring():
    """Comprehensive user engagement and retention analytics."""
    try:
        all_users = User.query.all()
        all_trades = UserTrade.query.all()
        if not all_users:
            return (
                jsonify(
                    {
                        "error": "No user data available",
                        "activity_summary": {},
                        "user_engagement": {},
                        "timestamp": time.time(),
                    }
                ),
                404,
            )

        activity_report = {
            "activity_summary": {
                "total_users": len(all_users),
                "active_users": len([u for u in all_users if u.is_active]),
                "inactive_users": len([u for u in all_users if not u.is_active]),
                "admin_users": len([u for u in all_users if u.is_admin]),
                "total_trades": len(all_trades),
                "avg_trades_per_user": 0.0,
            },
            "user_engagement": {
                "login_patterns": {},
                "trading_activity": {},
                "engagement_scores": {},
                "user_segments": {},
            },
            "activity_metrics": {
                "daily_active_users": {},
                "weekly_active_users": {},
                "monthly_active_users": {},
                "session_duration": {},
            },
            "retention_analysis": {
                "user_retention": {},
                "churn_risk": {},
                "engagement_trends": {},
            },
            "timestamp": time.time(),
        }

        total_users = len(all_users)
        total_trades = len(all_trades)
        activity_report["activity_summary"]["avg_trades_per_user"] = (
            total_trades / total_users if total_users > 0 else 0
        )

        user_activity = {}
        for user in all_users:
            user_trades = [t for t in all_trades if t.user_id == user.id]
            trade_count = len(user_trades)
            engagement_score = 0
            if user.is_active:
                engagement_score += 20
            engagement_score += min(trade_count * 2, 30)
            if user.last_login:
                days_since_login = (datetime.now() - user.last_login).days
                if days_since_login < 7:
                    engagement_score += 25
                elif days_since_login < 30:
                    engagement_score += 15
                elif days_since_login < 90:
                    engagement_score += 5
            user_activity[user.username] = {
                "user_id": user.id,
                "trade_count": trade_count,
                "total_pnl": sum((t.pnl or 0) for t in user_trades),
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "engagement_score": engagement_score,
                "account_age_days": (
                    datetime.now() - (user.created_at or datetime.now())
                ).days,
            }
        activity_report["user_engagement"]["trading_activity"] = user_activity

        high = [u for u in user_activity.values() if u["engagement_score"] >= 50]
        medium = [u for u in user_activity.values() if 25 <= u["engagement_score"] < 50]
        low = [u for u in user_activity.values() if u["engagement_score"] < 25]
        activity_report["user_engagement"]["user_segments"] = {
            "high_engagement": {
                "count": len(high),
                "percentage": (len(high) / total_users) * 100 if total_users > 0 else 0,
                "avg_trades": sum(u["trade_count"] for u in high) / len(high)
                if high
                else 0,
            },
            "medium_engagement": {
                "count": len(medium),
                "percentage": (len(medium) / total_users) * 100
                if total_users > 0
                else 0,
                "avg_trades": sum(u["trade_count"] for u in medium) / len(medium)
                if medium
                else 0,
            },
            "low_engagement": {
                "count": len(low),
                "percentage": (len(low) / total_users) * 100 if total_users > 0 else 0,
                "avg_trades": sum(u["trade_count"] for u in low) / len(low)
                if low
                else 0,
            },
        }

        new_users_30 = len(
            [
                u
                for u in all_users
                if u.created_at and (datetime.now() - u.created_at).days <= 30
            ]
        )
        active_last_30 = len(
            [
                u
                for u in user_activity.values()
                if u["last_login"]
                and (datetime.now() - datetime.fromisoformat(u["last_login"])).days
                <= 30
            ]
        )
        activity_report["retention_analysis"]["user_retention"] = {
            "new_users_30_days": new_users_30,
            "active_users_30_days": active_last_30,
            "retention_rate_30_days": (active_last_30 / total_users) * 100
            if total_users > 0
            else 0,
            "churn_rate_estimated": ((total_users - active_last_30) / total_users) * 100
            if total_users > 0
            else 0,
        }

        churn_risk_users = [
            u
            for u in user_activity.values()
            if u["engagement_score"] < 20 and u["trade_count"] < 5
        ]
        activity_report["retention_analysis"]["churn_risk"] = {
            "at_risk_count": len(churn_risk_users),
            "at_risk_percentage": (len(churn_risk_users) / total_users) * 100
            if total_users > 0
            else 0,
            "recommendations": [
                "Send re-engagement emails to low-activity users",
                "Offer tutorials for users with low trade counts",
                "Implement welcome series for new users",
            ],
        }

        return jsonify(activity_report)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error in /api/admin/user_activity_monitoring: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_analytics_bp.route("/consolidated_pnl")
@admin_required
def api_admin_consolidated_pnl():
    """Consolidated profit/loss reporting across all users."""
    try:
        all_trades = UserTrade.query.all()
        if not all_trades:
            return (
                jsonify(
                    {
                        "error": "No trade data available for consolidated reporting",
                        "summary": {},
                        "breakdowns": {},
                        "timestamp": time.time(),
                    }
                ),
                404,
            )

        report = {
            "summary": {
                "total_trades": len(all_trades),
                "total_users": len(set(t.user_id for t in all_trades)),
                "total_pnl": 0.0,
                "total_volume": 0.0,
                "avg_trade_pnl": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "recovery_factor": 0.0,
            },
            "breakdowns": {
                "by_time_period": {},
                "by_strategy": {},
                "by_symbol": {},
                "by_user": {},
                "by_risk_level": {},
                "by_trade_type": {},
            },
            "performance_metrics": {
                "monthly_performance": [],
                "weekly_performance": [],
                "daily_performance": [],
                "hourly_performance": [],
            },
            "risk_metrics": {
                "volatility_analysis": {},
                "correlation_matrix": {},
                "value_at_risk": {},
                "expected_shortfall": {},
            },
            "timestamp": time.time(),
        }

        winning_trades = [t for t in all_trades if (t.pnl or 0) > 0]
        losing_trades = [t for t in all_trades if (t.pnl or 0) < 0]
        total_pnl = sum((t.pnl or 0) for t in all_trades)
        total_volume = sum((t.quantity or 0) * (t.entry_price or 0) for t in all_trades)
        report["summary"]["total_pnl"] = total_pnl
        report["summary"]["total_volume"] = total_volume
        report["summary"]["avg_trade_pnl"] = (
            total_pnl / len(all_trades) if all_trades else 0
        )
        report["summary"]["win_rate"] = (
            (len(winning_trades) / len(all_trades)) * 100 if all_trades else 0
        )
        total_wins = sum((t.pnl or 0) for t in winning_trades)
        total_losses = abs(sum((t.pnl or 0) for t in losing_trades))
        report["summary"]["profit_factor"] = (
            total_wins / total_losses if total_losses > 0 else float("inf")
        )

        now = datetime.now()
        time_periods = {
            "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
            "this_week": now - timedelta(days=7),
            "this_month": now - timedelta(days=30),
            "this_quarter": now - timedelta(days=90),
            "this_year": now - timedelta(days=365),
            "all_time": datetime.min,
        }
        for period_name, start_date in time_periods.items():
            period_trades = [
                t for t in all_trades if t.timestamp and t.timestamp >= start_date
            ]
            if period_trades:
                period_pnl = sum((t.pnl or 0) for t in period_trades)
                period_wins = len([t for t in period_trades if (t.pnl or 0) > 0])
                period_win_rate = (period_wins / len(period_trades)) * 100
                report["breakdowns"]["by_time_period"][period_name] = {
                    "trades": len(period_trades),
                    "pnl": period_pnl,
                    "win_rate": period_win_rate,
                    "avg_pnl": period_pnl / len(period_trades),
                    "volume": sum(
                        (t.quantity or 0) * (t.entry_price or 0) for t in period_trades
                    ),
                }

        strategy_stats = {}
        for trade in all_trades:
            strategy = trade.signal_source or "unknown"
            stats = strategy_stats.setdefault(
                strategy,
                {"trades": 0, "pnl": 0.0, "wins": 0, "volume": 0.0, "users": set()},
            )
            stats["trades"] += 1
            stats["pnl"] += trade.pnl or 0
            stats["volume"] += (trade.quantity or 0) * (trade.entry_price or 0)
            stats["users"].add(trade.user_id)
            if (trade.pnl or 0) > 0:
                stats["wins"] += 1
        for strategy, stats in strategy_stats.items():
            report["breakdowns"]["by_strategy"][strategy] = {
                "trades": stats["trades"],
                "pnl": stats["pnl"],
                "win_rate": (stats["wins"] / stats["trades"]) * 100
                if stats["trades"] > 0
                else 0,
                "avg_pnl": stats["pnl"] / stats["trades"] if stats["trades"] > 0 else 0,
                "volume": stats["volume"],
                "unique_users": len(stats["users"]),
                "user_adoption_rate": len(stats["users"])
                / report["summary"]["total_users"]
                * 100
                if report["summary"]["total_users"] > 0
                else 0,
            }

        symbol_stats = {}
        for trade in all_trades:
            symbol = trade.symbol or "UNKNOWN"
            stats = symbol_stats.setdefault(
                symbol,
                {"trades": 0, "pnl": 0.0, "wins": 0, "volume": 0.0, "users": set()},
            )
            stats["trades"] += 1
            stats["pnl"] += trade.pnl or 0
            stats["volume"] += (trade.quantity or 0) * (trade.entry_price or 0)
            stats["users"].add(trade.user_id)
            if (trade.pnl or 0) > 0:
                stats["wins"] += 1
        for symbol, stats in symbol_stats.items():
            report["breakdowns"]["by_symbol"][symbol] = {
                "trades": stats["trades"],
                "pnl": stats["pnl"],
                "win_rate": (stats["wins"] / stats["trades"]) * 100
                if stats["trades"] > 0
                else 0,
                "avg_pnl": stats["pnl"] / stats["trades"] if stats["trades"] > 0 else 0,
                "volume": stats["volume"],
                "unique_users": len(stats["users"]),
                "market_share": stats["volume"]
                / report["summary"]["total_volume"]
                * 100
                if report["summary"]["total_volume"] > 0
                else 0,
            }

        user_stats = {}
        for trade in all_trades:
            stats = user_stats.setdefault(
                trade.user_id,
                {
                    "trades": 0,
                    "pnl": 0.0,
                    "wins": 0,
                    "volume": 0.0,
                    "symbols": set(),
                    "strategies": set(),
                },
            )
            stats["trades"] += 1
            stats["pnl"] += trade.pnl or 0
            stats["volume"] += (trade.quantity or 0) * (trade.entry_price or 0)
            stats["symbols"].add(trade.symbol)
            stats["strategies"].add(trade.signal_source or "unknown")
            if (trade.pnl or 0) > 0:
                stats["wins"] += 1
        for user_id, stats in user_stats.items():
            user = db.session.get(User, user_id)
            username = user.username if user else f"User_{user_id}"
            report["breakdowns"]["by_user"][username] = {
                "user_id": user_id,
                "trades": stats["trades"],
                "pnl": stats["pnl"],
                "win_rate": (stats["wins"] / stats["trades"]) * 100
                if stats["trades"] > 0
                else 0,
                "avg_pnl": stats["pnl"] / stats["trades"] if stats["trades"] > 0 else 0,
                "volume": stats["volume"],
                "symbols_traded": len(stats["symbols"]),
                "strategies_used": len(stats["strategies"]),
                "activity_score": stats["trades"]
                / report["summary"]["total_trades"]
                * 100
                if report["summary"]["total_trades"] > 0
                else 0,
            }

        for trade in all_trades:
            trade_value = (trade.quantity or 0) * (trade.entry_price or 0)
            portfolio = UserPortfolio.query.filter_by(user_id=trade.user_id).first()
            portfolio_value = portfolio.total_balance if portfolio else 10000
            risk_percentage = (
                (trade_value / portfolio_value) * 100 if portfolio_value > 0 else 0
            )
            if risk_percentage <= 1:
                risk_level = "low"
            elif risk_percentage <= 5:
                risk_level = "medium"
            elif risk_percentage <= 10:
                risk_level = "high"
            else:
                risk_level = "extreme"
            stats = report["breakdowns"]["by_risk_level"].setdefault(
                risk_level,
                {
                    "trades": 0,
                    "pnl": 0.0,
                    "wins": 0,
                    "avg_risk": 0.0,
                },
            )
            stats["trades"] += 1
            stats["pnl"] += trade.pnl or 0
            stats["avg_risk"] += risk_percentage
            if (trade.pnl or 0) > 0:
                stats["wins"] += 1
        for stats in report["breakdowns"]["by_risk_level"].values():
            if stats["trades"] > 0:
                stats["win_rate"] = (stats["wins"] / stats["trades"]) * 100
                stats["avg_risk"] = stats["avg_risk"] / stats["trades"]
                stats["avg_pnl"] = stats["pnl"] / stats["trades"]

        trade_types = {}
        for trade in all_trades:
            trade_type = trade.trade_type or "manual"
            stats = trade_types.setdefault(
                trade_type, {"trades": 0, "pnl": 0.0, "wins": 0, "volume": 0.0}
            )
            stats["trades"] += 1
            stats["pnl"] += trade.pnl or 0
            stats["volume"] += (trade.quantity or 0) * (trade.entry_price or 0)
            if (trade.pnl or 0) > 0:
                stats["wins"] += 1
        for trade_type, stats in trade_types.items():
            report["breakdowns"]["by_trade_type"][trade_type] = {
                "trades": stats["trades"],
                "pnl": stats["pnl"],
                "win_rate": (stats["wins"] / stats["trades"]) * 100
                if stats["trades"] > 0
                else 0,
                "avg_pnl": stats["pnl"] / stats["trades"] if stats["trades"] > 0 else 0,
                "volume": stats["volume"],
                "percentage": stats["trades"] / report["summary"]["total_trades"] * 100
                if report["summary"]["total_trades"] > 0
                else 0,
            }

        if len(all_trades) > 1:
            returns = [trade.pnl or 0 for trade in all_trades]
            avg_return = sum(returns) / len(returns)
            std_dev = (
                sum((r - avg_return) ** 2 for r in returns) / len(returns)
            ) ** 0.5
            report["summary"]["sharpe_ratio"] = (
                avg_return / std_dev if std_dev > 0 else 0
            )

        cumulative_pnl = 0
        peak = 0
        max_drawdown = 0
        for trade in sorted(all_trades, key=lambda x: x.timestamp or datetime.min):
            cumulative_pnl += trade.pnl or 0
            peak = max(peak, cumulative_pnl)
            drawdown = peak - cumulative_pnl
            max_drawdown = max(max_drawdown, drawdown)
        report["summary"]["max_drawdown"] = max_drawdown
        report["summary"]["recovery_factor"] = (
            total_pnl / max_drawdown if max_drawdown > 0 else float("inf")
        )

        return jsonify(report)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error in /api/admin/consolidated_pnl: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_analytics_bp.route("/dashboard")
@admin_required
def api_admin_dashboard():
    """Admin dashboard showing aggregated system data."""
    try:
        ctx = _ctx()
        dashboard_data = _dashboard_data(ctx)
        strategy_manager = ctx.get("strategy_manager")

        all_users = User.query.all()
        total_users = len(all_users)
        active_users = len([u for u in all_users if u.is_active])
        admin_users = len([u for u in all_users if u.is_admin])

        all_portfolios = UserPortfolio.query.all()
        total_portfolio_value = 0
        total_pnl = 0
        total_positions = len(all_portfolios)
        symbol_exposure = {}
        for portfolio in all_portfolios:
            current_value = (
                portfolio.quantity * (portfolio.current_price or portfolio.avg_price)
                if hasattr(portfolio, "quantity")
                else 0
            )
            current_value = current_value or 0
            total_portfolio_value += current_value
            total_pnl += portfolio.pnl or 0
            symbol = getattr(portfolio, "symbol", None)
            if symbol:
                symbol_exposure[symbol] = symbol_exposure.get(symbol, 0) + current_value

        all_trades = UserTrade.query.all()
        total_trades = len(all_trades)
        winning_trades = len([t for t in all_trades if (t.pnl or 0) > 0])
        losing_trades = len([t for t in all_trades if (t.pnl or 0) < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_trade_pnl = (
            sum((t.pnl or 0) for t in all_trades) / total_trades
            if total_trades > 0
            else 0
        )

        recent_trades = (
            UserTrade.query.order_by(UserTrade.timestamp.desc()).limit(50).all()
        )
        recent_trades_data = []
        for trade in recent_trades:
            user = db.session.get(User, trade.user_id)
            recent_trades_data.append(
                {
                    "id": trade.id,
                    "user_id": trade.user_id,
                    "username": user.username if user else "Unknown",
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.entry_price,
                    "pnl": trade.pnl,
                    "status": trade.status,
                    "trade_type": trade.trade_type,
                    "timestamp": trade.timestamp.isoformat()
                    if trade.timestamp
                    else None,
                }
            )

        user_performance = {}
        for user in all_users:
            user_trades = UserTrade.query.filter_by(user_id=user.id).all()
            user_pnl = sum((t.pnl or 0) for t in user_trades)
            user_trades_count = len(user_trades)
            user_performance[user.id] = {
                "username": user.username,
                "total_pnl": user_pnl,
                "trades_count": user_trades_count,
                "win_rate": len([t for t in user_trades if (t.pnl or 0) > 0])
                / user_trades_count
                * 100
                if user_trades_count > 0
                else 0,
            }
        top_performers = sorted(
            user_performance.values(), key=lambda x: x["total_pnl"], reverse=True
        )[:10]

        max_symbol_exposure = max(symbol_exposure.values()) if symbol_exposure else 0
        concentration_risk = (
            (max_symbol_exposure / total_portfolio_value * 100)
            if total_portfolio_value > 0
            else 0
        )
        if concentration_risk > 50:
            system_risk_level = "high"
        elif concentration_risk > 25:
            system_risk_level = "medium"
        else:
            system_risk_level = "low"

        return jsonify(
            {
                "summary": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "admin_users": admin_users,
                    "total_portfolio_value": total_portfolio_value,
                    "total_pnl": total_pnl,
                    "total_positions": total_positions,
                    "total_trades": total_trades,
                    "win_rate": win_rate,
                    "avg_trade_pnl": avg_trade_pnl,
                    "concentration_risk": concentration_risk,
                    "system_risk_level": system_risk_level,
                },
                "trade_statistics": {
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades,
                    "break_even_trades": total_trades - winning_trades - losing_trades,
                    "win_rate_percent": win_rate,
                    "avg_pnl_per_trade": avg_trade_pnl,
                },
                "symbol_exposure": symbol_exposure,
                "top_performers": top_performers,
                "recent_trades": recent_trades_data,
                "system_status": dashboard_data.get("system_status", {}),
                "strategy_performance": strategy_manager.get_all_performance()
                if strategy_manager
                else {},
                "timestamp": time.time(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error in /api/admin/dashboard: {exc}")
        return jsonify({"error": str(exc)}), 500
