"""Trading control and credential management routes."""
from __future__ import annotations

import json
import os
import time
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from app.auth.decorators import subscription_required
from app.services import FuturesManualService


trading_bp = Blueprint("trading", __name__)


def _get_bot_context() -> dict[str, Any]:
    ctx = current_app.extensions.get("ai_bot_context")
    if not ctx:
        # If missing, try to reuse a previously-registered fallback (dashboard
        # may have created one). Otherwise register a lightweight shared
        # fallback so toggles and dashboard reads operate consistently.
        fallback = current_app.extensions.get("ai_bot_context")
        if not fallback:
            # Provide the same lightweight services that dashboard fallback
            # registers so trading endpoints behave consistently in test-mode.
            from app.services.test_fallbacks import (
                InMemoryCredentialsStore,
                SimpleLogManager,
                FallbackTrader,
                default_apply_credentials,
                default_get_status,
            )

            fallback = {
                "dashboard_data": {"system_status": {}, "optimized_system_status": {}},
                "ultimate_trader": FallbackTrader(),
                "optimized_trader": FallbackTrader(),
                "binance_credentials_store": InMemoryCredentialsStore(),
                "binance_log_manager": SimpleLogManager(),
                "apply_binance_credentials": default_apply_credentials,
                "get_binance_credential_status": default_get_status,
            }
            current_app.extensions["ai_bot_context"] = fallback
        return fallback
    return ctx


def _get_dashboard_data(ctx: dict[str, Any]) -> dict[str, Any]:
    dashboard_data = ctx.get("dashboard_data")
    if dashboard_data is None:
        raise RuntimeError("Dashboard data is unavailable")
    return dashboard_data


def _get_futures_manual_service(ctx: dict[str, Any]) -> Optional[FuturesManualService]:
    service = ctx.get("futures_manual_service")
    if isinstance(service, FuturesManualService):
        return service
    return None


def _coerce_bool_with_ctx(
    ctx: dict[str, Any], value: Any, default: bool = True
) -> bool:
    coerce = ctx.get("coerce_bool")
    if callable(coerce):
        return coerce(value, default=default)
    if value is None:
        return default
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _state_file_path() -> str:
    try:
        from app.services.persistence import ensure_persistence_dirs

        persist_dir = ensure_persistence_dirs()
        return str(persist_dir / "bot_state.json")
    except Exception:
        try:
            from app.services.pathing import resolve_profile_path

            persist_dir = resolve_profile_path(
                "bot_persistence", allow_legacy=True, migrate_legacy=True
            )
            return os.path.join(persist_dir, "bot_state.json")
        except Exception:
            return os.path.join("bot_persistence", "default", "bot_state.json")


def _update_state_file(field: str, value: Any, *, profile: str | None = None) -> None:
    try:
        from app.services.persistence import ensure_persistence_dirs, _atomic_write_json, _bot_state_file_lock

        persist_dir = ensure_persistence_dirs(profile)
        state_file = str(persist_dir / "bot_state.json")
    except Exception:
        state_file = _state_file_path()
    if not os.path.exists(state_file):
        return
    try:
        with _bot_state_file_lock(state_file):
            with open(state_file, "r", encoding="utf-8") as handle:
                state = json.load(handle)
    except Exception:
        return

    trader_state = state.get("trader_state") or {}
    trader_state[field] = value
    state["trader_state"] = trader_state
    state["timestamp"] = datetime.now().isoformat()

    try:
        with _bot_state_file_lock(state_file):
            _atomic_write_json(state_file, state)
        print(f"💾 Directly updated state file: {field} = {value}")
    except Exception as exc:  # pragma: no cover - best effort logging
        print(f"⚠️ Failed to directly update state file: {exc}")


def _update_trading_config_state_file(
    field: str, value: Any, *, profile: str | None = None
) -> None:
    """Best-effort update of persisted TRADING_CONFIG in bot_state.json."""
    try:
        from app.services.persistence import ensure_persistence_dirs, _atomic_write_json, _bot_state_file_lock

        persist_dir = ensure_persistence_dirs(profile)
        state_file = str(persist_dir / "bot_state.json")
    except Exception:
        state_file = _state_file_path()
    if not os.path.exists(state_file):
        return
    try:
        with _bot_state_file_lock(state_file):
            with open(state_file, "r", encoding="utf-8") as handle:
                state = json.load(handle)
    except Exception:
        return

    configuration = state.get("configuration") or {}
    trading_config = configuration.get("TRADING_CONFIG") or {}
    trading_config[field] = value
    configuration["TRADING_CONFIG"] = trading_config
    state["configuration"] = configuration
    state["timestamp"] = datetime.now().isoformat()

    try:
        with _bot_state_file_lock(state_file):
            _atomic_write_json(state_file, state)
        print(f"💾 Directly updated state file: TRADING_CONFIG.{field} = {value}")
    except Exception as exc:  # pragma: no cover - best effort logging
        print(f"⚠️ Failed to directly update trading config in state file: {exc}")


