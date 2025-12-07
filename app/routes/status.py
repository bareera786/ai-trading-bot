"""Status and health endpoints."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify


status_bp = Blueprint('status', __name__)


def _ctx() -> dict:
    ctx = current_app.extensions.get('ai_bot_context')
    if not ctx:
        raise RuntimeError('AI bot context is not initialized')
    return ctx


def _dashboard_data(ctx: dict) -> dict:
    data = ctx.get('dashboard_data')
    if data is None:
        raise RuntimeError('Dashboard data is unavailable')
    return data


@status_bp.route('/health')
def health_check():
    ctx = _ctx()
    version = ctx.get('version_label') or 'ULTIMATE_AI_TRADER_V4.0_CRT_COMPREHENSIVE_PERSISTENCE'
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': version,
    })


@status_bp.route('/api/health', methods=['GET'])
def api_health_dashboard():
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)
    health_lock = ctx.get('health_data_lock')
    if health_lock is None:
        raise RuntimeError('Health data lock unavailable')

    with health_lock:
        payload = deepcopy(dashboard_data.get('health_report', {}))
    return jsonify(payload)
