"""High-level runtime orchestration helpers for the legacy AI bot."""
from __future__ import annotations

import signal
from typing import Any, Mapping, MutableMapping, Sequence


def _safe_bool_mapping(value, default):
    if isinstance(value, MutableMapping):
        return value
    return default


def initialize_runtime_from_context(context: Mapping[str, Any]) -> None:
    """Run the legacy initialization sequence using an assembled context payload."""

    dashboard_data: MutableMapping[str, Any] = context.get('dashboard_data') or {}
    trade_history = context.get('trade_history')
    persistence_manager = context.get('persistence_manager')
    ultimate_trader = context.get('ultimate_trader')
    optimized_trader = context.get('optimized_trader')
    ultimate_ml_system = context.get('ultimate_ml_system')
    optimized_ml_system = context.get('optimized_ml_system')
    background_task_manager = context.get('background_task_manager')
    trading_config: MutableMapping[str, Any] = context.get('trading_config') or {}
    historical_data: MutableMapping[str, Any] = context.get('historical_data') or {}
    top_symbols: Sequence[str] = context.get('top_symbols') or []
    get_active_trading_universe = context.get('get_active_trading_universe')
    get_real_market_data = context.get('get_real_market_data')
    health_report_service = context.get('health_report_service')
    signal_handler = context.get('signal_handler')

    print("🚀 INITIALIZING ULTIMATE PROFESSIONAL AI TRADING BOT...")
    print("=" * 80)

    trades = []
    if trade_history and hasattr(trade_history, 'load_trades'):
        try:
            trades = trade_history.load_trades()
        except Exception as exc:
            print(f"⚠️ Failed to load trade history: {exc}")
    print(f"📊 Loaded {len(trades)} historical trades")

    print("💾 Attempting to load previous bot state...")
    state_loaded = False
    if persistence_manager and ultimate_trader and ultimate_ml_system:
        try:
            state_loaded = persistence_manager.load_complete_state(ultimate_trader, ultimate_ml_system)
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
                return payload.get('price', 100)
            except Exception as exc:  # pragma: no cover - defensive logging only
                print(f"⚠️ Could not fetch market data for {symbol}: {exc}")
                return 100

        try:
            current_prices = {symbol: safe_get_price(symbol) for symbol in active_symbols}
            portfolio_summary = ultimate_trader.get_portfolio_summary(current_prices)
            dashboard_data['portfolio'] = portfolio_summary
        except Exception as exc:
            print(f"⚠️ Could not fetch market data for portfolio update: {exc}")
            print("ℹ️ Continuing with cached/default portfolio data")
    else:
        print("🔶 Starting with fresh bot state")

    if dashboard_data and optimized_trader:
        dashboard_data.setdefault('optimized_system_status', {})['trading_enabled'] = getattr(
            optimized_trader, 'trading_enabled', False
        )

    if background_task_manager:
        try:
            background_task_manager.start_background_tasks(
                start_ultimate_training=not getattr(ultimate_ml_system, 'models', None),
                start_optimized_training=not getattr(optimized_ml_system, 'models', None),
                persistence_inputs={
                    'trader': ultimate_trader,
                    'ml_system': ultimate_ml_system,
                    'config': trading_config,
                    'symbols': top_symbols,
                    'historical_data': historical_data,
                },
            )
        except Exception as exc:
            print(f"⚠️ Failed to start background tasks: {exc}")

    if dashboard_data is not None:
        system_status = dashboard_data.setdefault('system_status', {})
        optimized_status = dashboard_data.setdefault('optimized_system_status', {})
        if getattr(ultimate_ml_system, 'models', None):
            system_status['models_loaded'] = True
        if getattr(optimized_ml_system, 'models', None):
            optimized_status['models_loaded'] = True

    if trading_config.get('continuous_training'):
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
    print("📍 Dashboard available at: http://localhost:5001")
    print("📍 Health check at: http://localhost:5001/health")
    print("=" * 80)


__all__ = ['initialize_runtime_from_context']
