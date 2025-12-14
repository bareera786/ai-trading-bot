"""Status and health endpoints."""
from __future__ import annotations

import shutil
import time
from copy import deepcopy
from datetime import datetime, timezone

import requests
from flask import Blueprint, current_app, jsonify, Response
from prometheus_client import generate_latest

from app.extensions import db
from app.tasks.manager import _background_task_manager


status_bp = Blueprint("status", __name__)


def _ctx() -> dict:
    ctx = current_app.extensions.get("ai_bot_context")
    if not ctx:
        raise RuntimeError("AI bot context is not initialized")
    return ctx


def _dashboard_data(ctx: dict) -> dict:
    data = ctx.get("dashboard_data")
    if data is None:
        raise RuntimeError("Dashboard data is unavailable")
    return data


@status_bp.route("/health")
def health_check():
    ctx = _ctx()
    version = (
        ctx.get("version_label")
        or "ULTIMATE_AI_TRADER_V4.0_CRT_COMPREHENSIVE_PERSISTENCE"
    )

    # Check Binance API latency
    binance_status = "error"
    binance_latency_ms = None
    binance_testnet_status = "error"
    binance_testnet_latency_ms = None

    try:
        # Check mainnet API
        start_time = time.time()
        response = requests.get("https://api.binance.com/api/v3/time", timeout=5)
        if response.status_code == 200:
            binance_status = "ok"
            binance_latency_ms = round((time.time() - start_time) * 1000, 2)
    except Exception:
        pass

    try:
        # Check testnet API
        start_time = time.time()
        response = requests.get("https://testnet.binance.vision/api/v3/time", timeout=5)
        if response.status_code == 200:
            binance_testnet_status = "ok"
            binance_testnet_latency_ms = round((time.time() - start_time) * 1000, 2)
    except Exception:
        pass

    # Check database connection pool status
    db_status = "error"
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "ok"
    except Exception:
        pass

    # Check background worker heartbeat
    worker_status = "ok" if _background_task_manager is not None else "error"

    # Check available disk space
    disk_status = "error"
    disk_free_gb = None
    try:
        total, used, free = shutil.disk_usage("/")
        disk_free_gb = round(free / (1024**3), 2)
        disk_status = "ok" if free > 1024**3 else "low"  # Low if less than 1GB
    except Exception:
        pass

    # Check memory usage
    memory_status = "ok"
    memory_usage_percent = None
    try:
        import psutil

        memory = psutil.virtual_memory()
        memory_usage_percent = round(memory.percent, 1)
        memory_status = "high" if memory.percent > 90 else "ok"
    except ImportError:
        memory_status = "unknown"
    except Exception:
        memory_status = "error"

    # Check CPU usage
    cpu_status = "ok"
    cpu_usage_percent = None
    try:
        import psutil

        cpu_usage_percent = round(psutil.cpu_percent(interval=1), 1)
        cpu_status = "high" if cpu_usage_percent > 95 else "ok"
    except ImportError:
        cpu_status = "unknown"
    except Exception:
        cpu_status = "error"

    # Determine overall status
    checks = [
        binance_status,
        db_status,
        worker_status,
        disk_status,
        memory_status,
        cpu_status,
    ]
    overall_status = (
        "healthy"
        if all(status in ("ok", "unknown") for status in checks)
        else "unhealthy"
    )

    return jsonify(
        {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": version,
            "checks": {
                "binance_api": {
                    "status": binance_status,
                    "latency_ms": binance_latency_ms,
                },
                "binance_testnet_api": {
                    "status": binance_testnet_status,
                    "latency_ms": binance_testnet_latency_ms,
                },
                "database": {
                    "status": db_status,
                },
                "background_worker": {
                    "status": worker_status,
                },
                "disk_space": {
                    "status": disk_status,
                    "free_gb": disk_free_gb,
                },
                "memory": {
                    "status": memory_status,
                    "usage_percent": memory_usage_percent,
                },
                "cpu": {
                    "status": cpu_status,
                    "usage_percent": cpu_usage_percent,
                },
            },
        }
    )


@status_bp.route("/api/health", methods=["GET"])
def api_health_dashboard():
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)
    health_lock = ctx.get("health_data_lock")
    if health_lock is None:
        raise RuntimeError("Health data lock unavailable")

    with health_lock:
        payload = deepcopy(dashboard_data.get("health_report", {}))
    return jsonify(payload)


# RIBS Optimization Routes
@status_bp.route("/api/ribs/status", methods=["GET"])
def ribs_status():
    """Get RIBS optimization status"""
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)

    ribs_data = dashboard_data.get("ribs_optimization", {})
    return jsonify(
        {
            "enabled": ctx.get("ribs_enabled", False),
            "status": "active" if ribs_data else "inactive",
            "data": ribs_data,
        }
    )


