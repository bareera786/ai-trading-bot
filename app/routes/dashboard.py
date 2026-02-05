"""Dashboard UI and status endpoints."""
from __future__ import annotations

import random
import time
from typing import Any, Optional

import os
import json

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required


dashboard_bp = Blueprint("dashboard_bp", __name__)


def _extract_price(market_payload: Any) -> float | None:
    if not isinstance(market_payload, dict):
        return None
    for key in ("price", "last_price", "lastPrice", "current_price", "close"):
        value = market_payload.get(key)
        try:
            if value is None:
                continue
            return float(value)
        except Exception:
            continue
    return None


def _get_user_traders_from_market_service(
    ctx: dict[str, Any], user_id: int | str
) -> tuple[Any | None, Any | None]:
    market_service = ctx.get("market_data_service")
    getter = getattr(market_service, "_get_or_create_user_traders", None)
    if callable(getter):
        try:
            ultimate, optimized = getter(user_id)
            return ultimate, optimized
        except Exception:
            return None, None
    return None, None


def _build_user_portfolio(
    trader: Any,
    *,
    ctx: dict[str, Any],
    dashboard_data: dict[str, Any],
) -> dict[str, Any]:
    get_portfolio = getattr(trader, "get_portfolio_summary", None)
    if not callable(get_portfolio):
        return {}

    symbols: set[str] = set()
    try:
        positions = getattr(trader, "positions", {}) or {}
        if isinstance(positions, dict):
            symbols.update(str(s).upper() for s in positions.keys())
    except Exception:
        pass

    market_service = ctx.get("market_data_service")
    market_fn = getattr(market_service, "get_real_market_data", None)
    if not callable(market_fn):
        market_fn = ctx.get("get_real_market_data")

    prices: dict[str, float] = {}
    if callable(market_fn):
        for symbol in sorted(symbols):
            try:
                payload = market_fn(symbol)
                price = _extract_price(payload)
                if price is not None:
                    prices[symbol] = price
            except Exception:
                continue

    try:
        return get_portfolio(prices) or {}
    except Exception:
        return {}


def _build_user_performance(trader: Any) -> dict[str, Any]:
    get_perf = getattr(trader, "get_performance_summary", None)
    if callable(get_perf):
        try:
            return get_perf() or {}
        except Exception:
            return {}
    try:
        metrics = getattr(trader, "performance_metrics", None)
        return dict(metrics) if isinstance(metrics, dict) else {}
    except Exception:
        return {}


def _build_user_system_status(
    trader: Any,
    *,
    base_status: dict[str, Any],
) -> dict[str, Any]:
    # Start from existing status shape (keeps UI compatibility), but overwrite
    # sensitive/user-specific fields with values from the current user's trader.
    status = dict(base_status or {})
    try:
        status["trading_enabled"] = bool(getattr(trader, "trading_enabled", False))
    except Exception:
        pass
    try:
        status["paper_trading"] = bool(getattr(trader, "paper_trading", True))
    except Exception:
        pass
    try:
        status["real_trading_ready"] = bool(
            getattr(trader, "real_trading_enabled", False)
        )
    except Exception:
        pass
    try:
        status["futures_trading_ready"] = bool(
            getattr(trader, "futures_trading_enabled", False)
            and getattr(trader, "futures_trader", None)
        )
        status["futures_trading_enabled"] = bool(
            getattr(trader, "futures_trading_enabled", False)
        )
        status["futures_enabled"] = bool(
            getattr(trader, "futures_trading_enabled", False)
        )
    except Exception:
        pass
    try:
        trades = getattr(trader, "trade_history", None)
        get_history = getattr(trades, "get_trade_history", None)
        if callable(get_history):
            history = get_history() or []
            if history:
                status["last_trade"] = history[-1]
    except Exception:
        pass
    return status


def _build_user_journal_events(trader: Any, limit: int = 10) -> list[dict[str, Any]]:
    try:
        trade_history = getattr(trader, "trade_history", None)
        getter = getattr(trade_history, "get_journal_events", None)
        if callable(getter):
            events = getter(limit=limit) or []
            return events if isinstance(events, list) else []
    except Exception:
        pass
    return []


def _get_ai_bot_context() -> dict[str, Any]:
    """Get AI bot context, with fallback for when it's not fully initialized."""
    ctx = current_app.extensions.get("ai_bot_context")
    if not ctx:
        # Return and register a minimal context so other routes (e.g., trading)
        # can share state in lightweight test or limited setups.
        current_app.logger.warning(
            "⚠️ AI bot context not fully initialized, registering minimal fallback"
        )
        # Provide minimal test-friendly services
        from app.services.test_fallbacks import (
            InMemoryCredentialsStore,
            SimpleLogManager,
            FallbackTrader,
            default_apply_credentials,
            default_get_status,
        )

        fallback = {
            "version_label": "Ultimate AI Bot (Limited Mode)",
            "ai_bot_version": "Ultimate AI Bot (Limited Mode)",
            "dashboard_data": {
                "system_status": {},
                "optimized_system_status": {},
                "performance": {},
                "portfolio": {},
            },
            # Minimal services so endpoints can operate during tests
            "binance_credentials_store": InMemoryCredentialsStore(),
            "binance_log_manager": SimpleLogManager(),
            "apply_binance_credentials": default_apply_credentials,
            "get_binance_credential_status": default_get_status,
            "ultimate_trader": FallbackTrader(),
            "optimized_trader": FallbackTrader(),
        }
        # Store fallback in extensions so other modules access same object
        current_app.extensions["ai_bot_context"] = fallback
        return fallback
    return ctx