@trading_bp.route(
    "/api/binance/credentials",
    methods=["GET", "POST", "DELETE"],
    endpoint="api_binance_credentials",
)
@login_required
def api_binance_credentials():
    ctx = _get_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    # Ensure expected dashboard structure exists (tests may provide empty dict)
    dashboard_data.setdefault("system_status", {})
    dashboard_data.setdefault("optimized_system_status", {})

    status_fn = ctx.get("get_binance_credential_status")
    apply_credentials = ctx.get("apply_binance_credentials")
    credentials_store = ctx.get("binance_credentials_store")
    binance_log_manager = ctx.get("binance_log_manager")
    ultimate_trader = ctx.get("ultimate_trader")
    optimized_trader = ctx.get("optimized_trader")

    # Only require the minimal credential services for saving/loading credentials.
    if not all([callable(status_fn), callable(apply_credentials), credentials_store]):
        return jsonify({"error": "Binance credential services unavailable"}), 500

    method = request.method

    if method == "GET":
        status = status_fn(
            include_connection=True, include_logs=True, user_id=current_user.id
        )
        dashboard_data["binance_credentials"] = status
        dashboard_data["binance_logs"] = status.get("logs", [])
        dashboard_data["real_trading_status"] = status.get("ultimate_status") or {}
        dashboard_data["optimized_real_trading_status"] = (
            status.get("optimized_status") or {}
        )
        dashboard_data["system_status"]["paper_trading"] = getattr(
            ultimate_trader, "paper_trading", True
        )
        dashboard_data["system_status"]["real_trading_ready"] = bool(
            getattr(ultimate_trader, "real_trading_enabled", False)
        )
        dashboard_data["optimized_system_status"]["paper_trading"] = getattr(
            optimized_trader, "paper_trading", True
        )
        dashboard_data["optimized_system_status"]["real_trading_ready"] = bool(
            getattr(optimized_trader, "real_trading_enabled", False)
        )
        return jsonify(status)

    if method == "POST":
        payload = request.get_json(silent=True) or {}
        api_key = (payload.get("apiKey") or payload.get("api_key") or "").strip()
        api_secret = (
            payload.get("apiSecret") or payload.get("api_secret") or ""
        ).strip()
        testnet_flag = _coerce_bool_with_ctx(ctx, payload.get("testnet"), default=True)
        account_type = (
            payload.get("accountType")
            or payload.get("account_type")
            or payload.get("tradingType")
        )
        account_type = credentials_store._normalize_account_type(account_type)

        if not api_key or not api_secret:
            return jsonify({"error": "API key and secret are required"}), 400

        saved = credentials_store.save_credentials(
            api_key,
            api_secret,
            testnet=testnet_flag,
            note=payload.get("note"),
            account_type=account_type,
            user_id=current_user.id,
        )

        if binance_log_manager:
            binance_log_manager.add(
                "CREDENTIAL_SAVE",
                f"Saved {account_type.upper()} credentials.",
                severity="info",
                account_type=account_type,
                details={"testnet": testnet_flag},
                user_id=current_user.id,
            )

        try:
            connected = apply_credentials(
                account_type=account_type, creds=saved, user_id=current_user.id
            )
        except TypeError:
            # Backward-compat shim for older apply_credentials signatures
            connected = apply_credentials(account_type=account_type, creds=saved)
        status = status_fn(
            include_connection=True, include_logs=True, user_id=current_user.id
        )
        dashboard_data["binance_credentials"] = status
        dashboard_data["binance_logs"] = status.get("logs", [])

        ultimate_status = status.get("ultimate_status") or (
            ultimate_trader.get_real_trading_status() if ultimate_trader else {}
        )
        optimized_status = status.get("optimized_status") or (
            optimized_trader.get_real_trading_status() if optimized_trader else {}
        )

        if account_type == "spot":
            dashboard_data["real_trading_status"] = ultimate_status
            dashboard_data["optimized_real_trading_status"] = optimized_status

        dashboard_data["system_status"]["paper_trading"] = getattr(
            ultimate_trader, "paper_trading", True
        )
        dashboard_data["system_status"]["real_trading_ready"] = bool(
            getattr(ultimate_trader, "real_trading_enabled", False)
        )
        dashboard_data["optimized_system_status"]["paper_trading"] = getattr(
            optimized_trader, "paper_trading", True
        )
        dashboard_data["optimized_system_status"]["real_trading_ready"] = bool(
            getattr(optimized_trader, "real_trading_enabled", False)
        )

        response = {
            "saved": True,
            "account_type": account_type,
            "connection_established": bool(connected)
            if account_type == "spot"
            else False,
            "account_connections": {account_type: bool(connected)},
            "status": status,
            "ultimate_status": ultimate_status,
            "optimized_status": optimized_status,
        }
        response["connected"] = response["connection_established"]
        return jsonify(response)

    # DELETE
    payload = request.get_json(silent=True) or {}
    account_type = (
        payload.get("accountType")
        or payload.get("account_type")
        or request.args.get("accountType")
    )
    cleared_scope = account_type or "all"

    if account_type:
        account_type = credentials_store._normalize_account_type(account_type)
        credentials_store.clear_credentials(account_type, user_id=current_user.id)
        if binance_log_manager:
            binance_log_manager.add(
                "CREDENTIAL_CLEARED",
                f"Cleared {account_type.upper()} credentials.",
                severity="warning",
                account_type=account_type,
                user_id=current_user.id,
            )
    else:
        credentials_store.clear_credentials(user_id=current_user.id)
        if binance_log_manager:
            binance_log_manager.add(
                "CREDENTIAL_CLEARED",
                "Cleared all stored credentials.",
                severity="warning",
                account_type="spot",
                user_id=current_user.id,
            )
            binance_log_manager.add(
                "CREDENTIAL_CLEARED",
                "Cleared all stored credentials.",
                severity="warning",
                account_type="futures",
                user_id=current_user.id,
            )

    status = status_fn(
        include_connection=True, include_logs=True, user_id=current_user.id
    )
    dashboard_data["binance_credentials"] = status
    dashboard_data["binance_logs"] = status.get("logs", [])
    dashboard_data["real_trading_status"] = status.get("ultimate_status") or {}
    dashboard_data["optimized_real_trading_status"] = (
        status.get("optimized_status") or {}
    )
    dashboard_data["system_status"]["paper_trading"] = getattr(
        ultimate_trader, "paper_trading", True
    )
    dashboard_data["system_status"]["real_trading_ready"] = bool(
        getattr(ultimate_trader, "real_trading_enabled", False)
    )
    dashboard_data["optimized_system_status"]["paper_trading"] = getattr(
        optimized_trader, "paper_trading", True
    )
    dashboard_data["optimized_system_status"]["real_trading_ready"] = bool(
        getattr(optimized_trader, "real_trading_enabled", False)
    )

    response = {
        "cleared": True,
        "account_type": cleared_scope,
        "status": status,
        "ultimate_status": status.get("ultimate_status"),
        "optimized_status": status.get("optimized_status"),
    }
    return jsonify(response)


