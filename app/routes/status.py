"""Status and health endpoints."""
from __future__ import annotations

import shutil
import time
from copy import deepcopy
from datetime import datetime, timezone

import requests
from flask import Blueprint, current_app, jsonify, Response, render_template
from flask_login import login_required
import os
import json
from prometheus_client import generate_latest

from app.extensions import db


status_bp = Blueprint("status", __name__)


def _ctx() -> dict:
    ctx = current_app.extensions.get("ai_bot_context")
    if not ctx:
        # Return empty context for test mode or when not initialized
        return {}
    return ctx


def _dashboard_data(ctx: dict) -> dict:
    data = ctx.get("dashboard_data")
    if data is None:
        raise RuntimeError("Dashboard data is unavailable")
    return data


@status_bp.route("/health")
def health_check():
    # In test mode, AI bot context may not be initialized
    try:
        ctx = _ctx()
        version = (
            ctx.get("version_label")
            or "ULTIMATE_AI_TRADER_V4.0_CRT_COMPREHENSIVE_PERSISTENCE"
        )
    except RuntimeError:
        # Test mode or context not initialized
        ctx = None
        version = "TEST_MODE_AI_TRADER_V4.0"

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

    # Check background worker heartbeat with more detail
    try:
        # Import the manager module at runtime to pick up dynamic updates in tests/ops
        from app.tasks import manager as task_manager

        if getattr(task_manager, "_background_task_manager", None) is None:
            worker_status = "uninitialized"
        else:
            worker = task_manager.get_self_improvement_worker()
            if worker is None:
                worker_status = "missing"
            else:
                # Prefer explicit running flag if available
                running = getattr(worker, "is_running", None)
                if callable(running):
                    running = running()
                worker_status = "ok" if running else "stopped"
    except Exception as exc:
        # Log the exception for diagnostics and include a short marker in the response
        try:
            current_app.logger.exception("Background worker health probe failed")
        except Exception:
            pass
        worker_status = f"error:{type(exc).__name__}"

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
    try:
        ctx = _ctx()
        service_runtime = ctx.get("service_runtime")
        self_improvement_worker = (
            service_runtime.self_improvement_worker if service_runtime else None
        )
        dashboard_data = _dashboard_data(ctx)
        ribs_data = dashboard_data.get("ribs_optimization", {})
        return jsonify(
            {
                "enabled": self_improvement_worker.ribs_enabled
                if self_improvement_worker
                else False,
                "status": "active" if ribs_data else "inactive",
                "data": ribs_data,
            }
        )
    except RuntimeError:
        # Test mode or context not initialized
        return jsonify(
            {
                "enabled": False,
                "status": "inactive",
                "data": {},
                "message": "RIBS not available in test mode",
            }
        )


@status_bp.route("/api/ribs/archive/status", methods=["GET"])
def ribs_archive_status():
    """Return basic RIBS optimizer status for debugging and dashboard"""
    try:
        # Be forgiving when ai_bot_context is not present (tests often only
        # create a status file on disk rather than registering a full runtime).
        ctx = current_app.extensions.get("ai_bot_context", {}) or {}
        # Support either a directly-registered worker or a service_runtime wrapper
        worker = ctx.get("self_improvement_worker") or (
            getattr(ctx.get("service_runtime"), "self_improvement_worker", None)
            if ctx.get("service_runtime")
            else None
        )

        # If worker and optimizer accessible in this process, report live stats
        if worker and getattr(worker, "ribs_optimizer", None):
            optimizer = worker.ribs_optimizer
            # Get archive stats defensively (optimizer implementations used in
            # tests may raise or return non-serializable values).
            try:
                stats = optimizer.get_archive_stats() or {}
            except Exception as e:
                stats = {}
                # capture the error in the returned status so tests / monitors can see
                stats_error = str(e)
            else:
                stats_error = None

            # Check latest checkpoint file timestamp if any (use getattr to avoid
            # AttributeError when a fake optimizer does not have checkpoints_dir)
            cp_dir = getattr(
                optimizer,
                "checkpoints_dir",
                os.path.join("bot_persistence", "ribs_checkpoints"),
            )
            latest = None
            try:
                files = [os.path.join(cp_dir, f) for f in os.listdir(cp_dir)]
                files = [f for f in files if f.endswith(".pkl")]
                if files:
                    latest_file = max(files, key=os.path.getmtime)
                    latest = {
                        "path": latest_file,
                        "mtime": os.path.getmtime(latest_file),
                        "size": os.path.getsize(latest_file),
                    }
            except Exception:
                latest = None

            response = {
                "available": True,
                "archive_stats": stats,
                "latest_checkpoint": latest,
            }
            if stats_error:
                response["status_error"] = stats_error
            return jsonify(response)

        # Fallback: try reading a cross-process status file (useful when the worker lives in another process)
        status_path = os.path.join(
            "bot_persistence", "ribs_checkpoints", "ribs_status.json"
        )
        if os.path.exists(status_path):
            try:
                with open(status_path, "r") as sf:
                    status = json.load(sf)
                return jsonify({"available": True, "status_file": status})
            except Exception as e:
                return (
                    jsonify(
                        {
                            "available": False,
                            "error": f"Failed to read status file: {e}",
                        }
                    ),
                    500,
                )

        return jsonify(
            {"available": False, "message": "RIBS not enabled and no status file found"}
        )
    except Exception as e:
        return jsonify({"available": False, "error": str(e)}), 500