def _get_dashboard_data(ctx: dict[str, Any]) -> dict[str, Any]:
    # Try fetching from Redis first (Process Isolation Fix)
    try:
        redis_client = ctx.get("redis_client")
        if not redis_client:
            # Try getting from extensions or app config
            import redis
            redis_url = current_app.config.get("REDIS_URL", "redis://redis:6379/0")
            redis_client = redis.from_url(redis_url)
        
        if redis_client:
            cached_summ = redis_client.get("dashboard:global_state")
            if cached_summ:
                return json.loads(cached_summ)
    except Exception as e:
        # print(f"Redis fetch error: {e}")
        pass

    data = ctx.get("dashboard_data")
    if data is None:
        # Return empty dict instead of raising to prevent 500s during startup
        return {} 
    return data


def _callable_value(ctx: dict[str, Any], key: str, default: Any = None) -> Any:
    value = ctx.get(key)
    if callable(value):
        return value()
    return value if value is not None else default


def _indicator_profiles(ctx: dict[str, Any]) -> set[str]:
    profiles = _callable_value(ctx, "indicator_profiles", []) or []
    return {str(profile).strip().lower() for profile in profiles}


def _normalize_indicator_profile(
    raw_profile: Any, ctx: dict[str, Any]
) -> Optional[str]:
    if not raw_profile:
        return None
    profile = str(raw_profile).strip().lower()
    return profile if profile in _indicator_profiles(ctx) else None


def _ctx_value(ctx: dict[str, Any], key: str, default: Any = None) -> Any:
    value = ctx.get(key)
    return value if value is not None else default


def _ctx_trader(ctx: dict[str, Any], key: str):
    return ctx.get(key)


def _ctx_ml_system(ctx: dict[str, Any], key: str):
    return ctx.get(key)


@dashboard_bp.route("/dashboard")
@login_required
def dashboard():
    ctx = _get_ai_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    version_label = (
        ctx.get("version_label") or ctx.get("ai_bot_version") or "Ultimate AI Bot"
    )
    ribs_optimization = dashboard_data.get("ribs_optimization", {})
    response = make_response(
        render_template(
            "dashboard.html",
            version_label=version_label,
            ribs_optimization=ribs_optimization,
            current_time=int(time.time()),
        )
    )
    response.headers[
        "Cache-Control"
    ] = "no-cache, no-store, must-revalidate, max-age=0, private, no-transform"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@dashboard_bp.route("/ribs", endpoint="ribs_dashboard")
@login_required
def ribs_dashboard():
    ctx = _get_ai_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    version_label = (
        ctx.get("version_label") or ctx.get("ai_bot_version") or "Ultimate AI Bot"
    )
    ribs_optimization = dashboard_data.get("ribs_optimization", {})

    # If there is no live in-process ribs_optimization payload, try to read
    # a cross-process status file so the dashboard can show archive/progress
    # information even when the optimizer runs in another process.
    if not ribs_optimization:
        from app.services.pathing import resolve_profile_path
        
        # Try profile-aware path first (where worker writes)
        persistence_dir = resolve_profile_path("bot_persistence")
        status_path = os.path.join(persistence_dir, "ribs_checkpoints", "ribs_status.json")
        
        # Fallback to legacy path if not found
        if not os.path.exists(status_path):
             status_path = os.path.join("bot_persistence", "ribs_checkpoints", "ribs_status.json")
             
        try:
            if os.path.exists(status_path):
                with open(status_path, "r") as sf:
                    status = json.load(sf)
                # Map the status file into a shape compatible with the template
                ribs_optimization = {
                    "coverage": status.get("archive_stats", {}).get("coverage", 0),
                    "num_elites": status.get("archive_stats", {}).get("num_elites", 0),
                    "best_objective": status.get("archive_stats", {}).get(
                        "best_objective", 0
                    ),
                    "qd_score": status.get("archive_stats", {}).get("qd_score", 0),
                    "elite_strategies": status.get("archive_stats", {}).get(
                        "elites", []
                    )
                    or [],
                    # leave behaviors/objectives empty if not present
                }
        except Exception:
            # Fail silently; the page will still render with empty data
            ribs_optimization = ribs_optimization or {}
    response = make_response(
        render_template(
            "ribs_dashboard.html",
            version_label=version_label,
            ribs_optimization=ribs_optimization,
            is_full_page=True,
        )
    )
    response.headers[
        "Cache-Control"
    ] = "no-cache, no-store, must-revalidate, max-age=0, private, no-transform"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@dashboard_bp.route("/market-data", endpoint="market_data")
@login_required
def market_data():
    """Market Data page showing real-time prices, order book, and execution phases."""
    ctx = _get_ai_bot_context()
    version_label = (
        ctx.get("version_label") or ctx.get("ai_bot_version") or "Ultimate AI Bot"
    )
    
    response = make_response(
        render_template(
            "market_data.html",
            version_label=version_label,
            current_time=int(time.time()),
        )
    )
    response.headers[
        "Cache-Control"
    ] = "no-cache, no-store, must-revalidate, max-age=0, private, no-transform"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