@trading_bp.route(
    "/api/binance/credentials/test",
    methods=["POST"],
    endpoint="api_binance_credentials_test",
)
@login_required
def api_binance_credentials_test():
    ctx = _get_bot_context()
    credentials_service = ctx.get("binance_credential_service")

    if not credentials_service:
        return jsonify({"error": "Credential service unavailable"}), 500

    payload = request.get_json(silent=True) or {}
    api_key = (payload.get("apiKey") or payload.get("api_key") or "").strip()
    api_secret = (payload.get("apiSecret") or payload.get("api_secret") or "").strip()
    testnet_flag = _coerce_bool_with_ctx(ctx, payload.get("testnet"), default=True)

    if not api_key or not api_secret:
        return jsonify({"error": "API key and secret are required for testing"}), 400

    result = credentials_service.test_credentials(
        api_key, api_secret, testnet=testnet_flag
    )
    return jsonify(result)


@trading_bp.route("/api/binance/logs", methods=["GET"], endpoint="api_binance_logs")
def api_binance_logs():
    ctx = _get_bot_context()
    binance_log_manager = ctx.get("binance_log_manager")

    limit = request.args.get("limit", 50, type=int)
    account_type = request.args.get("accountType") or request.args.get("account_type")
    severity = request.args.get("severity")

    if not binance_log_manager:
        return jsonify({"logs": [], "count": 0})

    user_id = current_user.id if getattr(current_user, "is_authenticated", False) else None

    logs = binance_log_manager.get_logs(
        limit=limit, account_type=account_type, severity=severity, user_id=user_id
    )
    return jsonify(
        {
            "logs": logs,
            "count": len(logs),
            "limit": limit,
            "account_type": account_type or "all",
        }
    )