@status_bp.route("/api/ribs/start", methods=["POST"])
def start_ribs_optimization():
    """Start RIBS optimization"""
    ctx = _ctx()
    self_improvement_worker = ctx.get("self_improvement_worker")

    if not self_improvement_worker or not self_improvement_worker.ribs_enabled:
        return (
            jsonify({"success": False, "error": "RIBS optimization not available"}),
            400,
        )

    try:
        # Start RIBS optimization in background thread
        import threading

        ribs_thread = threading.Thread(
            target=self_improvement_worker.continuous_ribs_optimization, daemon=True
        )
        ribs_thread.start()

        return jsonify({"success": True, "message": "RIBS optimization started"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/api/ribs/pause", methods=["POST"])
def pause_ribs_optimization():
    """Pause RIBS optimization"""
    ctx = _ctx()
    self_improvement_worker = ctx.get("self_improvement_worker")

    if not self_improvement_worker:
        return (
            jsonify(
                {"success": False, "error": "Self-improvement worker not available"}
            ),
            400,
        )

    try:
        # Set stop event to pause optimization
        if hasattr(self_improvement_worker, "_stop_event"):
            self_improvement_worker._stop_event.set()

        return jsonify({"success": True, "message": "RIBS optimization paused"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/api/ribs/reset", methods=["POST"])
def reset_ribs_archive():
    """Reset RIBS archive"""
    ctx = _ctx()
    self_improvement_worker = ctx.get("self_improvement_worker")

    if not self_improvement_worker or not self_improvement_worker.ribs_optimizer:
        return jsonify({"success": False, "error": "RIBS optimizer not available"}), 400

    try:
        # Reset the RIBS optimizer
        self_improvement_worker.ribs_optimizer = None
        # Reinitialize
        from app.services.ribs_optimizer import TradingRIBSOptimizer

        self_improvement_worker.ribs_optimizer = TradingRIBSOptimizer()

        return jsonify({"success": True, "message": "RIBS archive reset"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/api/ribs/deploy/<strategy_id>", methods=["POST"])
def deploy_ribs_strategy(strategy_id):
    """Deploy a RIBS-generated strategy"""
    ctx = _ctx()
    self_improvement_worker = ctx.get("self_improvement_worker")

    if not self_improvement_worker or not self_improvement_worker.ribs_optimizer:
        return jsonify({"success": False, "error": "RIBS optimizer not available"}), 400

    try:
        # Find the strategy in elite strategies
        elite_strategies = self_improvement_worker.ribs_optimizer.get_elite_strategies()
        strategy = next((s for s in elite_strategies if s["id"] == strategy_id), None)

        if not strategy:
            return jsonify({"success": False, "error": "Strategy not found"}), 404

        # Deploy the strategy
        solution = strategy["solution"]
        self_improvement_worker.deploy_strategy(solution, strategy_id)

        return jsonify({"success": True, "message": f"Strategy {strategy_id} deployed"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/api/ribs/export/<strategy_id>", methods=["GET"])
def export_ribs_strategy(strategy_id):
    """Export RIBS strategy parameters"""
    ctx = _ctx()
    self_improvement_worker = ctx.get("self_improvement_worker")

    if not self_improvement_worker or not self_improvement_worker.ribs_optimizer:
        return jsonify({"success": False, "error": "RIBS optimizer not available"}), 400

    try:
        # Find the strategy
        elite_strategies = self_improvement_worker.ribs_optimizer.get_elite_strategies()
        strategy = next((s for s in elite_strategies if s["id"] == strategy_id), None)

        if not strategy:
            return jsonify({"success": False, "error": "Strategy not found"}), 404

        # Return strategy parameters as JSON
        from flask import Response
        import json

        strategy_data = {
            "strategy_id": strategy_id,
            "params": strategy["params"],
            "objective": strategy["objective"],
            "behavior": strategy["behavior"],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        return Response(
            json.dumps(strategy_data, indent=2),
            mimetype="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=ribs_strategy_{strategy_id}.json"
            },
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/api/ribs/export", methods=["GET"])
def export_ribs_archive():
    """Export entire RIBS archive data"""
    ctx = _ctx()
    self_improvement_worker = ctx.get("self_improvement_worker")

    if not self_improvement_worker or not self_improvement_worker.ribs_optimizer:
        return jsonify({"success": False, "error": "RIBS optimizer not available"}), 400

    try:
        # Get archive data
        archive_stats = self_improvement_worker.ribs_optimizer.get_archive_stats()
        elite_strategies = self_improvement_worker.ribs_optimizer.get_elite_strategies(
            top_n=20
        )

        archive_data = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "archive_stats": archive_stats,
            "elite_strategies": elite_strategies,
            "ribs_config": {
                "solution_dim": self_improvement_worker.ribs_optimizer.config.get(
                    "solution_dim", 10
                ),
                "archive_dimensions": self_improvement_worker.ribs_optimizer.config.get(
                    "archive_dimensions", [20, 20, 15]
                ),
                "num_emitters": self_improvement_worker.ribs_optimizer.config.get(
                    "num_emitters", 6
                ),
            },
        }

        # Return as downloadable JSON
        from flask import Response
        import json

        return Response(
            json.dumps(archive_data, indent=2),
            mimetype="application/json",
            headers={
                "Content-Disposition": "attachment; filename=ribs_archive_data.json"
            },
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")