# Placeholder pages for navigation items
@dashboard_bp.route("/symbols", endpoint="symbols_list")
@login_required
def symbols_list():
    """Symbols list page."""
    return render_template("symbols_list.html")


@dashboard_bp.route("/analytics/statistics", endpoint="statistics")
@login_required
def statistics():
    """Statistics page."""
    return render_template("statistics.html")


@dashboard_bp.route("/analytics/qfm", endpoint="qfm_analytics")
@login_required
def qfm_analytics():
    """QFM Analytics page."""
    return render_template("qfm_analytics.html")


@dashboard_bp.route("/analytics/ml-telemetry", endpoint="ml_telemetry")
@login_required
def ml_telemetry():
    """ML Telemetry page."""
    return render_template("ml_telemetry.html")


@dashboard_bp.route("/analytics/model-comparison", endpoint="model_comparison")
@login_required
def model_comparison():
    """ML Model Comparison page."""
    return render_template("analytics/model_comparison.html", active_page="model-comparison")


@dashboard_bp.route("/trading/spot", endpoint="spot_trading")
@login_required
def spot_trading():
    """Spot Trading page."""
    return render_template("spot_trading.html")


@dashboard_bp.route("/trading/futures", endpoint="futures_trading")
@login_required
def futures_trading():
    """Futures Trading page."""
    return render_template("futures_trading.html")


@dashboard_bp.route("/trading/strategies", endpoint="strategies")
@login_required
def strategies():
    """Strategies page."""
    return render_template("strategies.html")


@dashboard_bp.route("/trading/crt-signals", endpoint="crt_signals")
@login_required
def crt_signals():
    """CRT Signals page."""
    return render_template("crt_signals.html")


@dashboard_bp.route("/trades/history", endpoint="trade_history")
@login_required
def trade_history():
    """Trade History page."""
    return render_template("trade_history.html")


@dashboard_bp.route("/trading/journal", endpoint="trade_journal")
@login_required
def trade_journal():
    """Trade Journal page."""
    return render_template("analytics/trade_journal.html", active_page="trade-journal")