@trading_bp.route("/api/futures", methods=["GET"], endpoint="api_futures_dashboard")
def api_futures_dashboard():
    try:
        ctx = _get_bot_context()
        dashboard_data = _get_dashboard_data(ctx)
        futures_data_lock = ctx.get("futures_data_lock")
        futures_dashboard_state = ctx.get("futures_dashboard_state", {})
        ensure_manual_defaults = ctx.get("ensure_futures_manual_defaults")
        manual_service = _get_futures_manual_service(ctx)

        # Check if we're in test mode (no futures_data_lock means test mode)
        if not futures_data_lock:
            return (
                jsonify(
                    {
                        "error": "Futures data unavailable",
                        "message": "Futures trading not available in test mode",
                        "status": "inactive",
                        "timestamp": time.time(),
                    }
                ),
                200,
            )

        if manual_service is None and not callable(ensure_manual_defaults):
            return jsonify({"error": "Futures data unavailable"}), 500

        with futures_data_lock:
            snapshot = deepcopy(
                dashboard_data.get("futures_dashboard", futures_dashboard_state)
            )
        try:
            if manual_service is not None:
                snapshot["manual"] = manual_service.get_manual_state(
                    update_dashboard=True
                )
            else:
                snapshot["manual"] = ensure_manual_defaults(update_dashboard=True)
        except Exception as exc:  # pragma: no cover - defensive
            current_app.logger.error("Failed to load manual futures state: %s", exc)
            snapshot["manual"] = {"error": "Manual state unavailable"}
        snapshot["timestamp"] = time.time()
        return jsonify(snapshot)
    except (RuntimeError, KeyError, AttributeError):
        # Test mode or context not fully initialized
        return (
            jsonify(
                {
                    "error": "Futures data unavailable",
                    "message": "Futures trading not available in test mode",
                    "status": "inactive",
                    "timestamp": time.time(),
                }
            ),
            200,
        )


@trading_bp.route(
    "/api/futures/manual", methods=["GET"], endpoint="api_futures_manual_state"
)
def api_futures_manual_state():
    ctx = _get_bot_context()
    ensure_manual_defaults = ctx.get("ensure_futures_manual_defaults")
    futures_manual_lock = ctx.get("futures_manual_lock")
    futures_manual_settings = ctx.get("futures_manual_settings")
    futures_symbols = ctx.get("futures_symbols", [])
    manual_service = _get_futures_manual_service(ctx)

    if manual_service is not None:
        try:
            manual = manual_service.get_manual_state(
                include_symbols=True, update_dashboard=True
            )
            return jsonify(manual)
        except Exception as exc:  # pragma: no cover - defensive logging
            current_app.logger.error("Failed to fetch manual futures state: %s", exc)
            return jsonify({"error": "Manual futures state unavailable"}), 500

    if not all(
        [callable(ensure_manual_defaults), futures_manual_lock, futures_manual_settings]
    ):
        return jsonify({"error": "Manual futures state unavailable"}), 500

    ensure_manual_defaults(update_dashboard=True)
    with futures_manual_lock:
        manual = deepcopy(futures_manual_settings)
    manual["available_symbols"] = list(futures_symbols)
    manual["timestamp"] = time.time()
    return jsonify(manual)


@trading_bp.route(
    "/api/futures/manual/select", methods=["POST"], endpoint="api_futures_manual_select"
)
@subscription_required
def api_futures_manual_select():
    ctx = _get_bot_context()
    manual_service = _get_futures_manual_service(ctx)
    ensure_manual_defaults = ctx.get("ensure_futures_manual_defaults")
    futures_manual_lock = ctx.get("futures_manual_lock")
    futures_manual_settings = ctx.get("futures_manual_settings")
    futures_symbols = ctx.get("futures_symbols", [])
    trading_config = ctx.get("trading_config")

    payload = request.get_json(silent=True) or {}
    raw_symbol = payload.get("symbol")
    leverage = payload.get("leverage")
    order_size = payload.get("order_size_usdt")

    if manual_service is not None:
        try:
            result = manual_service.select_symbol(
                raw_symbol,
                leverage=leverage,
                order_size_usdt=order_size,
            )
            return jsonify(result)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # pragma: no cover - defensive logging
            current_app.logger.error(
                "Failed to update manual futures selection: %s", exc
            )
            return jsonify({"error": "Unable to update manual futures settings"}), 500

    dashboard_data = _get_dashboard_data(ctx)

    if not all(
        [
            callable(ensure_manual_defaults),
            futures_manual_lock,
            futures_manual_settings,
            trading_config,
        ]
    ):
        return jsonify({"error": "Manual futures configuration unavailable"}), 500

    ensure_manual_defaults(update_dashboard=False)
    if not raw_symbol:
        return jsonify({"error": "Symbol is required"}), 400

    symbol = str(raw_symbol).strip().upper()
    if symbol not in futures_symbols:
        return (
            jsonify({"error": f"Symbol {symbol} is not in the allowed futures list"}),
            400,
        )

    with futures_manual_lock:
        futures_manual_settings["selected_symbol"] = symbol
        futures_manual_settings["last_error"] = None
        futures_manual_settings["updated_at"] = time.time()
        trading_config["futures_selected_symbol"] = symbol

        if leverage is not None:
            try:
                leverage_value = max(
                    1,
                    min(
                        float(leverage), trading_config.get("futures_max_leverage", 20)
                    ),
                )
                futures_manual_settings["leverage"] = leverage_value
                trading_config["futures_manual_leverage"] = leverage_value
            except (TypeError, ValueError):
                futures_manual_settings[
                    "last_error"
                ] = f"Invalid leverage value: {leverage}"
        if order_size is not None:
            try:
                order_size_value = max(1.0, float(order_size))
                futures_manual_settings["order_size_usdt"] = order_size_value
                trading_config["futures_manual_default_notional"] = order_size_value
            except (TypeError, ValueError):
                futures_manual_settings[
                    "last_error"
                ] = f"Invalid order size value: {order_size}"

        dashboard_data["futures_manual"] = futures_manual_settings

    return jsonify(
        {
            "selected_symbol": symbol,
            "leverage": futures_manual_settings["leverage"],
            "order_size_usdt": futures_manual_settings["order_size_usdt"],
            "last_error": futures_manual_settings["last_error"],
        }
    )


