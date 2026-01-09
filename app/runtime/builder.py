"""Runtime builder utilities that bridge the legacy monolith."""

from __future__ import annotations

from importlib import import_module
from typing import Any, Optional

from .context import (
    IndicatorRuntime,
    RuntimeContext,
    SymbolRuntime,
    build_runtime_context as _build_context,
    UserScopedProxy,
)
from .indicators import INDICATOR_SIGNAL_OPTIONS
from .payloads import build_ai_bot_context_payload
from . import symbols
from .symbols import get_training_universe

LEGACY_RUNTIME_MODULE = "ai_ml_auto_bot_final"


class RuntimeBuilderError(RuntimeError):
    """Raised when the runtime builder cannot assemble the context."""


def _import_legacy_module():
    try:
        return import_module(LEGACY_RUNTIME_MODULE)
    except (
        Exception
    ) as exc:  # pragma: no cover - defensive logging for import edge cases
        raise RuntimeBuilderError(f"Failed to import legacy runtime: {exc}") from exc


def _build_indicator_runtime(module) -> Optional[IndicatorRuntime]:
    manager = getattr(module, "indicator_selection_manager", None)
    if manager is None:
        return None
    refresher = getattr(module, "refresh_indicator_dashboard_state", None)
    return IndicatorRuntime(
        selection_manager=manager,
        signal_options=INDICATOR_SIGNAL_OPTIONS,
        dashboard_refresher=refresher,
    )


def _build_symbol_runtime() -> SymbolRuntime:
    return SymbolRuntime(
        get_active_universe=symbols.get_active_trading_universe,
        get_all_symbols=symbols.get_all_known_symbols,
        get_disabled_symbols=symbols.get_disabled_symbols,
        disable_symbol=symbols.disable_symbol,
        enable_symbol=symbols.enable_symbol,
        is_symbol_disabled=symbols.is_symbol_disabled,
        refresh_counters=symbols.refresh_symbol_counters,
        clear_symbol_dashboards=symbols.clear_symbol_from_dashboard,
        save_state=symbols.save_symbol_state,
        normalize_symbol=symbols.normalize_symbol,
        static_top_symbols=list(symbols.TOP_SYMBOLS),
        static_disabled_symbols=list(symbols.DISABLED_SYMBOLS),
    )


def _require_attr(module, attr_name: str):
    if not hasattr(module, attr_name):
        raise RuntimeBuilderError(f"Legacy module missing attribute: {attr_name}")
    return getattr(module, attr_name)


def _resolve_binance_credential_methods(module):
    service = _require_attr(module, "binance_credential_service")
    apply_creds = getattr(service, "apply_credentials", None)
    status_getter = getattr(service, "get_status", None)
    if apply_creds is None or status_getter is None:
        raise RuntimeBuilderError(
            "BinanceCredentialService is missing required helpers"
        )
    return service, apply_creds, status_getter