@dashboard_bp.route("/api/trades", endpoint="api_recent_trades")
@login_required
def api_recent_trades():
    """Return paginated trade history for the current user."""
    # Import here to avoid circular dependencies if any
    from app.models import UserTrade
    from app.routes.user_api import normalize_trade_to_canonical
    from datetime import datetime, timedelta

    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("limit", 20, type=int)
        symbol = request.args.get("symbol")
        days = request.args.get("days", type=int)
        execution_mode = request.args.get("execution_mode")

        query = UserTrade.query.filter_by(user_id=current_user.id)
        if symbol:
            query = query.filter(UserTrade.symbol == symbol)
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            query = query.filter(UserTrade.timestamp >= cutoff)
        if execution_mode:
            query = query.filter(UserTrade.execution_mode == execution_mode)

        # Sort by timestamp desc
        query = query.order_by(UserTrade.timestamp.desc())
        
        # Optimize count queries
        total_trades = query.with_entities(UserTrade.id).count()
        trades = query.offset((page - 1) * per_page).limit(per_page).all()

        trades_data = [normalize_trade_to_canonical(trade) for trade in trades]

        return jsonify(
            {
                "trades": trades_data,
                "total_trades": total_trades,
                "current_page": page,
                "total_pages": max(1, (total_trades + per_page - 1) // per_page),
                "per_page": per_page,
                "user_id": current_user.id,
                "timestamp": time.time(),
            }
        )
    except Exception as exc:
        print(f"Error in /api/trades: {exc}")
        # Return empty list instead of 500 to keep UI alive
        return jsonify({"trades": [], "error": str(exc), "total_trades": 0})



@dashboard_bp.route("/backtest", endpoint="backtest_lab")
@login_required
def backtest_lab():
    """Backtest Lab page."""
    return render_template("backtest_lab.html")


@dashboard_bp.route("/backtesting", endpoint="backtesting")
@login_required
def backtesting():
    """Enhanced Backtesting page."""
    return render_template("backtesting.html", active_page="backtesting")


@dashboard_bp.route("/settings/safety", endpoint="safety_settings")
@login_required
def safety_settings():
    """Safety Settings page."""
    return render_template("safety_settings.html")


@dashboard_bp.route("/settings/api-keys", endpoint="api_keys")
@login_required
def api_keys():
    """Unified Exchange & Assets page."""
    return render_template("settings/exchange_assets.html")


@dashboard_bp.route("/settings/notifications", endpoint="notification_settings")
@login_required
def notification_settings():
    """Notification Settings page."""
    return render_template("settings/notifications.html")


@dashboard_bp.route("/settings/risk-presets", endpoint="risk_presets_settings")
@login_required
def risk_presets_settings():
    """Risk Presets Settings page."""
    return render_template("settings/risk_presets.html", active_page="risk-presets")


@dashboard_bp.route("/settings/subscription", endpoint="user_subscription")
@login_required
def user_subscription():
    """User Subscription Management page."""
    from app.models import UserTrade
    from datetime import datetime, timedelta
    
    # 1. Get Subscription Details
    sub = current_user.active_subscription
    plan = sub.plan if sub else None
    
    # 2. Get Quota/Limits
    quota = current_user.quota
    limits = {
        "max_bots": quota.get("max_concurrent_bots", 1),
        "max_trades": quota.get("max_trades_daily", 50)
    }
    
    # 3. Calculate Usage
    # Daily trades (UTC)
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_trades_count = UserTrade.query.filter(
        UserTrade.user_id == current_user.id,
        UserTrade.timestamp >= start_of_day
    ).count()
    
    # Active bots (Approximation from dashboard data or DB)
    # For now, we'll assume 0 or fetch from context if available
    ctx = _get_ai_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    # This is a bit tricky as dashboard_data is global or specific? 
    # Let's rely on a simple placeholder or the dashboard's system status for now
    system_status = dashboard_data.get("system_status", {})
    # If the user is running bots locally, this might be accurate. 
    # If multi-user, we need a better way. 
    # Let's just use 0 as placeholder or try to infer.
    active_bots_count = 0 
    
    usage = {
        "active_bots": active_bots_count,
        "daily_trades": daily_trades_count
    }

    return render_template(
        "settings/user_subscription.html", 
        active_page="settings",
        subscription=sub,
        plan=plan,
        limits=limits,
        usage=usage
    )


@dashboard_bp.route("/dashboard/subscription/confirm", endpoint="confirm_subscription_change")
@login_required
def confirm_subscription_change():
    """Handle plan switch confirmation (Mock Payment Flow)."""
    from app.models import SubscriptionPlan
    from app.subscriptions.helpers import assign_subscription_to_user
    from app.extensions import db

    plan_code = request.args.get("plan")
    if not plan_code:
        return redirect(url_for("marketing.pricing"))
        
    plan = SubscriptionPlan.query.filter_by(code=plan_code).first()
    if not plan:
        # Flash error here if we had msg flashing
        return redirect(url_for("marketing.pricing"))
        
    # In a real app, this would redirect to Stripe/PayPal
    # Here we just instantly assign the plan (Free/Mock)
    try:
        assign_subscription_to_user(
            current_user,
            plan,
            cancel_existing=True,
            notes="User switched via Dashboard"
        )
        db.session.commit()
    except Exception as e:
        print(f"Error switching plan: {e}")
        
    return redirect(url_for("dashboard_bp.user_subscription"))


@dashboard_bp.route("/journal", endpoint="trading_journal")
@login_required
def trading_journal():
    """Trading Journal page."""
    return render_template("trading_journal.html")


@dashboard_bp.route("/system/persistence", endpoint="persistence_dashboard")
@login_required
def persistence_dashboard():
    """Persistence Dashboard page."""
    return render_template("persistence_dashboard.html")


@dashboard_bp.route("/admin/settings", endpoint="admin_settings")
@login_required
def admin_settings():
    """Admin Settings page."""
    return render_template("admin_settings.html")


@dashboard_bp.route("/health", endpoint="health_monitor")
@login_required
def health_monitor():
    """System Health Monitor page."""
    return render_template("health.html")


@dashboard_bp.route("/dashboard", endpoint="dashboard_redirect")

@login_required
def dashboard_redirect():
    return redirect(url_for("dashboard_bp.dashboard"))


@dashboard_bp.route("/api/indicator_options", endpoint="api_indicator_options")
def api_indicator_options():
    ctx = _get_ai_bot_context()
    if getattr(current_user, "is_authenticated", False):
        get_all_selections = ctx.get("get_all_indicator_selections")
        selections = get_all_selections() if callable(get_all_selections) else {}
        return jsonify(
            {
                "options": ctx.get("indicator_signal_options", []),
                "selections": selections,
                "timestamp": time.time(),
            }
        )

    refresher = ctx.get("refresh_indicator_dashboard_state")
    if callable(refresher):
        refresher()
    dashboard_data = _get_dashboard_data(ctx)
    return jsonify(
        {
            "options": ctx.get("indicator_signal_options", []),
            "selections": dashboard_data.get("indicator_selections", {}),
            "timestamp": time.time(),
        }
    )


@dashboard_bp.route(
    "/api/indicator_selection", methods=["GET"], endpoint="api_get_indicator_selection"
)
def api_get_indicator_selection():
    ctx = _get_ai_bot_context()
    profile = _normalize_indicator_profile(request.args.get("profile"), ctx)

    get_selection = ctx.get("get_indicator_selection")
    get_all_selections = ctx.get("get_all_indicator_selections")

    if getattr(current_user, "is_authenticated", False):
        if profile and callable(get_selection):
            return jsonify({"profile": profile, "selections": get_selection(profile)})

        if callable(get_all_selections):
            return jsonify({"selections": get_all_selections()})

        return jsonify({"selections": {}})

    if profile and callable(get_selection):
        return jsonify({"profile": profile, "selections": get_selection(profile)})

    if callable(get_all_selections):
        return jsonify({"selections": get_all_selections()})

    dashboard_data = _get_dashboard_data(ctx)
    return jsonify({"selections": dashboard_data.get("indicator_selections", {})})


@dashboard_bp.route(
    "/api/indicator_selection", methods=["POST"], endpoint="api_set_indicator_selection"
)
@login_required
def api_set_indicator_selection():
    ctx = _get_ai_bot_context()
    payload = request.get_json(silent=True) or {}
    profile = _normalize_indicator_profile(payload.get("profile") or "ultimate", ctx)

    if not profile:
        return jsonify({"error": "Invalid profile specified"}), 400

    options = ctx.get("indicator_signal_options", [])

    if payload.get("select_all"):
        selections = options
    elif payload.get("select_none"):
        selections = []
    else:
        selections = payload.get("selections")

    if selections is None:
        return jsonify({"error": "No selections provided"}), 400

    if not isinstance(selections, (list, tuple, set)):
        return jsonify({"error": "Selections must be a list"}), 400

    setter = ctx.get("set_indicator_selection")
    if callable(setter):
        updated = setter(profile, selections)
    else:
        updated = list(selections)

    if getattr(current_user, "is_authenticated", False):
        get_all_selections = ctx.get("get_all_indicator_selections")
        selections_snapshot = (
            get_all_selections() if callable(get_all_selections) else {}
        )
        return jsonify(
            {
                "profile": profile,
                "selections": updated,
                "options": options,
                "indicator_selections": selections_snapshot,
                "message": f"Indicator selection updated for {profile}",
            }
        )

    refresher = ctx.get("refresh_indicator_dashboard_state")
    if callable(refresher):
        refresher()

    dashboard_data = _get_dashboard_data(ctx)

    return jsonify(
        {
            "profile": profile,
            "selections": updated,
            "options": options,
            "indicator_selections": dashboard_data.get("indicator_selections", {}),
            "message": f"Indicator selection updated for {profile}",
        }
    )


@dashboard_bp.route("/api/status", endpoint="api_status")
@login_required
def api_status():
    ctx = _get_ai_bot_context()
    user_trader_factory = ctx.get("get_user_trader")

    if not callable(user_trader_factory):
        return jsonify({"error": "User trader factory unavailable"}), 500

    try:
        user_trader = user_trader_factory(current_user.id, "ultimate")
        return jsonify(
            {
                "portfolio": {},
                "performance": {},
                "system_status": {
                    "trading_enabled": getattr(user_trader, "trading_enabled", False),
                    "paper_trading": getattr(user_trader, "paper_trading", True),
                    "real_trading_enabled": getattr(
                        user_trader, "real_trading_enabled", False
                    ),
                    "user_id": current_user.id,
                },
                "last_update": time.time(),
            }
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error in /api/status: {exc}")
        return jsonify({"error": str(exc)}), 500


@dashboard_bp.route("/api/safety_status", endpoint="api_safety_status")
@login_required
def api_safety_status():
    ctx = _get_ai_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    return jsonify(
        {
            "ultimate": dashboard_data.get("safety_status", {}),
            "optimized": dashboard_data.get("optimized_safety_status", {}),
            "last_update": dashboard_data.get("last_update"),
        }
    )


@dashboard_bp.route("/api/real_trading_status", endpoint="api_real_trading_status")
@login_required
def api_real_trading_status():
    ctx = _get_ai_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    return jsonify(
        {
            "ultimate": dashboard_data.get("real_trading_status", {}),
            "optimized": dashboard_data.get("optimized_real_trading_status", {}),
            "last_update": dashboard_data.get("last_update"),
        }
    )


@dashboard_bp.route("/api/dashboard", endpoint="api_dashboard_overview")
@login_required
def api_dashboard_overview():
    ctx = _get_ai_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    indicator_options = ctx.get("indicator_signal_options", [])

    get_all_selections = ctx.get("get_all_indicator_selections")
    indicator_selections = get_all_selections() if callable(get_all_selections) else {}

    binance_logs: list[dict[str, Any]] = []
    binance_credentials: dict[str, Any] = {}
    status_fn = ctx.get("get_binance_credential_status")
    if callable(status_fn):
        try:
            try:
                status = status_fn(
                    include_connection=True,
                    include_logs=True,
                    user_id=getattr(current_user, "id", None),
                )
            except TypeError:
                status = status_fn(
                    include_logs=True,
                    user_id=getattr(current_user, "id", None),
                )

            if isinstance(status, dict):
                binance_credentials = status
                raw_logs = status.get("logs", [])
                binance_logs = raw_logs if isinstance(raw_logs, list) else []
        except Exception:
            binance_logs = []
            binance_credentials = {}

    # Multi-user isolation hardening:
    # Never return shared dashboard_data fields that reflect another user's
    # state. When the MarketDataService supports per-user traders, derive the
    # sensitive dashboard sections from the current user's trader instances.
    ultimate_trader = None
    optimized_trader = None
    ultimate_trader = None
    optimized_trader = None
    user_id = getattr(current_user, "id", None)
    
    if user_id:
        ultimate_trader, optimized_trader = _get_user_traders_from_market_service(
            ctx, user_id
        )

    system_status = dashboard_data.get("system_status", {})
    performance = dashboard_data.get("performance", {})
    portfolio = dashboard_data.get("portfolio", {})
    optimized_system_status = dashboard_data.get("optimized_system_status", {})
    optimized_performance = dashboard_data.get("optimized_performance", {})
    optimized_portfolio = dashboard_data.get("optimized_portfolio", {})
    journal_events = dashboard_data.get("journal_events", [])[:10]

    if ultimate_trader is not None:
        system_status = _build_user_system_status(
            ultimate_trader, base_status=system_status
        )
        performance = _build_user_performance(ultimate_trader)
        portfolio = _build_user_portfolio(
            ultimate_trader, ctx=ctx, dashboard_data=dashboard_data
        )
        journal_events = _build_user_journal_events(ultimate_trader, limit=10)

    if optimized_trader is not None:
        optimized_system_status = _build_user_system_status(
            optimized_trader, base_status=optimized_system_status
        )
        optimized_performance = _build_user_performance(optimized_trader)
        optimized_portfolio = _build_user_portfolio(
            optimized_trader, ctx=ctx, dashboard_data=dashboard_data
        )

    return jsonify(
        {
            "user": {
                "username": getattr(current_user, "username", "unknown"),
                "is_admin": getattr(current_user, "is_admin", False),
            },
            "system_status": system_status,
            "performance": performance,
            "portfolio": portfolio,
            "last_update": dashboard_data.get("last_update"),
            "optimized_system_status": optimized_system_status,
            "optimized_performance": optimized_performance,
            "optimized_portfolio": optimized_portfolio,
            "safety_status": dashboard_data.get("safety_status", {}),
            "optimized_safety_status": dashboard_data.get(
                "optimized_safety_status", {}
            ),
            "real_trading_status": dashboard_data.get("real_trading_status", {}),
            "optimized_real_trading_status": dashboard_data.get(
                "optimized_real_trading_status", {}
            ),
            "backtest_results": dashboard_data.get("backtest_results", {}),
            "journal_events": journal_events,
            "futures_dashboard": dashboard_data.get("futures_dashboard", {}),
            "futures_manual": dashboard_data.get("futures_manual", {}),
            "indicator_options": indicator_options,
            "indicator_selections": indicator_selections,
            "binance_credentials": binance_credentials,
            "binance_logs": binance_logs,
            "ml_telemetry": dashboard_data.get("ml_telemetry", {}),
            "health_report": dashboard_data.get("health_report", {}),
        }
    )


@dashboard_bp.route("/api/phases", endpoint="api_phases")
@login_required
def api_phases():
    """Return lightweight per-symbol execution phase telemetry."""
    ctx = _get_ai_bot_context()

    phases: dict[str, Any] = {}
    phase_order: list[str] = []

    # Preferred: MarketDataService phase snapshot (live in-process).
    market_service = ctx.get("market_data_service")
    snapshot_fn = getattr(market_service, "get_phase_snapshot", None)
    order_fn = getattr(market_service, "get_phase_order", None)
    if callable(snapshot_fn):
        try:
            phases = snapshot_fn() or {}
        except Exception:
            phases = {}

    if callable(order_fn):
        try:
            phase_order = list(order_fn() or [])
        except Exception:
            phase_order = []

    # Optional: filter to the current user's trading universe when available.
    # (Best-effort only; fall back to returning all phases.)
    if getattr(current_user, "is_authenticated", False) and phases:
        get_universe = ctx.get("get_user_trading_universe")
        if callable(get_universe):
            try:
                universe = set(get_universe(current_user) or [])
                if universe:
                    phases = {sym: payload for sym, payload in phases.items() if sym in universe}
            except Exception:
                pass

    return jsonify({"phase_order": phase_order, "phases": phases, "timestamp": time.time()})


@dashboard_bp.route("/api/performance", endpoint="api_performance_metrics")
@login_required
def api_performance_metrics():
    ctx = _get_ai_bot_context()
    traders = [
        _ctx_trader(ctx, "ultimate_trader"),
        _ctx_trader(ctx, "optimized_trader"),
    ]

    total_profit = 0.0
    total_trades = 0
    successful_trades = 0
    active_trades = 0

    for trader in traders:
        if not trader:
            continue
        efficiency = getattr(trader, "bot_efficiency", {}) or {}
        total_profit += efficiency.get("total_profit", 0)
        total_trades += efficiency.get("total_trades", 0)
        successful_trades += efficiency.get("successful_trades", 0)
        positions = getattr(trader, "positions", None)
        if positions:
            active_trades += len(positions)

    win_rate = (successful_trades / total_trades) * 100 if total_trades else 0
    portfolio_value = 10000.0 + total_profit

    # === SINGLE SOURCE OF TRUTH ===
    from app.core.system_state import SystemStateManager
    bot_state = SystemStateManager.get_status()

    return jsonify(
        {
            "portfolio_value": round(portfolio_value, 2),
            "total_profit": round(total_profit, 2),
            "daily_change": 2.5, # TODO: Calculate real daily change
            "win_rate": round(win_rate, 1),
            "active_trades": active_trades,
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "system_status": bot_state["status"], # ONLINE | OFFLINE (Real)
        }
    )


@dashboard_bp.route(
    "/api/dashboard_performance", endpoint="api_dashboard_performance_metrics"
)
def api_dashboard_performance_metrics():
    ctx = _get_ai_bot_context()
    ultimate = _ctx_trader(ctx, "ultimate_trader")
    optimized = _ctx_trader(ctx, "optimized_trader")

    def _performance(trader):
        if not trader:
            return {}
        getter = getattr(trader, "get_performance_metrics", None)
        if callable(getter):
            return getter()
        fallback = {
            "total_profit": getattr(trader, "total_profit", 0),
            "total_trades": getattr(trader, "total_trades", 0),
            "successful_trades": getattr(trader, "successful_trades", 0),
            "active_trades": len(getattr(trader, "positions", {}) or {}),
            "win_rate": 0,
            "portfolio_value": getattr(trader, "portfolio_value", 0),
            "daily_change": getattr(trader, "daily_change", 0),
            "system_status": "active"
            if getattr(trader, "trading_enabled", False)
            else "inactive",
        }
        trades = fallback["total_trades"]
        if trades:
            fallback["win_rate"] = (fallback["successful_trades"] / trades) * 100
        return fallback

    return jsonify(
        {
            "ultimate": _performance(ultimate),
            "optimized": _performance(optimized),
            "timestamp": time.time(),
            "success": True,
        }
    )


@dashboard_bp.route("/api/ml_telemetry", endpoint="api_ml_telemetry")
def api_ml_telemetry():
    ctx = _get_ai_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    telemetry = dashboard_data.get("ml_telemetry", {})
    return jsonify(
        {
            "ultimate": telemetry.get("ultimate", {}),
            "optimized": telemetry.get("optimized", {}),
        }
    )


@dashboard_bp.route("/api/qfm", endpoint="api_qfm_analytics")
def api_qfm_analytics():
    ctx = _get_ai_bot_context()
    ml_system = _ctx_ml_system(ctx, "ultimate_ml_system")
    get_universe = ctx.get("get_active_trading_universe")
    raw_symbols = get_universe() if callable(get_universe) else []
    if isinstance(raw_symbols, (list, tuple, set)):
        active_symbols = list(raw_symbols)
    else:
        active_symbols = []

    qfm_data: dict[str, dict[str, float]] = {}
    for symbol in active_symbols:
        try:
            if (
                ml_system
                and hasattr(ml_system, "get_qfm_features")
                and symbol in getattr(ml_system, "models", {})
            ):
                features = ml_system.get_qfm_features(symbol)
                if features:
                    qfm_data[symbol] = {
                        "qfm_velocity": features.get("qfm_velocity", 0.0),
                        "qfm_acceleration": features.get("qfm_acceleration", 0.0),
                        "qfm_jerk": features.get("qfm_jerk", 0.0),
                        "qfm_volume_pressure": features.get("qfm_volume_pressure", 0.0),
                        "qfm_trend_confidence": features.get(
                            "qfm_trend_confidence", 0.0
                        ),
                        "qfm_regime_score": features.get("qfm_regime_score", 0.0),
                        "qfm_entropy": features.get("qfm_entropy", 0.0),
                    }
                    continue
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Error getting QFM data for {symbol}: {exc}")

        qfm_data[symbol] = {
            "qfm_velocity": round(random.uniform(-1.0, 1.0), 4),
            "qfm_acceleration": round(random.uniform(-0.5, 0.5), 4),
            "qfm_jerk": round(random.uniform(-0.2, 0.2), 4),
            "qfm_volume_pressure": round(random.uniform(0.0, 1.0), 4),
            "qfm_trend_confidence": round(random.uniform(0.0, 1.0), 4),
            "qfm_regime_score": round(random.uniform(-1.0, 1.0), 4),
            "qfm_entropy": round(random.uniform(0.0, 1.0), 4),
        }

    aggregate = {}
    if qfm_data:
        aggregate = {
            metric: sum(data[metric] for data in qfm_data.values()) / len(qfm_data)
            for metric in next(iter(qfm_data.values())).keys()
        }

    return jsonify(
        {
            "symbols": qfm_data,
            "aggregate": aggregate,
            "count": len(qfm_data),
        }
    )


@dashboard_bp.route("/api/qfm/status", endpoint="api_qfm_status")
@login_required
def api_qfm_status():
    ctx = _get_ai_bot_context()
    qfm_engine = ctx.get("qfm_engine")
    if qfm_engine:
        return jsonify(
            {
                "status": "active",
                "strategy": "Quantum Fusion Momentum",
                "version": "1.0",
                "signals_generated": getattr(qfm_engine, "signals_count", 0),
                "performance": getattr(qfm_engine, "performance_metrics", {}),
            }
        )
    return (
        jsonify(
            {
                "status": "inactive",
                "message": "QFM engine not initialized",
            }
        ),
        404,
    )


@dashboard_bp.route("/api/qfm/signals", endpoint="api_qfm_signals")
@login_required
def api_qfm_signals():
    signals = [
        {
            "symbol": "BTC/USDT",
            "signal": "BUY",
            "confidence": 0.85,
            "timestamp": "2024-01-24T10:00:00Z",
        },
        {
            "symbol": "ETH/USDT",
            "signal": "HOLD",
            "confidence": 0.62,
            "timestamp": "2024-01-24T09:45:00Z",
        },
    ]
    return jsonify({"signals": signals, "count": len(signals)})


@dashboard_bp.route("/api/crt/status", endpoint="api_crt_status")
@login_required
def api_crt_status():
    return jsonify(
        {
            "status": "active",
            "strategy": "Composite Reasoning Technology",
            "version": "1.0",
            "analysis_modules": ["technical", "sentiment", "momentum"],
        }
    )


@dashboard_bp.route("/api/ml/status", endpoint="api_ml_status")
@login_required
def api_ml_status():
    ctx = _get_ai_bot_context()
    ml_system = _ctx_ml_system(ctx, "ultimate_ml_system")
    
    status = "inactive"
    models_loaded = 0
    accuracy = 0.0
    
    if ml_system:
        status = "active"
        # Try to get real stats if available
        models_loaded = len(getattr(ml_system, "models", {}))
        accuracy = getattr(ml_system, "last_accuracy", 0.0)

    return jsonify(
        {
            "status": status,
            "models_loaded": models_loaded,
            "training_status": "idle", # TODO: check worker status
            "prediction_accuracy": accuracy,
            "active_strategies": ["QFM", "CRT", "Ensemble"],
        }
    )


@dashboard_bp.route("/api/trading/status", endpoint="api_trading_status")
@login_required
def api_trading_status():
    from app.core.system_state import SystemStateManager
    bot_state = SystemStateManager.get_status()
    
    # Get Real Portfolio Data
    ctx = _get_ai_bot_context()
    trader = _ctx_trader(ctx, "ultimate_trader")
    
    open_positions = 0
    total_trades = 0
    success_rate = 0.0
    daily_pnl = 0.0
    
    if trader:
        open_positions = len(getattr(trader, "positions", {}) or {})
        eff = getattr(trader, "bot_efficiency", {})
        total_trades = eff.get("total_trades", 0)
        success_trades = eff.get("successful_trades", 0)
        if total_trades > 0:
            success_rate = success_trades / total_trades
        daily_pnl = getattr(trader, "daily_pnl", 0.0)

    return jsonify(
        {
            "status": "active" if bot_state["status"] == "ONLINE" else "inactive",
            "mode": "paper_trading", # TODO: Check config for real/paper
            "open_positions": open_positions,
            "total_trades": total_trades,
            "success_rate": round(success_rate, 2),
            "daily_pnl": round(daily_pnl, 2),
        }
    )
    
@dashboard_bp.route("/api/market-data/history/<symbol>", endpoint="api_market_history")
@login_required
def api_market_history(symbol):
    """Get historical OHLCV data for charting (REAL)."""
    try:
        from app.services.binance_market import get_historical_klines
        
        # Fetch real daily candles
        candles = get_historical_klines(symbol, interval="1d", limit=100)
        
        return jsonify({"success": True, "symbol": symbol, "candles": candles})
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return jsonify({"success": False, "error": str(e), "dataset": []})

@dashboard_bp.route("/api/dashboard/stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    """Get dashboard header stats (Real)."""
    try:
        from app.models import UserPortfolio, UserTrade
        from app.extensions import db
        
        ctx = _get_ai_bot_context()
        user_id = getattr(current_user, "id", None)
        
        # 1. Get Portfolio Data
        portfolio = UserPortfolio.query.filter_by(user_id=user_id).first()
        
        portfolio_value = 10000.0  # Default
        daily_change_percent = 0.0
        
        if portfolio:
            portfolio_value = portfolio.total_balance or 0.0
            daily_pnl = portfolio.daily_pnl or 0.0
            
            # Calculate approx percentage change
            # If current is 10000 and daily PnL is 100, open was 9900. 100/9900
            start_balance = portfolio_value - daily_pnl
            if start_balance > 0:
                daily_change_percent = (daily_pnl / start_balance) * 100
            elif start_balance == 0 and daily_pnl > 0:
                daily_change_percent = 100.0
                
        # 2. Get Active Trades (Runtime preferred, DB fallback)
        active_trades = 0
        
        # Try runtime first
        ultimate_trader = _ctx_trader(ctx, "ultimate_trader")
        if ultimate_trader:
             # Check if we have user-specific trader (isolation)
             market_service = ctx.get("market_data_service")
             if market_service and hasattr(market_service, "_get_or_create_user_traders"):
                  try:
                      ut, _ = market_service._get_or_create_user_traders(user_id)
                      if ut:
                          ultimate_trader = ut
                  except:
                      pass
             
             positions = getattr(ultimate_trader, "positions", {})
             if positions:
                 active_trades = len(positions)
        
        # DB Fallback if runtime 0 (maybe restarted)
        if active_trades == 0 and portfolio and portfolio.open_positions:
            # Check if json implies keys
             try:
                 if isinstance(portfolio.open_positions, dict):
                     active_trades = len(portfolio.open_positions)
             except:
                 pass

        # 3. Calculate Win Rate (Historical)
        win_rate = 0.0
        total_closed = 0
        wins = 0
        
        # Query DB for closed trades
        # status="closed" or exit_price > 0? Schema has 'status'.
        trades = UserTrade.query.filter_by(
            user_id=user_id, 
            status="closed"
        ).order_by(UserTrade.timestamp.desc()).limit(100).all()
        
        if trades:
            total_closed = len(trades)
            # Count wins (pnl > 0)
            wins = sum(1 for t in trades if (t.pnl or 0) > 0)
            if total_closed > 0:
                win_rate = (wins / total_closed) * 100

        return jsonify({
            "portfolio_value": round(portfolio_value, 2),
            "daily_change": round(daily_change_percent, 2),
            "active_trades": active_trades,
            "win_rate": round(win_rate, 1)
        })
        
    except Exception as exc:
        current_app.logger.error(f"Error fetching dashboard stats: {exc}")
        # Return safe defaults on error
        return jsonify({
            "portfolio_value": 0.00,
            "daily_change": 0.0,
            "active_trades": 0,
            "win_rate": 0
        })