@trading_bp.route(
    "/api/futures/manual/toggle",
    methods=["POST"],
    endpoint="api_futures_manual_toggle_trading",
)
@subscription_required
def api_futures_manual_toggle_trading():
    ctx = _get_bot_context()
    manual_service = _get_futures_manual_service(ctx)
    ensure_manual_defaults = ctx.get("ensure_futures_manual_defaults")
    futures_manual_lock = ctx.get("futures_manual_lock")
    futures_manual_settings = ctx.get("futures_manual_settings")
    trading_config = ctx.get("trading_config")
    ultimate_trader = ctx.get("ultimate_trader")
    dashboard_data = _get_dashboard_data(ctx)

    payload = request.get_json(silent=True) or {}
    enable = payload.get("enable")
    mode = payload.get("mode")

    if manual_service is not None:
        if not ultimate_trader:
            return jsonify({"error": "Manual futures toggle unavailable"}), 500
        try:
            result = manual_service.toggle_auto_trading(
                enable=enable,
                mode=mode,
                ultimate_trader=ultimate_trader,
            )
            return jsonify(result)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:  # pragma: no cover - defensive logging
            current_app.logger.error("Failed to toggle manual futures trading: %s", exc)
            return jsonify({"error": "Unable to toggle manual futures trading"}), 500

    if not all(
        [
            callable(ensure_manual_defaults),
            futures_manual_lock,
            futures_manual_settings,
            trading_config,
            ultimate_trader,
        ]
    ):
        return jsonify({"error": "Manual futures toggle unavailable"}), 500

    ensure_manual_defaults(update_dashboard=False)
    if enable is None:
        enable = not futures_manual_settings.get("auto_trade_enabled", False)

    enable = bool(enable)
    mode = (mode or futures_manual_settings.get("mode") or "manual").lower()

    if mode not in ("manual", "analysis"):
        return jsonify({"error": "Mode must be manual or analysis"}), 400

    with futures_manual_lock:
        selected_symbol = futures_manual_settings.get("selected_symbol")
        if enable and not selected_symbol:
            return (
                jsonify({"error": "Select a symbol before enabling manual trading"}),
                400,
            )

        futures_manual_settings["auto_trade_enabled"] = enable
        futures_manual_settings["mode"] = mode
        futures_manual_settings["updated_at"] = time.time()
        trading_config["futures_manual_auto_trade"] = enable
        trading_config["futures_manual_mode"] = mode
        dashboard_data["futures_manual"] = futures_manual_settings

        if enable and not getattr(ultimate_trader, "futures_trading_enabled", False):
            futures_manual_settings["auto_trade_enabled"] = False
            futures_manual_settings["updated_at"] = time.time()
            trading_config["futures_manual_auto_trade"] = False
            dashboard_data["futures_manual"] = futures_manual_settings
            system_status = dashboard_data.get("system_status") or {}
            system_status["futures_manual_auto_trade"] = False
            system_status["futures_trading_ready"] = bool(
                getattr(ultimate_trader, "futures_trading_enabled", False)
            )
            dashboard_data["system_status"] = system_status
            return (
                jsonify(
                    {
                        "error": "Futures trader not connected. Add futures API credentials before enabling auto trading."
                    }
                ),
                400,
            )

    system_status = dashboard_data.get("system_status") or {}
    system_status["futures_manual_auto_trade"] = enable
    system_status["futures_trading_ready"] = bool(
        getattr(ultimate_trader, "futures_trading_enabled", False)
    )
    dashboard_data["system_status"] = system_status
    dashboard_data["futures_manual"] = ensure_manual_defaults(update_dashboard=False)

    _update_trading_config_state_file("futures_manual_auto_trade", enable)
    _update_trading_config_state_file("futures_manual_mode", mode)
    _update_trading_config_state_file(
        "futures_selected_symbol", futures_manual_settings.get("selected_symbol")
    )

    return jsonify(
        {
            "auto_trade_enabled": enable,
            "mode": mode,
            "selected_symbol": futures_manual_settings.get("selected_symbol"),
        }
    )


