"""Realtime polling fallback endpoints blueprint."""
from __future__ import annotations

import random
import time
from typing import Any

from flask import Blueprint, current_app, jsonify, session
from flask_login import login_required


realtime_bp = Blueprint('realtime', __name__)


def _context() -> dict[str, Any]:
    ctx = current_app.extensions.get('ai_bot_context')
    if not ctx:
        raise RuntimeError('AI bot context is not initialized')
    return ctx


def _dashboard_data(ctx: dict[str, Any]) -> dict[str, Any]:
    data = ctx.get('dashboard_data')
    if data is None:
        raise RuntimeError('Dashboard data is unavailable')
    return data


def _get_user_portfolio(ctx: dict[str, Any], user_id: Any) -> dict[str, Any]:
    getter = ctx.get('get_user_portfolio_data')
    if callable(getter) and user_id:
        return getter(user_id) or {}
    return {}


def _get_active_universe(ctx: dict[str, Any]) -> list[str]:
    active_fn = ctx.get('get_active_trading_universe')
    if callable(active_fn):
        result = active_fn()
        if isinstance(result, list):
            return result
        if hasattr(result, '__iter__'):
            return list(result)
    return []


def _top_default_symbols() -> list[str]:
    return [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
        'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LTCUSDT'
    ]


@realtime_bp.route('/api/realtime/portfolio')
@login_required
def realtime_portfolio():
    ctx = _context()
    dashboard_data = _dashboard_data(ctx)
    try:
        user_id = session.get('user_id')
        if user_id:
            portfolio_data = _get_user_portfolio(ctx, user_id)
        else:
            portfolio_data = dashboard_data.get('portfolio', {})

        return jsonify({
            'success': True,
            'data': portfolio_data,
            'timestamp': time.time()
        })
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({
            'success': False,
            'error': str(exc),
            'timestamp': time.time()
        }), 500


@realtime_bp.route('/api/realtime/pnl')
@login_required
def realtime_pnl():
    ctx = _context()
    dashboard_data = _dashboard_data(ctx)
    try:
        portfolio = dashboard_data.get('portfolio', {})
        pnl_data = {
            'total_pnl': portfolio.get('total_pnl', 0),
            'daily_pnl': portfolio.get('daily_pnl', 0),
            'open_positions_pnl': sum(pos.get('pnl', 0) for pos in portfolio.get('positions', [])),
            'timestamp': time.time()
        }
        return jsonify({
            'success': True,
            'data': pnl_data,
            'timestamp': time.time()
        })
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({
            'success': False,
            'error': str(exc),
            'timestamp': time.time()
        }), 500


@realtime_bp.route('/api/realtime/performance')
@login_required
def realtime_performance():
    ctx = _context()
    dashboard_data = _dashboard_data(ctx)
    try:
        performance_data = dashboard_data.get('performance', {})
        return jsonify({
            'success': True,
            'data': performance_data,
            'timestamp': time.time()
        })
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({
            'success': False,
            'error': str(exc),
            'timestamp': time.time()
        }), 500


@realtime_bp.route('/api/realtime/market_data')
def realtime_market_data():
    ctx = _context()
    dashboard_data = _dashboard_data(ctx)
    try:
        active_symbols = _get_active_universe(ctx)
        if not active_symbols:
            active_symbols = _top_default_symbols()

        market_data = {}
        available = dashboard_data.get('market_data', {})
        for symbol in active_symbols[:20]:
            if symbol in available:
                market_data[symbol] = available[symbol]
            else:
                base_prices = {
                    'BTCUSDT': 45000, 'ETHUSDT': 2450, 'BNBUSDT': 245, 'ADAUSDT': 0.45,
                    'XRPUSDT': 0.55, 'SOLUSDT': 95, 'DOTUSDT': 6.8, 'DOGEUSDT': 0.08,
                    'AVAXUSDT': 35, 'LTCUSDT': 68
                }
                base_price = base_prices.get(symbol, 100)
                price_change = random.uniform(-5, 5)
                current_price = base_price * (1 + price_change / 100)

                market_data[symbol] = {
                    'price': current_price,
                    'price_change_24h': price_change,
                    'volume_24h': random.randint(1_000_000, 100_000_000),
                    'symbol': symbol
                }

        return jsonify({
            'success': True,
            'data': market_data,
            'timestamp': time.time()
        })
    except Exception as exc:  # pragma: no cover - defensive
        return jsonify({
            'success': False,
            'error': str(exc),
            'timestamp': time.time()
        }), 500
