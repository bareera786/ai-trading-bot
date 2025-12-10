"""System maintenance endpoints for persistence, training, and symbol management."""
from __future__ import annotations

import os
import threading
import time
from datetime import datetime
from typing import Any, Iterable

from flask import Blueprint, current_app, jsonify, request, send_file
from flask_login import login_required


system_ops_bp = Blueprint("system_ops", __name__)


def _ctx() -> dict[str, Any]:
    ctx = current_app.extensions.get("ai_bot_context")
    if not ctx:
        raise RuntimeError("AI bot context is not initialized")
    return ctx


def _dashboard_data(ctx: dict[str, Any]) -> dict[str, Any]:
    data = ctx.get("dashboard_data")
    if data is None:
        raise RuntimeError("Dashboard data is unavailable")
    return data


def _ctx_callable(ctx: dict[str, Any], key: str):
    value = ctx.get(key)
    return value if callable(value) else None


def _ml_system(ctx: dict[str, Any], mode: str):
    system = (
        ctx.get("optimized_ml_system")
        if mode == "optimized"
        else ctx.get("ultimate_ml_system")
    )
    if not system:
        raise RuntimeError(f"ML system for mode '{mode}' is unavailable")
    return system


def _traders(ctx: dict[str, Any]):
    ultimate = ctx.get("ultimate_trader")
    optimized = ctx.get("optimized_trader")
    if not ultimate and not optimized:
        raise RuntimeError("Trader instances unavailable")
    return ultimate, optimized


def _persistence_manager(ctx: dict[str, Any]):
    manager = ctx.get("persistence_manager")
    if not manager:
        raise RuntimeError("Persistence manager unavailable")
    return manager


def _persistence_scheduler(ctx: dict[str, Any]):
    scheduler = ctx.get("persistence_scheduler")
    if not scheduler:
        raise RuntimeError("Persistence scheduler unavailable")
    return scheduler


def _historical_data(ctx: dict[str, Any]) -> dict[str, Any]:
    data = ctx.get("historical_data")
    if data is None:
        data = {}
        ctx["historical_data"] = data
    return data


def _top_symbols(ctx: dict[str, Any]) -> Iterable[str]:
    symbols = ctx.get("top_symbols")
    return symbols if symbols is not None else []


def _disabled_symbols(ctx: dict[str, Any]) -> Iterable[str]:
    disabled = ctx.get("disabled_symbols")
    if isinstance(disabled, Iterable):
        return disabled
    getter = _ctx_callable(ctx, "get_disabled_symbols")
    return getter() if callable(getter) else []


def _all_known_symbols(ctx: dict[str, Any]) -> list[str]:
    getter = _ctx_callable(ctx, "get_all_known_symbols")
    if callable(getter):
        try:
            return list(getter())
        except Exception:
            pass
    top = list(_top_symbols(ctx))
    disabled = list(_disabled_symbols(ctx))
    return sorted(set(top) | set(disabled))


def _refresh_symbol_counters(ctx: dict[str, Any]) -> None:
    refresher = _ctx_callable(ctx, "refresh_symbol_counters")
    if callable(refresher):
        try:
            refresher()
        except Exception:
            pass


def _clear_symbol_from_dashboard(ctx: dict[str, Any], symbol: str) -> None:
    clearer = _ctx_callable(ctx, "clear_symbol_from_dashboard")
    if callable(clearer):
        try:
            clearer(symbol)
        except Exception:
            pass


def _is_symbol_disabled(ctx: dict[str, Any], symbol: str) -> bool:
    checker = _ctx_callable(ctx, "is_symbol_disabled")
    if callable(checker):
        try:
            return bool(checker(symbol))
        except Exception:
            return False
    disabled = set(_disabled_symbols(ctx))
    return symbol in disabled


def _normalize_symbol(symbol: Any) -> str:
    if not symbol:
        return ""
    normalized = str(symbol).strip().upper()
    if normalized and not normalized.endswith("USDT"):
        normalized = f"{normalized}USDT"
    return normalized