@trading_bp.route("/api/spot/toggle", methods=["POST"], endpoint="api_spot_toggle")
@subscription_required
def api_spot_toggle():
    ctx = _get_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    market_data_service = ctx.get("market_data_service")

    ultimate_trader = None
    optimized_trader = None
    if (
        getattr(current_user, "is_authenticated", False)
        and market_data_service is not None
        and hasattr(market_data_service, "_get_or_create_user_traders")
    ):
        try:
            ultimate_trader, optimized_trader = market_data_service._get_or_create_user_traders(
                int(current_user.id)
            )
        except Exception:
            ultimate_trader = None
            optimized_trader = None

    if ultimate_trader is None or optimized_trader is None:
        ultimate_trader = ctx.get("ultimate_trader")
        optimized_trader = ctx.get("optimized_trader")

    if not all([ultimate_trader, optimized_trader]):
        return jsonify({"error": "Trading engines unavailable"}), 500

    try:
        payload = request.get_json(silent=True) or {}
        enable = payload.get("enable")

        if enable is None:
            enable = not getattr(ultimate_trader, "trading_enabled", False)

        enable = bool(enable)

        ultimate_trader.trading_enabled = enable
        optimized_trader.trading_enabled = enable

        dashboard_data["system_status"]["trading_enabled"] = enable
        dashboard_data["system_status"]["paper_trading"] = getattr(
            ultimate_trader, "paper_trading", True
        )
        dashboard_data["system_status"]["real_trading_ready"] = bool(
            getattr(ultimate_trader, "real_trading_enabled", False)
        )
        dashboard_data["optimized_system_status"]["trading_enabled"] = enable
        dashboard_data["optimized_system_status"]["paper_trading"] = getattr(
            optimized_trader, "paper_trading", True
        )
        dashboard_data["optimized_system_status"]["real_trading_ready"] = bool(
            getattr(optimized_trader, "real_trading_enabled", False)
        )

        persistence_profile = getattr(ultimate_trader, "persistence_profile", None)
        _update_state_file("trading_enabled", enable, profile=persistence_profile)

        # Diagnostic: log instance ids and flags so we can compare with persistence
        try:
            print(
                f"[TOGGLE DEBUG] spot toggle: id(ultimate_trader)={id(ultimate_trader)}, id(optimized_trader)={id(optimized_trader)}, ultimate.trading_enabled={getattr(ultimate_trader,'trading_enabled',None)}, ultimate.paper_trading={getattr(ultimate_trader,'paper_trading',None)}"
            )
        except Exception:
            pass

        # Also attempt to trigger the persistence scheduler so the full
        # runtime state (including trader flags) is saved to disk.
        try:
            scheduler = ctx.get("persistence_scheduler")
            ultimate_ml = ctx.get("ultimate_ml_system")
            trading_config = ctx.get("trading_config") or {}
            symbols = list(_top_symbols(ctx)) if "_top_symbols" in globals() else list(
                ctx.get("top_symbols") or []
            )
            history = ctx.get("historical_data") or {}
            if scheduler and hasattr(scheduler, "manual_save"):
                try:
                    try:
                        scheduler.manual_save(
                            ultimate_trader,
                            ultimate_ml,
                            trading_config,
                            symbols,
                            history,
                            profile=persistence_profile,
                        )
                    except TypeError:
                        scheduler.manual_save(
                            ultimate_trader, ultimate_ml, trading_config, symbols, history
                        )
                except Exception as exc:  # pragma: no cover - best-effort persistence
                    print(f"Error saving state after spot toggle: {exc}")
        except Exception:
            pass

        return jsonify(
            {
                "trading_enabled": enable,
                "message": f"Spot trading {'enabled' if enable else 'disabled'} for both profiles",
            }
        )
    except Exception as exc:
        print(f"Error in /api/spot/toggle: {exc}")
        return jsonify({"error": str(exc)}), 500


@trading_bp.route("/api/spot/trade", methods=["POST"], endpoint="api_spot_trade")
@subscription_required
def api_spot_trade():
    ctx = _get_bot_context()
    get_user_trader = ctx.get("get_user_trader")
    record_user_trade = ctx.get("record_user_trade")

    if not callable(get_user_trader) or not callable(record_user_trade):
        return jsonify({"error": "User trading services unavailable"}), 500

    try:
        payload = request.get_json(silent=True) or {}
        symbol = payload.get("symbol", "").upper().strip()
        side = payload.get("side", "").upper()
        quantity = payload.get("quantity")
        price = payload.get("price")
        signal_source = payload.get("signal_source", "manual")
        confidence_score = payload.get("confidence_score", 1.0)

        if not symbol or not side or quantity is None:
            return jsonify({"error": "Symbol, side, and quantity are required"}), 400

        if side not in ["BUY", "SELL"]:
            return jsonify({"error": "Side must be BUY or SELL"}), 400

        if not symbol.endswith("USDT"):
            symbol = symbol + "USDT"

        user_trader = get_user_trader(current_user.id, "ultimate")
        result = user_trader.execute_manual_trade(symbol, side, quantity, price)

        if result.get("success"):
            record_user_trade(
                user_id=current_user.id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=result.get("price", price),
                trade_type="manual_spot",
                signal_source=signal_source,
                confidence_score=confidence_score,
            )

            return jsonify(
                {
                    "message": f"Spot {side} order executed successfully",
                    "order": result.get("order", {}),
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                }
            )
        return jsonify({"error": result.get("error", "Trade execution failed")}), 400
    except Exception as exc:
        print(f"Error in /api/spot/trade: {exc}")
        return jsonify({"error": str(exc)}), 500


