"""High-level runtime orchestration helpers for the legacy AI bot."""
from __future__ import annotations

import signal
from typing import Any, Mapping, MutableMapping, Sequence
import os

from flask import current_app, has_app_context

from config.resource_manager import ResourceManager


def _safe_bool_mapping(value, default):
    if isinstance(value, MutableMapping):
        return value
    return default


def initialize_runtime_from_context(context: Mapping[str, Any]) -> None:
    """Run the legacy initialization sequence using an assembled context payload."""

    dashboard_data: MutableMapping[str, Any] = context.get("dashboard_data") or {}
    trade_history = context.get("trade_history")
    persistence_manager = context.get("persistence_manager")
    ultimate_trader = context.get("ultimate_trader")
    optimized_trader = context.get("optimized_trader")
    ultimate_ml_system = context.get("ultimate_ml_system")
    optimized_ml_system = context.get("optimized_ml_system")
    background_task_manager = context.get("background_task_manager")
    trading_config: MutableMapping[str, Any] = context.get("trading_config") or {}
    historical_data: MutableMapping[str, Any] = context.get("historical_data") or {}
    top_symbols: Sequence[str] = context.get("top_symbols") or []
    get_active_trading_universe = context.get("get_active_trading_universe")
    get_real_market_data = context.get("get_real_market_data")
    health_report_service = context.get("health_report_service")
    signal_handler = context.get("signal_handler")

    # Wire TimescaleDB service to ML systems
    if (
        ultimate_trader
        and hasattr(ultimate_trader, "timescaledb_service")
        and ultimate_ml_system
    ):
        ultimate_ml_system.timescaledb_service = ultimate_trader.timescaledb_service
    if (
        optimized_trader
        and hasattr(optimized_trader, "timescaledb_service")
        and optimized_ml_system
    ):
        optimized_ml_system.timescaledb_service = optimized_trader.timescaledb_service

    print("🚀 INITIALIZING ULTIMATE PROFESSIONAL AI TRADING BOT...")
    print("=" * 80)

    trades = []
    if trade_history and hasattr(trade_history, "load_trades"):
        try:
            trades = trade_history.load_trades()
        except Exception as exc:
            print(f"⚠️ Failed to load trade history: {exc}")
    print(f"📊 Loaded {len(trades)} historical trades")

    print("💾 Attempting to load previous bot state...")
    state_loaded = False
    if persistence_manager and ultimate_trader and ultimate_ml_system:
        try:
            state_loaded = persistence_manager.load_complete_state(
                ultimate_trader, ultimate_ml_system
            )
        except Exception as exc:
            print(f"⚠️ Persistence restore failed: {exc}")

    active_symbols = []
    if callable(get_active_trading_universe):
        try:
            active_symbols = list(get_active_trading_universe())
        except Exception as exc:
            print(f"⚠️ Failed to resolve active universe: {exc}")

    if state_loaded and dashboard_data is not None and callable(get_real_market_data):
        print("✅ Bot state successfully restored from persistence")

        def safe_get_price(symbol):
            try:
                payload = get_real_market_data(symbol) or {}
                return payload.get("price", 100)
            except Exception as exc:  # pragma: no cover - defensive logging only
                print(f"⚠️ Could not fetch market data for {symbol}: {exc}")
                return 100

        try:
            current_prices = {
                symbol: safe_get_price(symbol) for symbol in active_symbols
            }
            portfolio_summary = ultimate_trader.get_portfolio_summary(current_prices)
            dashboard_data["portfolio"] = portfolio_summary
        except Exception as exc:
            print(f"⚠️ Could not fetch market data for portfolio update: {exc}")
            print("ℹ️ Continuing with cached/default portfolio data")
    else:
        print("🔶 Starting with fresh bot state")

    if dashboard_data and optimized_trader:
        dashboard_data.setdefault("optimized_system_status", {})[
            "trading_enabled"
        ] = getattr(optimized_trader, "trading_enabled", False)

    # Respect an environment-level kill-switch so persisted state cannot
    # automatically re-enable heavy continuous training on startup.
    disable_continuous_training = os.environ.get(
        "DISABLE_CONTINUOUS_TRAINING", os.environ.get("DISABLE_TRAINING", "0")
    ).lower() in ("1", "true", "yes")

    # Initialize resource manager for system monitoring
    resource_manager = ResourceManager()

    if background_task_manager:
        # Don't start long-running background tasks when running tests
        if has_app_context() and current_app.config.get("TESTING"):
            print("ℹ️ TESTING mode detected: skipping start of background tasks")
        else:
            try:
                # If the env-based kill-switch is enabled, do not start
                # any long-running training tasks regardless of persisted state.
                background_task_manager.start_background_tasks(
                    start_ultimate_training=(
                        not getattr(ultimate_ml_system, "models", None)
                        and not disable_continuous_training
                    ),
                    start_optimized_training=(
                        not getattr(optimized_ml_system, "models", None)
                        and not disable_continuous_training
                    ),
                    persistence_inputs={
                        "trader": ultimate_trader,
                        "ml_system": ultimate_ml_system,
                        "config": trading_config,
                        "symbols": top_symbols,
                        "historical_data": historical_data,
                    },
                )
            except Exception as exc:
                print(f"⚠️ Failed to start background tasks: {exc}")

    if dashboard_data is not None:
        system_status = dashboard_data.setdefault("system_status", {})
        optimized_status = dashboard_data.setdefault("optimized_system_status", {})
        if getattr(ultimate_ml_system, "models", None):
            system_status["models_loaded"] = True
        if getattr(optimized_ml_system, "models", None):
            optimized_status["models_loaded"] = True
        
        # Add system resource info to dashboard
        resources = resource_manager.get_system_resources()
        dashboard_data["system_resources"] = {
            "cpu_percent": resources.cpu_percent,
            "memory_percent": resources.memory_percent,
            "memory_available_gb": resources.memory_available_gb,
            "load_avg_1min": resources.load_avg_1min,
            "disk_usage_percent": resources.disk_usage_percent,
        }

    # Don't start continuous training if the environment explicitly
    # disables it. This prevents persisted state from re-enabling
    # CPU-heavy operations unexpectedly.
    if not disable_continuous_training and trading_config.get("continuous_training"):
        # Check system resources before starting training
        if not resource_manager.is_safe_for_training():
            print("⚠️ System resources insufficient for continuous training - skipping")
        else:
            try:
                ultimate_ml_system.start_continuous_training_cycle()
                print("✅ Continuous training cycle started")
            except Exception as exc:
                print(f"⚠️ Failed to start ultimate continuous training: {exc}")
            try:
                optimized_ml_system.start_continuous_training_cycle()
                print("✅ Optimized continuous training cycle started")
            except Exception as exc:
                print(f"⚠️ Failed to start optimized continuous training: {exc}")

    if health_report_service:
        try:
            health_report_service.refresh(run_backtest=False)
            health_report_service.start_periodic_refresh()
            print("✅ Backtest health monitor initialized")
        except Exception as exc:
            print(f"⚠️ Failed to initialize health monitor: {exc}")

    if signal_handler:
        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            print("✅ Signal handlers registered for graceful shutdown")
        except Exception as exc:
            print(f"⚠️ Failed to register signal handlers: {exc}")

    print("=" * 80)
    print("🎉 ULTIMATE AI TRADING BOT FULLY INITIALIZED AND READY!")
    print("💾 Professional Persistence: ACTIVE")

    # Get the actual port from Flask app config or default to 5000
    port = 5000  # Default port we're using
    try:
        if hasattr(current_app, "config"):
            # Try to get port from SERVER_NAME if set
            server_name = current_app.config.get("SERVER_NAME")
            if server_name and ":" in server_name:
                port = int(server_name.split(":")[-1])
    except Exception:
        pass  # Fall back to default

    print(f"📍 Dashboard available at: http://localhost:{port}")
    print(f"📍 Health check at: http://localhost:{port}/health")
    print("=" * 80)


__all__ = ["initialize_runtime_from_context"]