def _normalize_request_symbol(payload: Any) -> str:
    if isinstance(payload, dict):
        return _normalize_symbol(payload.get("symbol"))
    return _normalize_symbol(payload)


def _update_ml_telemetry(ctx: dict[str, Any]) -> None:
    dashboard_data = ctx.get("dashboard_data") or {}
    ml_key = dashboard_data.get("ml_telemetry")
    if not isinstance(ml_key, dict):
        return
    ultimate = ctx.get("ultimate_ml_system")
    optimized = ctx.get("optimized_ml_system")
    if ultimate and hasattr(ultimate, "get_ml_telemetry"):
        try:
            ml_key["ultimate"] = ultimate.get_ml_telemetry()
        except Exception:
            pass
    if optimized and hasattr(optimized, "get_ml_telemetry"):
        try:
            ml_key["optimized"] = optimized.get_ml_telemetry()
        except Exception:
            pass


@system_ops_bp.route("/api/performance_chart")
def api_performance_chart():
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)
    chart = (
        dashboard_data.get("performance_chart")
        or dashboard_data.get("performance")
        or {}
    )
    return jsonify({"chart_data": chart, "timestamp": time.time()})


@system_ops_bp.route("/api/training_logs")
def api_training_logs():
    ctx = _ctx()
    mode = request.args.get("mode", "ultimate").lower()
    system = _ml_system(ctx, mode)
    logs = []
    getter = getattr(system, "get_training_logs", None)
    if callable(getter):
        try:
            logs = getter()
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
    return jsonify({"mode": mode, "logs": logs})


@system_ops_bp.route("/api/training_progress")
def api_training_progress():
    ctx = _ctx()
    mode = request.args.get("mode", "ultimate").lower()
    system = _ml_system(ctx, mode)
    progress = getattr(system, "training_progress", None)
    return jsonify({"mode": mode, "progress": progress})


@system_ops_bp.route("/api/persistence/status")
def api_persistence_status():
    ctx = _ctx()
    manager = _persistence_manager(ctx)
    try:
        status = manager.get_persistence_status()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify(status)


@system_ops_bp.route("/api/persistence/save", methods=["POST"])
def api_persistence_save():
    ctx = _ctx()
    scheduler = _persistence_scheduler(ctx)
    ultimate, _ = _traders(ctx)
    ultimate_ml = ctx.get("ultimate_ml_system")
    trading_config = ctx.get("trading_config") or {}
    symbols = list(_top_symbols(ctx))
    history = _historical_data(ctx)

    try:
        success = scheduler.manual_save(
            ultimate,
            ultimate_ml,
            trading_config,
            symbols,
            history,
        )
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    message = "Manual state save completed" if success else "Manual state save failed"
    return jsonify({"success": bool(success), "message": message})


@system_ops_bp.route("/api/persistence/backups")
def api_persistence_backups():
    ctx = _ctx()
    manager = _persistence_manager(ctx)
    backup_dir = getattr(manager, "backup_dir", None)
    backups: list[dict[str, Any]] = []
    if backup_dir and os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if not (
                filename.startswith("state_backup_") and filename.endswith(".json")
            ):
                continue
            file_path = os.path.join(backup_dir, filename)
            created = datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
            size_kb = os.path.getsize(file_path) // 1024
            backups.append(
                {"filename": filename, "created": created, "size_kb": size_kb}
            )
    backups.sort(key=lambda item: item["created"], reverse=True)
    return jsonify({"backups": backups})


