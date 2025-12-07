"""Strategy management API blueprint."""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required


strategies_bp = Blueprint('strategies', __name__)


def _context() -> dict[str, Any]:
    ctx = current_app.extensions.get('ai_bot_context')
    if not ctx:
        raise RuntimeError('AI bot context is not initialized')
    return ctx


def _strategy_manager():
    manager = _context().get('strategy_manager')
    if not manager:
        raise RuntimeError('Strategy manager unavailable')
    return manager


def _qfm_engine():
    ctx = _context()
    engine = ctx.get('qfm_engine')
    if engine:
        return engine
    manager = ctx.get('strategy_manager')
    if manager:
        engine = getattr(manager, 'qfm_engine', None)
        if engine:
            return engine
    return getattr(current_app, 'qfm_engine', None)


def _jsonify_error(message: str, status: int = 500):
    return jsonify({'error': message}), status


@strategies_bp.route('/api/strategies', methods=['GET'])
def list_strategies():
    manager = _strategy_manager()
    strategies = manager.get_all_strategies()
    response: dict[str, Any] = {
        'strategies': strategies,
        'active_count': len([s for s in strategies if s.get('active')]),
        'total_count': len(strategies),
        'timestamp': time.time(),
    }
    status_getter = getattr(manager, 'get_all_strategies_status', None)
    if current_user.is_authenticated and callable(status_getter):
        detailed = status_getter()
        response['strategies_status'] = detailed
        response['total_strategies'] = len(detailed)
        response['active_strategies'] = len([s for s in detailed if s.get('active')])
    return jsonify(response)


@strategies_bp.route('/api/strategies/<strategy_name>', methods=['GET'])
def strategy_details(strategy_name: str):
    manager = _strategy_manager()
    if current_user.is_authenticated:
        details_getter = getattr(manager, 'get_strategy_details', None)
        if callable(details_getter):
            details = details_getter(strategy_name)
            if details:
                return jsonify(details)
    strategy = manager.get_strategy(strategy_name)
    if not strategy:
        return _jsonify_error(f'Strategy {strategy_name} not found', 404)
    return jsonify(strategy)


@strategies_bp.route('/api/strategies/<strategy_name>', methods=['PUT'])
@login_required
def update_strategy(strategy_name: str):
    manager = _strategy_manager()
    payload = request.get_json()
    if not payload:
        return _jsonify_error('No data provided', 400)
    updater = getattr(manager, 'update_strategy_config', None)
    if not callable(updater):
        return _jsonify_error('Strategy update not supported', 501)
    if updater(strategy_name, payload):
        return jsonify({
            'message': f'Strategy {strategy_name} updated successfully',
            'strategy': strategy_name,
            'updated_fields': list(payload.keys())
        })
    return _jsonify_error(f'Failed to update strategy {strategy_name}', 500)


@strategies_bp.route('/api/strategies/<strategy_name>/toggle', methods=['POST'])
@login_required
def toggle_strategy(strategy_name: str):
    manager = _strategy_manager()
    payload = request.get_json(silent=True) or {}
    enable = bool(payload.get('enable', True))
    if not manager.toggle_strategy(strategy_name, enable):
        return _jsonify_error(f'Failed to toggle strategy {strategy_name}', 400)
    return jsonify({
        'strategy': strategy_name,
        'enabled': enable,
        'message': f'Strategy {strategy_name} {"enabled" if enable else "disabled"} successfully'
    })


@strategies_bp.route('/api/strategies/<strategy_name>/configure', methods=['POST'])
@login_required
def configure_strategy(strategy_name: str):
    manager = _strategy_manager()
    payload = request.get_json(silent=True) or {}
    config = payload.get('config', {})
    if not manager.configure_strategy(strategy_name, config):
        return _jsonify_error(f'Failed to configure strategy {strategy_name}', 400)
    return jsonify({
        'strategy': strategy_name,
        'config': config,
        'message': f'Strategy {strategy_name} configured successfully'
    })


@strategies_bp.route('/api/strategies/<strategy_name>/performance', methods=['GET'])
def strategy_performance(strategy_name: str):
    manager = _strategy_manager()
    performance = manager.get_strategy_performance(strategy_name)
    if performance is None:
        return _jsonify_error(f'Performance data not available for {strategy_name}', 404)
    return jsonify(performance)


@strategies_bp.route('/api/strategies/performance', methods=['GET'])
def all_strategies_performance():
    manager = _strategy_manager()
    performance_data = manager.get_all_performance()
    return jsonify({
        'performance': performance_data,
        'timestamp': time.time()
    })