@trading_bp.route(
    "/api/futures/toggle", methods=["POST"], endpoint="api_futures_toggle"
)
@subscription_required
def api_futures_toggle():
    ctx = _get_bot_context()
    dashboard_data = _get_dashboard_data(ctx)
    market_data_service = ctx.get("market_data_service")
    ultimate_trader = None
    optimized_trader = None
    futures_market_data_service = ctx.get("futures_market_data_service")
    trading_config = ctx.get("trading_config")
    if not isinstance(trading_config, dict):
        trading_config = {}

    user_scoped = False
    persistence_profile = None
    if (
        getattr(current_user, "is_authenticated", False)
        and market_data_service is not None
        and hasattr(market_data_service, "_get_or_create_user_traders")
    ):
        try:
            ultimate_trader, optimized_trader = market_data_service._get_or_create_user_traders(
                int(current_user.id)
            )
            user_scoped = True
            persistence_profile = getattr(ultimate_trader, "persistence_profile", None)
        except Exception:
            ultimate_trader = None
            optimized_trader = None
            user_scoped = False

    if ultimate_trader is None or optimized_trader is None:
        ultimate_trader = ctx.get("ultimate_trader")
        optimized_trader = ctx.get("optimized_trader")
        user_scoped = False

    if not all([ultimate_trader, optimized_trader]):
        return jsonify({"error": "Trading engines unavailable"}), 500

    if dashboard_data is not None:
        dashboard_data.setdefault("system_status", {})
        dashboard_data.setdefault("optimized_system_status", {})

    try:
        payload = request.get_json(silent=True) or {}
        enable = payload.get("enable")

        if enable is None:
            enable = not bool(
                getattr(ultimate_trader, "futures_trading_enabled", False)
            )

        enable = bool(enable)

        ultimate_trader.futures_trading_enabled = enable
        optimized_trader.futures_trading_enabled = enable

        # Legacy single-user behavior: futures market-data loop is gated on
        # TRADING_CONFIG.futures_enabled, so keep it aligned.
        if not user_scoped and isinstance(trading_config, dict):
            trading_config["futures_enabled"] = enable

        # Diagnostic: log instance ids and flags so we can compare with persistence
        try:
            print(
                f"[TOGGLE DEBUG] futures toggle: id(ultimate_trader)={id(ultimate_trader)}, ultimate.futures_trading_enabled={getattr(ultimate_trader,'futures_trading_enabled',None)}, ultimate.paper_trading={getattr(ultimate_trader,'paper_trading',None)}"
            )
        except Exception:
            pass

        dashboard_data["system_status"]["futures_trading_enabled"] = enable
        dashboard_data["system_status"]["futures_trading_ready"] = enable
        dashboard_data["optimized_system_status"]["futures_trading_enabled"] = enable
        dashboard_data["optimized_system_status"]["futures_trading_ready"] = enable

        dashboard_data["system_status"]["futures_enabled"] = bool(
            enable if user_scoped else trading_config.get("futures_enabled", False)
        )

        _update_state_file("futures_trading_enabled", enable, profile=persistence_profile)
        if not user_scoped:
            _update_trading_config_state_file("futures_enabled", enable)

        # Keep the background futures loop aligned with config only in legacy
        # single-user mode. In multi-user mode, a single user's toggle must not
        # start/stop a shared background service.
        if not user_scoped:
            try:
                if futures_market_data_service is not None:
                    if enable:
                        futures_market_data_service.start()
                    else:
                        futures_market_data_service.stop()
            except Exception as exc:  # pragma: no cover - defensive
                current_app.logger.warning(
                    "Failed to start/stop futures market data service: %s", exc
                )

        return jsonify(
            {
                "futures_trading_enabled": enable,
                "futures_enabled": enable
                if user_scoped
                else (
                    bool(trading_config.get("futures_enabled", False))
                    if isinstance(trading_config, dict)
                    else None
                ),
                "message": f"Futures trading {'enabled' if enable else 'disabled'}{' for current user' if user_scoped else ' for both profiles'}",
            }
        )
    except Exception as exc:
        print(f"Error in /api/futures/toggle: {exc}")
        return jsonify({"error": str(exc)}), 500


