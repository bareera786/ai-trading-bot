"""Shared service assembly helpers for the AI bot runtime."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, MutableMapping, Sequence

from app.services import (
    FuturesMarketDataService,
    MarketDataService,
    RealtimeUpdateService,
)
from app.tasks import ModelTrainingWorker, SelfImprovementWorker

from .indicators import (
    BEST_INDICATORS,
    build_indicator_dashboard_refresher,
    IndicatorSelectionManager,
)


@dataclass
class ServiceRuntime:
    """Group of runtime services shared across the app."""

    historical_data: MutableMapping[str, list[Any]]
    refresh_indicator_dashboard_state: Callable[[], Dict[str, list[str]]]
    market_data_service: MarketDataService
    futures_market_data_service: FuturesMarketDataService | None
    realtime_update_service: RealtimeUpdateService
    model_training_worker: ModelTrainingWorker
    self_improvement_worker: SelfImprovementWorker


def build_service_runtime(
    *,
    dashboard_data: MutableMapping[str, Any],
    indicator_selection_manager: IndicatorSelectionManager,
    trading_config: Mapping[str, Any],
    ultimate_trader: Any,
    optimized_trader: Any,
    ultimate_ml_system: Any,
    optimized_ml_system: Any,
    futures_ml_system: Any,
    parallel_engine: Any,
    futures_manual_settings: MutableMapping[str, Any],
    binance_credential_service: Any,
    get_active_trading_universe: Callable[[], Sequence[str]],
    get_real_market_data: Callable[[str], Mapping[str, Any]],
    get_trending_pairs: Callable[[], Iterable[str]],
    refresh_symbol_counters: Callable[[], None],
    handle_manual_futures_trading: Callable[..., Any],
    futures_dashboard_state: MutableMapping[str, Any],
    futures_symbols: Sequence[str],
    futures_data_lock: Any,
    socketio: Any,
    safe_float: Callable[[Any, float], float],
    bot_logger: Any,
) -> ServiceRuntime:
    """Construct all runtime services that depend on dashboard state."""

    historical_data = {symbol: [] for symbol in get_active_trading_universe()}

    refresh_indicator_dashboard_state = build_indicator_dashboard_refresher(
        dashboard_data,
        indicator_selection_manager,
    )
    refresh_indicator_dashboard_state()

    futures_market_data_service = FuturesMarketDataService(
        dashboard_data=dashboard_data,
        futures_dashboard_state=futures_dashboard_state,
        trading_config=trading_config,
        futures_ml_system=futures_ml_system,
        ultimate_trader=ultimate_trader,
        futures_symbols=futures_symbols,
        futures_data_lock=futures_data_lock,
        manual_trade_handler=handle_manual_futures_trading,
        bot_logger=bot_logger,
    )

    realtime_update_service = RealtimeUpdateService(
        socketio, dashboard_data, get_active_trading_universe
    )

    market_data_service = MarketDataService(
        dashboard_data=dashboard_data,
        historical_data=historical_data,
        trading_config=trading_config,
        ultimate_trader=ultimate_trader,
        optimized_trader=optimized_trader,
        ultimate_ml_system=ultimate_ml_system,
        optimized_ml_system=optimized_ml_system,
        parallel_engine=parallel_engine,
        futures_manual_settings=futures_manual_settings,
        binance_credential_service=binance_credential_service,
        get_active_trading_universe=get_active_trading_universe,
        get_real_market_data=get_real_market_data,
        get_trending_pairs=get_trending_pairs,
        refresh_symbol_counters=refresh_symbol_counters,
        refresh_indicator_dashboard_state=refresh_indicator_dashboard_state,
        safe_float=safe_float,
        bot_logger=bot_logger,
        sleep_interval=trading_config.get("market_data_interval_seconds", 30),
    )

    model_training_worker = ModelTrainingWorker(
        ultimate_ml_system=ultimate_ml_system,
        optimized_ml_system=optimized_ml_system,
        dashboard_data=dashboard_data,
        get_active_trading_universe=get_active_trading_universe,
        refresh_symbol_counters=refresh_symbol_counters,
        best_indicators=BEST_INDICATORS,
        logger=bot_logger,
    )

    self_improvement_worker = SelfImprovementWorker(
        ultimate_trader=ultimate_trader,
        optimized_trader=optimized_trader,
        ultimate_ml_system=ultimate_ml_system,
        optimized_ml_system=optimized_ml_system,
        dashboard_data=dashboard_data,
        trading_config=trading_config,
        cycle_interval_seconds=trading_config.get(
            "self_improvement_interval_seconds", 10800.0
        ),
        logger=bot_logger,
    )

    return ServiceRuntime(
        historical_data=historical_data,
        refresh_indicator_dashboard_state=refresh_indicator_dashboard_state,
        market_data_service=market_data_service,
        futures_market_data_service=futures_market_data_service,
        realtime_update_service=realtime_update_service,
        model_training_worker=model_training_worker,
        self_improvement_worker=self_improvement_worker,
    )


__all__ = ["ServiceRuntime", "build_service_runtime"]