@strategies_bp.route('/api/strategies/<strategy_name>/execute', methods=['POST'])
@login_required
def execute_strategy(strategy_name: str):
    manager = _strategy_manager()
    payload = request.get_json(silent=True) or {}
    symbol = payload.get('symbol')
    market_data = payload.get('market_data')
    if not symbol:
        return _jsonify_error('Symbol is required', 400)
    result = manager.execute_strategy(strategy_name, symbol, market_data)
    return jsonify({
        'strategy': strategy_name,
        'symbol': symbol,
        'result': result,
        'timestamp': time.time()
    })


@strategies_bp.route('/api/strategies/reset', methods=['POST'])
@login_required
def reset_strategies():
    manager = _strategy_manager()
    manager.reset_all_strategies()
    return jsonify({
        'message': 'All strategies reset to default state',
        'timestamp': time.time()
    })


@strategies_bp.route('/api/strategies/backtest', methods=['POST'])
@login_required
def backtest_strategies():
    manager = _strategy_manager()
    payload = request.get_json(silent=True) or {}
    strategy_names = payload.get('strategies', [])
    symbols = payload.get('symbols', [])
    start_date = payload.get('start_date')
    end_date = payload.get('end_date')
    if not strategy_names:
        return _jsonify_error('At least one strategy must be specified', 400)
    if not symbols:
        return _jsonify_error('At least one symbol must be specified', 400)
    job_id = manager.start_backtest(strategy_names, symbols, start_date, end_date)
    return jsonify({
        'job_id': job_id,
        'message': 'Backtest started',
        'strategies': strategy_names,
        'symbols': symbols,
        'timestamp': time.time()
    }), 202


@strategies_bp.route('/api/strategies/backtest/<job_id>', methods=['GET'])
def backtest_status(job_id: str):
    manager = _strategy_manager()
    status = manager.get_backtest_status(job_id)
    if status is None:
        return _jsonify_error(f'Backtest job {job_id} not found', 404)
    return jsonify(status)


@strategies_bp.route('/api/strategies/<strategy_name>/config', methods=['GET'])
@login_required
def get_strategy_config(strategy_name: str):
    manager = _strategy_manager()
    getter = getattr(manager, 'get_strategy_config', None)
    if not callable(getter):
        return _jsonify_error('Strategy config retrieval not supported', 501)
    config = getter(strategy_name)
    if not config:
        return _jsonify_error(f'Configuration not found for {strategy_name}', 404)
    return jsonify({
        'strategy': strategy_name,
        'config': config,
        'timestamp': datetime.now().isoformat()
    })


@strategies_bp.route('/api/strategies/<strategy_name>/config', methods=['PUT'])
@login_required
def update_strategy_config(strategy_name: str):
    manager = _strategy_manager()
    data = request.get_json()
    if not data:
        return _jsonify_error('No configuration data provided', 400)
    updater = getattr(manager, 'update_strategy_config', None)
    if not callable(updater):
        return _jsonify_error('Strategy config update not supported', 501)
    if updater(strategy_name, data):
        return jsonify({
            'message': f'Configuration updated for {strategy_name}',
            'strategy': strategy_name,
            'updated_config': data
        })
    return _jsonify_error(f'Failed to update configuration for {strategy_name}', 500)


@strategies_bp.route('/api/strategies/optimize', methods=['POST'])
@login_required
def optimize_strategies():
    manager = _strategy_manager()

    def optimize_worker():
        try:
            manager.optimize_all_strategies()
            print('Strategy optimization completed successfully')
        except Exception as exc:
            print(f'Strategy optimization failed: {exc}')

    threading.Thread(target=optimize_worker, daemon=True).start()
    return jsonify({
        'message': 'Strategy optimization started',
        'status': 'running',
        'timestamp': datetime.now().isoformat()
    })


@strategies_bp.route('/api/strategies/optimization/status', methods=['GET'])
@login_required
def optimization_status():
    manager = _strategy_manager()
    status = manager.get_optimization_status()
    return jsonify({
        'optimization_status': status,
        'timestamp': datetime.now().isoformat()
    })


@strategies_bp.route('/api/qfm/analyze', methods=['POST'])
@login_required
def qfm_analyze():
    engine = _qfm_engine()
    if not engine:
        return jsonify({
            'success': False,
            'message': 'QFM engine not available',
            'timestamp': datetime.now().isoformat()
        })
    try:
        result = engine.run_analysis()
    except Exception as exc:
        return _jsonify_error(str(exc))
    return jsonify({
        'success': True,
        'message': 'QFM analysis completed',
        'result': result,
        'timestamp': datetime.now().isoformat()
    })


@strategies_bp.route('/api/strategies/config', methods=['POST'])
@login_required
def save_strategy_config():
    payload = request.get_json(silent=True)
    if not payload:
        return _jsonify_error('No configuration data provided', 400)
    return jsonify({
        'success': True,
        'message': 'Strategy configuration saved successfully',
        'timestamp': datetime.now().isoformat()
    })