@trading_bp.route(
    "/api/futures/diagnostics",
    methods=["GET"],
    endpoint="api_futures_diagnostics",
)
@subscription_required
def api_futures_diagnostics():
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Admin access required"}), 403

    ctx = _get_bot_context()
    ultimate_trader = ctx.get("ultimate_trader")
    optimized_trader = ctx.get("optimized_trader")
    trading_config = ctx.get("trading_config") or {}
    futures_market_data_service = ctx.get("futures_market_data_service")
    futures_dashboard_state = ctx.get("futures_dashboard_state") or {}
    futures_manual_settings = ctx.get("futures_manual_settings") or {}

    futures_trader = getattr(ultimate_trader, "futures_trader", None)
    futures_ready = bool(getattr(futures_trader, "is_ready", lambda: False)()) if futures_trader else False

    thread = getattr(futures_market_data_service, "_thread", None)
    service_alive = bool(thread.is_alive()) if thread else False

    config_futures_enabled = bool(trading_config.get("futures_enabled", False))
    trader_futures_enabled = bool(
        getattr(ultimate_trader, "futures_trading_enabled", False)
    )
    manual_auto_trade = bool(trading_config.get("futures_manual_auto_trade", False))

    blockers: list[str] = []
    if not config_futures_enabled:
        blockers.append("TRADING_CONFIG.futures_enabled is false (loop will not run)")
    if not trader_futures_enabled:
        blockers.append("ultimate_trader.futures_trading_enabled is false")
    if manual_auto_trade and not futures_ready:
        blockers.append("Manual auto-trade enabled but futures trader not ready")
    if manual_auto_trade and not futures_manual_settings.get("selected_symbol"):
        blockers.append("Manual auto-trade enabled but no selected_symbol")

    return jsonify(
        {
            "config": {
                "futures_enabled": config_futures_enabled,
                "futures_manual_auto_trade": manual_auto_trade,
                "futures_manual_mode": trading_config.get("futures_manual_mode"),
                "futures_selected_symbol": trading_config.get("futures_selected_symbol"),
            },
            "trader": {
                "ultimate_futures_trading_enabled": trader_futures_enabled,
                "optimized_futures_trading_enabled": bool(
                    getattr(optimized_trader, "futures_trading_enabled", False)
                ),
                "futures_trader_ready": futures_ready,
            },
            "service": {
                "futures_market_data_service_alive": service_alive,
                "last_futures_update": futures_dashboard_state.get("last_update"),
            },
            "manual": {
                "selected_symbol": futures_manual_settings.get("selected_symbol"),
                "auto_trade_enabled": futures_manual_settings.get("auto_trade_enabled"),
                "mode": futures_manual_settings.get("mode"),
                "last_error": futures_manual_settings.get("last_error"),
                "updated_at": futures_manual_settings.get("updated_at"),
            },
            "blockers": blockers,
        }
    )


@trading_bp.route("/api/futures/trade", methods=["POST"], endpoint="api_futures_trade")
@subscription_required
def api_futures_trade():
    try:
        ctx = _get_bot_context()
        get_user_trader = ctx.get("get_user_trader")
        record_user_trade = ctx.get("record_user_trade")

        if not callable(get_user_trader) or not callable(record_user_trade):
            return jsonify({"error": "User trading services unavailable"}), 500

        try:
            payload = request.get_json(silent=True) or {}
            symbol = payload.get("symbol", "").upper().strip()
            side = payload.get("side", "").upper()
            quantity = payload.get("quantity")
            leverage = payload.get("leverage", 1)
            price = payload.get("price")
            signal_source = payload.get("signal_source", "manual")
            confidence_score = payload.get("confidence_score", 1.0)

            if not symbol or not side or quantity is None:
                return (
                    jsonify({"error": "Symbol, side, and quantity are required"}),
                    400,
                )

            if side not in ["BUY", "SELL"]:
                return jsonify({"error": "Side must be BUY or SELL"}), 400

            if not symbol.endswith("USDT"):
                symbol = symbol + "USDT"

            user_trader = get_user_trader(current_user.id, "ultimate")
            result = user_trader.execute_manual_futures_trade(
                symbol, side, quantity, leverage, price
            )

            if result.get("success"):
                record_user_trade(
                    current_user.id,
                    symbol,
                    side,
                    quantity,
                    price,
                    "manual_futures",
                    signal_source,
                    confidence_score,
                    leverage,
                )
                return jsonify(
                    {
                        "message": f"Futures {side} order executed successfully",
                        "order": result.get("order", {}),
                        "symbol": symbol,
                        "side": side,
                        "quantity": quantity,
                        "leverage": leverage,
                        "price": price,
                    }
                )
            return (
                jsonify(
                    {"error": result.get("error", "Futures trade execution failed")}
                ),
                400,
            )
        except Exception as exc:
            print(f"Error in /api/futures/trade: {exc}")
            return jsonify({"error": str(exc)}), 500
    except (RuntimeError, KeyError, AttributeError):
        # Test mode or context not fully initialized
        return (
            jsonify(
                {
                    "error": "Futures trading not available in test mode",
                    "message": "Cannot execute futures trades in test mode",
                }
            ),
            200,
        )