@status_bp.route("/api/health/ribs", methods=["GET"])
def api_health_ribs():
    """Return a lightweight health status for RIBS based on ribs_status.json"""
    status_path = os.path.join(
        "bot_persistence", "ribs_checkpoints", "ribs_status.json"
    )
    if not os.path.exists(status_path):
        return (
            jsonify({"status": "missing", "message": "RIBS status file not found"}),
            404,
        )

    try:
        with open(status_path, "r") as sf:
            status = json.load(sf)

        latest = status.get("latest_checkpoint") or {}
        mtime = latest.get("mtime")
        age = None
        if mtime:
            age = int(time.time() - float(mtime))

        return jsonify(
            {
                "status": "ok",
                "status_file": status,
                "latest_checkpoint_age_seconds": age,
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@status_bp.route("/api/ribs/progress", methods=["GET"])
def api_ribs_progress():
    """Return lightweight RIBS progress information read from ribs_status.json"""
    status_path = os.path.join(
        "bot_persistence", "ribs_checkpoints", "ribs_status.json"
    )
    if not os.path.exists(status_path):
        return (
            jsonify({"status": "missing", "message": "RIBS status file not found"}),
            404,
        )

    try:
        with open(status_path, "r") as sf:
            status = json.load(sf)

            # Provide a minimal progress view
            # Compute checkpoint age (seconds) for frontend
            latest = status.get("latest_checkpoint") or {}
            mtime = latest.get("mtime")
            age = None
            try:
                if mtime is not None:
                    age = int(time.time() - float(mtime))
            except Exception:
                age = None

            # Provide a minimal progress view including health
            progress = {
                "running": status.get("running", False),
                "current_iteration": status.get("current_iteration"),
                "progress_percent": status.get("progress_percent"),
                "archive_stats": status.get("archive_stats", {}),
                "latest_checkpoint": latest,
                "latest_checkpoint_age_seconds": age,
                "healthy": (age is not None and age <= 3600),
            }
        return jsonify(progress)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@status_bp.route("/api/ribs/start", methods=["POST"])
def start_ribs_optimization():
    """Start RIBS optimization"""
    ctx = _ctx()
    service_runtime = ctx.get("service_runtime")
    self_improvement_worker = (
        service_runtime.self_improvement_worker if service_runtime else None
    )

    if not self_improvement_worker or not self_improvement_worker.ribs_enabled:
        return (
            jsonify({"success": False, "error": "RIBS optimization not available"}),
            400,
        )

    try:
        started = False
        # Prefer the worker's managed start method if available
        starter = getattr(self_improvement_worker, "start_ribs_optimization", None)
        if callable(starter):
            started = starter()
        else:
            # Fallback: spawn a thread (legacy behavior)
            import threading

            ribs_thread = threading.Thread(
                target=self_improvement_worker.continuous_ribs_optimization, daemon=True
            )
            ribs_thread.start()
            started = True

        if started:
            return jsonify({"success": True, "message": "RIBS optimization started"})
        return (
            jsonify({"success": False, "error": "RIBS already running or unavailable"}),
            400,
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/api/ribs/pause", methods=["POST"])
def pause_ribs_optimization():
    """Pause/stop the running RIBS optimization loop."""
    ctx = _ctx()
    service_runtime = ctx.get("service_runtime")
    self_improvement_worker = (
        service_runtime.self_improvement_worker if service_runtime else None
    )

    if not self_improvement_worker or not self_improvement_worker.ribs_enabled:
        return (
            jsonify({"success": False, "error": "RIBS optimization not available"}),
            400,
        )

    try:
        stopper = getattr(self_improvement_worker, "stop_ribs_optimization", None)
        stopped = False
        if callable(stopper):
            stopped = stopper()
        else:
            # Fallback: use generic stop which stops entire worker
            self_improvement_worker.stop()
            stopped = True

        if stopped:
            return jsonify({"success": True, "message": "RIBS optimization paused"})
        return jsonify({"success": False, "error": "RIBS not running"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/ribs/analyze/<strategy_id>", methods=["GET"])
@login_required
def ribs_analyze(strategy_id):
    """Render an analysis page for a RIBS elite strategy (admin-only view)."""
    ctx = _ctx()
    service_runtime = ctx.get("service_runtime")
    self_improvement_worker = (
        service_runtime.self_improvement_worker if service_runtime else None
    )

    # Try to locate strategy from live optimizer if available
    strategy = None
    backtest_result = None

    if self_improvement_worker and self_improvement_worker.ribs_optimizer:
        elites = self_improvement_worker.ribs_optimizer.get_elite_strategies(10)
        strategy = next((s for s in elites if s["id"] == strategy_id), None)

        # Run a light-weight backtest using recent data if available
        try:
            market_data = self_improvement_worker.load_recent_data()
            backtest_result = (
                self_improvement_worker.ribs_optimizer.run_backtest(
                    strategy["params"], market_data
                )
                if strategy
                else None
            )
        except Exception:
            backtest_result = None

    # Fallback: check status file for archived elite strategies
    if not strategy:
        status_path = os.path.join(
            "bot_persistence", "ribs_checkpoints", "ribs_status.json"
        )
        try:
            if os.path.exists(status_path):
                with open(status_path, "r") as sf:
                    status = json.load(sf) or {}
                for s in status.get("elite_strategies", []):
                    if s.get("id") == strategy_id:
                        strategy = s
                        break
        except Exception:
            strategy = strategy or None

    if not strategy:
        return (
            jsonify({"success": False, "error": "Strategy not found"}),
            404,
        )

    # Render a simple analyze page with params and backtest summary
    return render_template(
        "ribs_analyze.html",
        strategy=strategy,
        backtest=backtest_result,
        strategy_id=strategy_id,
    )


@status_bp.route("/api/ribs/reset", methods=["POST"])
def reset_ribs_archive():
    """Reset RIBS archive"""
    ctx = _ctx()
    service_runtime = ctx.get("service_runtime")
    self_improvement_worker = (
        service_runtime.self_improvement_worker if service_runtime else None
    )

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
    service_runtime = ctx.get("service_runtime")
    self_improvement_worker = (
        service_runtime.self_improvement_worker if service_runtime else None
    )

    if not self_improvement_worker or not self_improvement_worker.ribs_optimizer:
        return jsonify({"success": False, "error": "RIBS optimizer not available"}), 400

    try:
        # Find the strategy in elite strategies
        elite_strategies = self_improvement_worker.ribs_optimizer.get_elite_strategies()
        strategy = next((s for s in elite_strategies if s["id"] == strategy_id), None)

        if not strategy:
            return jsonify({"success": False, "error": "Strategy not found"}), 404

        # Deploy the strategy (with gating)
        solution = strategy["solution"]
        res = self_improvement_worker.deploy_strategy(solution, strategy_id)
        if isinstance(res, dict):
            if not res.get("success"):
                return jsonify({"success": False, "error": res.get("message")}), 400
            return jsonify({"success": True, "message": res.get("message")})

        # Back-compat: if deploy_strategy didn't return a dict, assume success
        return jsonify({"success": True, "message": f"Strategy {strategy_id} deployed"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/api/ribs/export/<strategy_id>", methods=["GET"])
def export_ribs_strategy(strategy_id):
    """Export RIBS strategy parameters"""
    ctx = _ctx()
    service_runtime = ctx.get("service_runtime")
    self_improvement_worker = (
        service_runtime.self_improvement_worker if service_runtime else None
    )

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
    if not ctx:
        return (
            jsonify({"success": False, "error": "AI bot context not initialized"}),
            503,
        )

    service_runtime = ctx.get("service_runtime")
    self_improvement_worker = (
        service_runtime.self_improvement_worker if service_runtime else None
    )

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


@status_bp.route("/performance/metrics")
def performance_metrics():
    """Get real-time performance metrics"""
    try:
        from ai_ml_auto_bot_final import performance_monitor

        metrics = performance_monitor.get_metrics()
        return jsonify({"success": True, "metrics": metrics})
    except Exception as e:
        current_app.logger.error(f"Failed to get performance metrics: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@status_bp.route("/api/system-metrics")
def api_system_metrics():
    """API endpoint for system metrics."""
    try:
        # Return dummy data for now
        return jsonify({
            "system": {
                "cpu_percent": 45.2,
                "memory_used_gb": 2.1,
                "memory_percent": 52.3
            },
            "trading": {
                "active_positions": 2,
                "total_trades": 156,
                "win_rate": 0.68
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f"Failed to get system metrics: {e}")
        return jsonify({"error": str(e)}), 500


@status_bp.route("/api/alerts")
def api_alerts():
    """API endpoint for alerts."""
    try:
        return jsonify({
            "alerts": [],
            "summary": {"total": 0, "critical": 0, "warning": 0}
        })
    except Exception as e:
        current_app.logger.error(f"Failed to get alerts: {e}")
        return jsonify({"error": str(e)}), 500


@status_bp.route("/api/resource-recommendations")
def api_resource_recommendations():
    """API endpoint for resource recommendations."""
    try:
        return jsonify({
            "recommendations": []
        })
    except Exception as e:
        current_app.logger.error(f"Failed to get resource recommendations: {e}")
        return jsonify({"error": str(e)}), 500


@status_bp.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")