@system_ops_bp.route("/api/toggle_trading", methods=["POST"])
@login_required
def api_toggle_trading():
    ctx = _ctx()
    ultimate, optimized = _traders(ctx)
    dashboard_data = _dashboard_data(ctx)

    enable = not getattr(ultimate, "trading_enabled", False)
    ultimate.trading_enabled = enable
    if optimized:
        optimized.trading_enabled = enable

    system_status = dashboard_data.setdefault("system_status", {})
    system_status["trading_enabled"] = enable
    system_status["paper_trading"] = getattr(ultimate, "paper_trading", True)
    system_status["real_trading_ready"] = bool(
        getattr(ultimate, "real_trading_enabled", False)
    )

    optimized_status = dashboard_data.setdefault("optimized_system_status", {})
    optimized_status["trading_enabled"] = (
        enable if optimized else optimized_status.get("trading_enabled")
    )
    optimized_status["paper_trading"] = (
        getattr(optimized, "paper_trading", True)
        if optimized
        else optimized_status.get("paper_trading")
    )
    optimized_status["real_trading_ready"] = (
        bool(getattr(optimized, "real_trading_enabled", False))
        if optimized
        else optimized_status.get("real_trading_ready")
    )

    return jsonify(
        {
            "trading_enabled": enable,
            "optimized_trading_enabled": enable if optimized else None,
            "message": f"Trading {'enabled' if enable else 'disabled'} for both profiles",
        }
    )


@system_ops_bp.route("/api/train_models", methods=["POST"])
@login_required
def api_train_models():
    ctx = _ctx()
    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")
    if not ultimate_system or not optimized_system:
        return jsonify({"error": "ML systems unavailable"}), 500

    def train_async():
        try:
            ultimate_system.train_all_ultimate_models(use_real_data=True)
            optimized_system.train_all_optimized_models(use_real_data=True)
        except Exception as exc:
            print(f"Error during bulk training: {exc}")

    threading.Thread(target=train_async, daemon=True).start()
    return jsonify({"message": "Training started for all symbols"})


@system_ops_bp.route("/api/train_single", methods=["POST"])
def api_train_single():
    ctx = _ctx()
    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")
    if not ultimate_system or not optimized_system:
        return jsonify({"error": "ML systems unavailable"}), 500

    data = request.get_json(silent=True) or {}
    symbol = _normalize_symbol(data.get("symbol"))

    if not symbol:
        return jsonify({"error": "Symbol required"}), 400

    def train_async():
        try:
            ultimate_system.train_ultimate_model(symbol, use_real_data=True)
            optimized_system.train_optimized_model(symbol, use_real_data=True)
        except Exception as exc:
            print(f"Error training {symbol}: {exc}")

    threading.Thread(target=train_async, daemon=True).start()
    return jsonify({"message": f"Training started for {symbol}"})


@system_ops_bp.route("/api/add_symbol", methods=["POST"])
@login_required
def api_add_symbol():
    ctx = _ctx()
    data = request.get_json(silent=True) or {}
    symbol = _normalize_symbol(data.get("symbol"))
    if not symbol:
        return jsonify({"error": "Symbol required"}), 400

    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")
    if not ultimate_system or not optimized_system:
        return jsonify({"error": "ML systems unavailable"}), 500

    success_ultimate = ultimate_system.add_symbol_with_retrain(symbol)
    success_optimized = optimized_system.add_symbol_with_retrain(symbol)

    if success_ultimate and success_optimized:
        _refresh_symbol_counters(ctx)
        return jsonify(
            {
                "message": f"Symbol {symbol} added successfully and training started",
                "symbol": symbol,
            }
        )

    return (
        jsonify(
            {
                "error": f"Failed to add symbol {symbol}",
                "ultimate_success": success_ultimate,
                "optimized_success": success_optimized,
            }
        ),
        500,
    )