def _build_payload_from_module(
    module, *, indicator_runtime: Optional[IndicatorRuntime]
) -> dict[str, Any]:
    indicator_profiles = indicator_runtime.profiles() if indicator_runtime else []
    service, apply_credentials, get_status = _resolve_binance_credential_methods(module)
    ultimate_ml_system = _require_attr(module, "ultimate_ml_system")

    raw_qfm_engine = getattr(ultimate_ml_system, "qfm_engine", None)
    if raw_qfm_engine is not None:
        qfm_engine = UserScopedProxy(
            base=raw_qfm_engine,
            factory=lambda: raw_qfm_engine.__class__(),
        )
    else:
        qfm_engine = None

    raw_strategy_manager = _require_attr(module, "strategy_manager")

    # The legacy module exposes a global StrategyManager singleton.
    # Wrap it so user-facing routes do not share mutable strategy/analytics state.
    strategy_manager = UserScopedProxy(
        base=raw_strategy_manager,
        factory=lambda: raw_strategy_manager.__class__(),
    )

    return build_ai_bot_context_payload(
        dashboard_data=_require_attr(module, "dashboard_data"),
        health_data_lock=_require_attr(module, "health_data_lock"),
        health_report_service=_require_attr(module, "health_report_service"),
        indicator_signal_options=INDICATOR_SIGNAL_OPTIONS,
        indicator_profiles=indicator_profiles,
        get_indicator_selection=_require_attr(module, "get_indicator_selection"),
        get_all_indicator_selections=_require_attr(
            module, "get_all_indicator_selections"
        ),
        set_indicator_selection=_require_attr(module, "set_indicator_selection"),
        refresh_indicator_dashboard_state=_require_attr(
            module, "refresh_indicator_dashboard_state"
        ),
        ultimate_trader=_require_attr(module, "ultimate_trader"),
        optimized_trader=_require_attr(module, "optimized_trader"),
        ultimate_ml_system=ultimate_ml_system,
        optimized_ml_system=_require_attr(module, "optimized_ml_system"),
        futures_ml_system=_require_attr(module, "futures_ml_system"),
        parallel_engine=_require_attr(module, "parallel_engine"),
        strategy_manager=strategy_manager,
        backtest_manager=_require_attr(module, "backtest_manager"),
        get_active_trading_universe=get_training_universe,
        get_real_market_data=_require_attr(module, "get_real_market_data"),
        get_trending_pairs=_require_attr(module, "get_trending_pairs"),
        get_user_trader=_require_attr(module, "get_user_trader"),
        get_user_portfolio_data=_require_attr(module, "get_user_portfolio_data"),
        update_live_portfolio_pnl=_require_attr(module, "update_live_portfolio_pnl"),
        trade_history=_require_attr(module, "trade_history"),
        apply_binance_credentials=apply_credentials,
        get_binance_credential_status=get_status,
        binance_credentials_store=_require_attr(module, "binance_credentials_store"),
        binance_credential_service=service,
        binance_log_manager=_require_attr(module, "binance_log_manager"),
        futures_dashboard_state=_require_attr(module, "futures_dashboard_state"),
        futures_manual_service=_require_attr(module, "futures_manual_service"),
        futures_manual_settings=_require_attr(module, "futures_manual_settings"),
        futures_manual_lock=_require_attr(module, "futures_manual_lock"),
        futures_data_lock=_require_attr(module, "futures_data_lock"),
        futures_symbols=symbols.FUTURES_SYMBOLS,
        ensure_futures_manual_defaults=_require_attr(
            module, "_ensure_futures_manual_defaults"
        ),
        trading_config=_require_attr(module, "TRADING_CONFIG"),
        coerce_bool=_require_attr(module, "_coerce_bool"),
        qfm_engine=qfm_engine,
        persistence_manager=_require_attr(module, "persistence_manager"),
        persistence_scheduler=_require_attr(module, "persistence_scheduler"),
        persistence_runtime=_require_attr(module, "persistence_runtime"),
        background_runtime=getattr(
            module, "background_runtime", None
        ),  # Optional, will be built if missing
        background_task_manager=getattr(
            module, "background_task_manager", None
        ),  # Optional, will be built if missing
        service_runtime=_require_attr(module, "service_runtime"),
        realtime_update_service=_require_attr(module, "realtime_update_service"),
        market_data_service=_require_attr(module, "market_data_service"),
        futures_market_data_service=_require_attr(
            module, "futures_market_data_service"
        ),
        live_portfolio_scheduler=_require_attr(module, "live_portfolio_scheduler"),
        historical_data=_require_attr(module, "historical_data"),
        top_symbols=symbols.TOP_SYMBOLS,
        disabled_symbols=symbols.DISABLED_SYMBOLS,
        get_all_known_symbols=symbols.get_all_known_symbols,
        get_disabled_symbols=symbols.get_disabled_symbols,
        refresh_symbol_counters=symbols.refresh_symbol_counters,
        clear_symbol_from_dashboard=symbols.clear_symbol_from_dashboard,
        is_symbol_disabled=symbols.is_symbol_disabled,
        disable_symbol=symbols.disable_symbol,
        enable_symbol=symbols.enable_symbol,
        save_symbol_state=symbols.save_symbol_state,
        normalize_symbol=symbols.normalize_symbol,
        signal_handler=getattr(module, "signal_handler", None),
        version_label=getattr(module, "AI_BOT_VERSION", "LEGACY"),
    )


def assemble_runtime_context(
    *, flask_app=None, force: bool = False
) -> Optional[RuntimeContext]:
    """Build a runtime context backed by the legacy monolith globals."""

    module = _import_legacy_module()
    if module is None:
        return None
    indicator_runtime = _build_indicator_runtime(module)
    payload = _build_payload_from_module(module, indicator_runtime=indicator_runtime)
    dashboard_data = payload.get("dashboard_data")
    if dashboard_data is not None:
        symbols.attach_dashboard_data(dashboard_data)

    # Try to get background_runtime from module, build it if missing
    background_runtime = payload.get("background_runtime")
    if background_runtime is None and payload.get("background_task_manager") is None:
        # Build background runtime if not available
        try:
            from .background import build_background_runtime

            background_runtime = build_background_runtime(
                update_callback=payload.get("update_live_portfolio_pnl"),
                bot_logger=getattr(module, "logger", None),
                market_data_service=payload.get("market_data_service"),
                futures_market_data_service=payload.get("futures_market_data_service"),
                futures_safety_service=getattr(
                    payload.get("service_runtime"), "futures_safety_service", None
                )
                if payload.get("service_runtime")
                else None,
                realtime_update_service=payload.get("realtime_update_service"),
                persistence_scheduler=payload.get("persistence_scheduler"),
                self_improvement_worker=getattr(
                    payload.get("service_runtime"), "self_improvement_worker", None
                )
                if payload.get("service_runtime")
                else None,
                model_training_worker=getattr(
                    payload.get("service_runtime"), "model_training_worker", None
                )
                if payload.get("service_runtime")
                else None,
                trading_config=payload.get("trading_config", {}),
                flask_app=flask_app,
            )
            # Set it on the module for future use
            setattr(module, "background_runtime", background_runtime)
            payload["background_runtime"] = background_runtime
            payload["background_task_manager"] = getattr(
                background_runtime, "background_task_manager", None
            )
        except Exception as exc:
            # Log but don't fail - background runtime is optional
            import logging

            logger = logging.getLogger("ai_trading_bot")
            logger.warning("Failed to build background runtime: %s", exc)

    runtime = _build_context(
        payload,
        indicator_runtime=indicator_runtime,
        symbol_runtime=_build_symbol_runtime(),
        persistence_runtime=payload.get("persistence_runtime"),
        background_runtime=background_runtime,
        service_runtime=payload.get("service_runtime"),
    )

    if flask_app is not None:
        runtime.attach_to_app(flask_app, force=force)

    return runtime


__all__ = ["assemble_runtime_context", "RuntimeBuilderError"]
