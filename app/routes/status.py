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
    try:
        start_time = time.time()
        response = requests.get("https://api.binance.com/api/v3/time", timeout=5)
        if response.status_code == 200:
            binance_status = "ok"
            binance_latency_ms = round((time.time() - start_time) * 1000, 2)
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

    # Determine overall status
    checks = [binance_status, db_status, worker_status, disk_status]
    overall_status = (
        "healthy" if all(status == "ok" for status in checks) else "unhealthy"
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


@status_bp.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype="text/plain")