@system_ops_bp.route("/api/symbols/disable", methods=["POST"])
@login_required
def api_disable_symbol():
    ctx = _ctx()
    data = request.get_json(silent=True) or {}
    symbol = _normalize_request_symbol(data)

    if not symbol:
        return jsonify({"error": "Symbol required"}), 400

    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")
    disabled_ultimate = (
        ultimate_system.remove_symbol(symbol, permanent=False)
        if ultimate_system
        else False
    )
    disabled_optimized = (
        optimized_system.remove_symbol(symbol, permanent=False)
        if optimized_system
        else False
    )

    if (
        not disabled_ultimate
        and not disabled_optimized
        and not _is_symbol_disabled(ctx, symbol)
    ):
        return jsonify({"error": f"Symbol {symbol} not found"}), 404

    _clear_symbol_from_dashboard(ctx, symbol)

    ultimate, optimized = _traders(ctx)
    for trader in (ultimate, optimized):
        if not trader:
            continue
        if hasattr(trader, "positions") and isinstance(trader.positions, dict):
            trader.positions.pop(symbol, None)
        if hasattr(trader, "latest_market_data") and isinstance(
            trader.latest_market_data, dict
        ):
            trader.latest_market_data.pop(symbol, None)

    _refresh_symbol_counters(ctx)
    _update_ml_telemetry(ctx)

    return jsonify(
        {
            "message": f"Symbol {symbol} disabled successfully",
            "symbol": symbol,
            "status": "disabled",
        }
    )


@system_ops_bp.route("/api/remove_symbol", methods=["POST"])
@login_required
def api_remove_symbol():
    return api_disable_symbol()


@system_ops_bp.route("/api/symbols/enable", methods=["POST"])
@login_required
def api_enable_symbol():
    ctx = _ctx()
    data = request.get_json(silent=True) or {}
    symbol = _normalize_request_symbol(data)
    retrain = bool(data.get("retrain", False))

    if not symbol:
        return jsonify({"error": "Symbol required"}), 400

    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")
    if not ultimate_system or not optimized_system:
        return jsonify({"error": "ML systems unavailable"}), 500

    success_ultimate = ultimate_system.add_symbol(symbol, train_immediately=retrain)
    success_optimized = optimized_system.add_symbol(symbol, train_immediately=retrain)

    history = _historical_data(ctx)
    history.setdefault(symbol, [])

    _refresh_symbol_counters(ctx)
    _update_ml_telemetry(ctx)

    ultimate_ready = symbol in getattr(ultimate_system, "models", {})
    optimized_ready = symbol in getattr(optimized_system, "models", {})

    if not (success_ultimate or success_optimized):
        return (
            jsonify(
                {
                    "error": f"Failed to enable symbol {symbol}",
                    "ultimate_success": success_ultimate,
                    "optimized_success": success_optimized,
                }
            ),
            500,
        )

    return jsonify(
        {
            "message": f"Symbol {symbol} enabled successfully",
            "symbol": symbol,
            "status": "active",
            "ultimate_model_ready": ultimate_ready,
            "optimized_model_ready": optimized_ready,
            "retrained": retrain,
        }
    )


@system_ops_bp.route("/api/symbols", methods=["GET"])
def api_list_symbols():
    ctx = _ctx()
    get_universe = _ctx_callable(ctx, "get_active_trading_universe")
    get_disabled = _ctx_callable(ctx, "get_disabled_symbols")

    all_symbols = _all_known_symbols(ctx)
    active_set = (
        set(get_universe())
        if callable(get_universe)
        else set(sym for sym in _top_symbols(ctx))
    )
    disabled_set = (
        set(get_disabled()) if callable(get_disabled) else set(_disabled_symbols(ctx))
    )

    search = request.args.get("search", "", type=str).strip().upper()
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 15, type=int)

    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    if search:
        all_symbols = [sym for sym in all_symbols if search in sym.upper()]

    all_symbols.sort()
    total = len(all_symbols)
    total_pages = max(1, (total + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages

    start = (page - 1) * page_size
    end = start + page_size
    page_symbols = all_symbols[start:end]

    portfolio_symbols: set[str] = set()
    ultimate, optimized = _traders(ctx)
    for trader in (ultimate, optimized):
        if not trader:
            continue
        positions = getattr(trader, "positions", None)
        if isinstance(positions, dict):
            portfolio_symbols.update(positions.keys())

    def _model_state(system, sym: str):
        if not system:
            return False, None
        if sym in getattr(system, "models", {}):
            model_info = system.models.get(sym, {})
            return True, model_info.get("training_date")
        models_dir = getattr(system, "models_dir", "")
        if models_dir:
            model_path = os.path.join(models_dir, f"{sym}_ultimate_model.pkl")
            return os.path.exists(model_path), None
        return False, None

    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")

    symbols_payload = []
    for idx, sym in enumerate(page_symbols, start=start + 1):
        ultimate_ready, ultimate_trained = _model_state(ultimate_system, sym)
        optimized_ready, optimized_trained = _model_state(optimized_system, sym)
        symbols_payload.append(
            {
                "symbol": sym,
                "index": idx,
                "active": sym in active_set,
                "disabled": sym in disabled_set,
                "ultimate_model_ready": ultimate_ready,
                "optimized_model_ready": optimized_ready,
                "ultimate_last_trained": ultimate_trained,
                "optimized_last_trained": optimized_trained,
                "in_portfolio": sym in portfolio_symbols,
            }
        )

    return jsonify(
        {
            "symbols": symbols_payload,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
            },
            "metrics": {
                "active": len(active_set),
                "disabled": len(disabled_set),
                "known": len(_all_known_symbols(ctx)),
            },
        }
    )


@system_ops_bp.route("/api/start_continuous_training", methods=["POST"])
@login_required
def api_start_continuous_training():
    ctx = _ctx()
    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")
    if not ultimate_system or not optimized_system:
        return jsonify({"error": "ML systems unavailable"}), 500
    ultimate_system.start_continuous_training_cycle()
    optimized_system.start_continuous_training_cycle()
    return jsonify(
        {
            "message": "Continuous training cycles started for ultimate and optimized systems"
        }
    )


@system_ops_bp.route("/api/stop_continuous_training", methods=["POST"])
@login_required
def api_stop_continuous_training():
    ctx = _ctx()
    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")
    if not ultimate_system or not optimized_system:
        return jsonify({"error": "ML systems unavailable"}), 500
    ultimate_system.stop_continuous_training_cycle()
    optimized_system.stop_continuous_training_cycle()
    return jsonify(
        {
            "message": "Continuous training cycles stopped for ultimate and optimized systems"
        }
    )


@system_ops_bp.route("/api/clear_history", methods=["POST"])
@login_required
def api_clear_history():
    ctx = _ctx()
    ultimate, _ = _traders(ctx)
    history = getattr(ultimate, "trade_history", None)
    if not history or not hasattr(history, "clear_history"):
        return jsonify({"error": "Trade history unavailable"}), 500
    success = history.clear_history()
    if success:
        return jsonify({"message": "Trade history cleared successfully"})
    return jsonify({"error": "Failed to clear history"}), 500


@system_ops_bp.route("/api/export_trades")
def api_export_trades():
    ctx = _ctx()
    ultimate, _ = _traders(ctx)
    history = getattr(ultimate, "trade_history", None)
    if not history or not hasattr(history, "export_to_csv"):
        return jsonify({"error": "Trade history unavailable"}), 500
    filepath = history.export_to_csv()
    if filepath and os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "Export failed"}), 500


@system_ops_bp.route("/api/reload_models")
def api_reload_models():
    ctx = _ctx()
    ultimate_system = ctx.get("ultimate_ml_system")
    optimized_system = ctx.get("optimized_ml_system")
    if not ultimate_system or not optimized_system:
        return jsonify({"error": "ML systems unavailable"}), 500

    ultimate_loaded = ultimate_system.load_models()
    optimized_loaded = optimized_system.load_models()

    dashboard_data = _dashboard_data(ctx)
    system_status = dashboard_data.setdefault("system_status", {})
    optimized_status = dashboard_data.setdefault("optimized_system_status", {})
    system_status["models_loaded"] = bool(ultimate_loaded)
    optimized_status["models_loaded"] = bool(optimized_loaded)

    return jsonify(
        {
            "ultimate_models_loaded": ultimate_loaded,
            "optimized_models_loaded": optimized_loaded,
        }
    )
