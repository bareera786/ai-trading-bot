"""Analytic endpoints for journal, backtests, and market data."""
from __future__ import annotations

import time
from typing import Any, Iterable

from flask import Blueprint, current_app, jsonify, request, session
from flask_login import login_required

from app.models import UserTrade


metrics_bp = Blueprint('metrics', __name__)


def _ctx() -> dict[str, Any]:
    ctx = current_app.extensions.get('ai_bot_context')
    if not ctx:
        raise RuntimeError('AI bot context is not initialized')
    return ctx


def _dashboard_data(ctx: dict[str, Any]) -> dict[str, Any]:
    data = ctx.get('dashboard_data')
    if data is None:
        raise RuntimeError('Dashboard data is unavailable')
    return data


def _get_traders(ctx: dict[str, Any]):
    ultimate = ctx.get('ultimate_trader')
    optimized = ctx.get('optimized_trader')
    if not ultimate and not optimized:
        raise RuntimeError('Trader instances unavailable')
    return ultimate, optimized


def _callable(ctx: dict[str, Any], key: str):
    value = ctx.get(key)
    return value if callable(value) else None


def _get_backtest_manager(ctx: dict[str, Any]):
    manager = ctx.get('backtest_manager')
    if not manager:
        raise RuntimeError('Backtest manager unavailable')
    return manager


def _pick_trader(ctx: dict[str, Any], mode: str):
    ultimate, optimized = _get_traders(ctx)
    return optimized if mode == 'optimized' else ultimate


def _pearson_corr(xs: list[float], ys: list[float]) -> float:
    if not xs or not ys or len(xs) != len(ys):
        return 0.0
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 0 or var_y <= 0:
        return 0.0
    return cov / ((var_x ** 0.5) * (var_y ** 0.5))


@metrics_bp.route('/api/journal')
def api_journal():
    ctx = _ctx()
    ultimate, optimized = _get_traders(ctx)

    limit = request.args.get('limit', 50, type=int)
    event_type = request.args.get('event_type')
    symbol = request.args.get('symbol')
    search = request.args.get('search')
    mode = request.args.get('mode', 'ultimate').lower()

    def _annotated_events(trader_obj, profile: str, limit_override: int | None = None):
        if not trader_obj or not hasattr(trader_obj, 'trade_history'):
            return []
        events_raw = trader_obj.trade_history.get_journal_events(
            limit=limit_override,
            event_type=event_type,
            symbol=symbol,
            search=search,
        )
        annotated = []
        for entry in events_raw:
            entry_copy = dict(entry)
            entry_copy['_profile'] = profile
            annotated.append(entry_copy)
        return annotated

    events: list[dict[str, Any]] = []
    if mode == 'optimized':
        events = _annotated_events(optimized, 'optimized', limit)
    elif mode == 'all':
        per_limit = None if not limit or limit <= 0 else limit
        events = _annotated_events(ultimate, 'ultimate', per_limit) + _annotated_events(optimized, 'optimized', per_limit)
        events.sort(key=lambda ev: ev.get('timestamp', ''), reverse=True)
        if limit and limit > 0:
            events = events[:limit]
    else:
        events = _annotated_events(ultimate, 'ultimate', limit)

    return jsonify({
        'mode': mode,
        'events': events,
        'count': len(events),
        'limit': limit,
        'event_type': event_type,
        'symbol': symbol,
        'search': search,
    })


@metrics_bp.route('/api/journal/filters')
def api_journal_filters():
    ctx = _ctx()
    ultimate, optimized = _get_traders(ctx)
    get_universe = _callable(ctx, 'get_active_trading_universe')

    symbols = set(str(symbol).upper() for symbol in (get_universe() or [])) if get_universe else set()
    event_types = set()
    total_events = 0

    for trader in (ultimate, optimized):
        if not trader or not hasattr(trader, 'trade_history'):
            continue
        try:
            entries = trader.trade_history.get_journal_events(limit=None)
        except Exception:
            entries = []

        total_events += len(entries)
        for entry in entries:
            evt_type = entry.get('event_type')
            if evt_type:
                event_types.add(str(evt_type))
            payload = entry.get('payload') or {}
            payload_symbol = payload.get('symbol')
            if payload_symbol:
                symbols.add(str(payload_symbol).upper())

    sorted_symbols = sorted(symbols)
    sorted_events = sorted(event_types)

    return jsonify({
        'symbols': sorted_symbols,
        'event_types': sorted_events,
        'profiles': ['ultimate', 'optimized', 'all'],
        'total_events': total_events,
    })


@metrics_bp.route('/api/backtests')
def api_backtests():
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)
    ultimate_ml = ctx.get('ultimate_ml_system')
    optimized_ml = ctx.get('optimized_ml_system')

    mode = request.args.get('mode', 'all').lower()
    results = dashboard_data.get('backtest_results', {})

    if (not results) or all(not v for v in results.values()):
        try:
            results = {
                'ultimate': ultimate_ml.get_backtest_results() if ultimate_ml else {},
                'optimized': optimized_ml.get_backtest_results() if optimized_ml else {},
            }
            dashboard_data['backtest_results'] = results
        except Exception as exc:  # pragma: no cover - runtime logging
            print(f"❌ Error refreshing backtest results: {exc}")
            results = results or {}

    if mode in ['ultimate', 'optimized']:
        results = {mode: results.get(mode, {})}

    return jsonify({'mode': mode, 'results': results})


def _parse_symbol_payload(symbols: Any) -> list[str]:
    if symbols is None:
        return []
    if isinstance(symbols, str):
        sanitized = symbols.replace('\n', ' ').replace('\t', ' ').replace(',', ' ')
        return [segment for segment in sanitized.split(' ') if segment.strip()]
    if isinstance(symbols, Iterable):
        parsed: list[str] = []
        for item in symbols:
            if isinstance(item, str) and item.strip():
                parsed.append(item.strip())
        return parsed
    return []


@metrics_bp.route('/api/backtests/run', methods=['POST'])
@login_required
def api_backtests_run():
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)
    manager = _get_backtest_manager(ctx)
    payload = request.get_json(silent=True) or {}
    symbols = _parse_symbol_payload(payload.get('symbols'))
    payload['symbols'] = symbols

    job = manager.submit(payload)
    dashboard_data.setdefault('backtest_jobs', {})
    dashboard_data['backtest_jobs']['active'] = job
    dashboard_data['backtest_jobs']['history'] = manager.get_history()

    return jsonify({'job': job}), 202


@metrics_bp.route('/api/backtests/status/<job_id>')
def api_backtests_status(job_id: str):
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)
    manager = _get_backtest_manager(ctx)

    job = manager.get_job(job_id)
    if not job:
        return jsonify({'error': 'Backtest job not found'}), 404

    active_job = manager.get_active_job()
    dashboard_data['backtest_jobs']['active'] = active_job
    dashboard_data['backtest_jobs']['history'] = manager.get_history()
    return jsonify({'job': job, 'active': active_job})


@metrics_bp.route('/api/backtests/history')
def api_backtests_history():
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)
    manager = _get_backtest_manager(ctx)

    history = manager.get_history()
    active_job = manager.get_active_job()
    dashboard_data['backtest_jobs']['active'] = active_job
    dashboard_data['backtest_jobs']['history'] = history
    return jsonify({'history': history, 'active': active_job})


@metrics_bp.route('/api/market_data')
def api_market_data():
    ctx = _ctx()
    dashboard_data = _dashboard_data(ctx)
    get_universe = _callable(ctx, 'get_active_trading_universe')
    get_market_data = _callable(ctx, 'get_real_market_data')

    active = set(get_universe()) if get_universe else set()
    market_data = {}
    if get_market_data:
        for symbol in active:
            real_data = get_market_data(symbol)
            if real_data:
                market_data[symbol] = real_data

    def _filter_mapping(key: str):
        mapping = dashboard_data.get(key, {})
        if isinstance(mapping, dict):
            return {symbol: value for symbol, value in mapping.items() if symbol in active}
        return {}

    return jsonify({
        'market_data': market_data,
        'ml_predictions': _filter_mapping('ml_predictions'),
        'ai_signals': _filter_mapping('ai_signals'),
        'trending_pairs': [symbol for symbol in dashboard_data.get('trending_pairs', []) if symbol in active],
        'ensemble_predictions': _filter_mapping('ensemble_predictions'),
        'crt_signals': _filter_mapping('crt_signals'),
        'qfm_signals': _filter_mapping('qfm_signals'),
        'optimized_ml_predictions': _filter_mapping('optimized_ml_predictions'),
        'optimized_ai_signals': _filter_mapping('optimized_ai_signals'),
        'optimized_ensemble_predictions': _filter_mapping('optimized_ensemble_predictions'),
        'optimized_crt_signals': _filter_mapping('optimized_crt_signals'),
        'optimized_qfm_signals': _filter_mapping('optimized_qfm_signals'),
    })


# ...existing code...


@metrics_bp.route('/api/crt_data')
def api_crt_data():
    ctx = _ctx()
    symbol = request.args.get('symbol')
    mode = (request.args.get('mode', 'ultimate') or 'ultimate').lower()
    ultimate_ml = ctx.get('ultimate_ml_system')
    optimized_ml = ctx.get('optimized_ml_system')
    system = optimized_ml if mode == 'optimized' else ultimate_ml

    if system is None or not hasattr(system, 'get_crt_dashboard_data'):
        return jsonify({'error': f'ML system unavailable for mode {mode}'}), 503

    try:
        crt_data = system.get_crt_dashboard_data(symbol)
    except Exception as exc:  # pragma: no cover - runtime defensive logging
        print(f"Error fetching CRT data for mode {mode}: {exc}")
        return jsonify({'error': str(exc)}), 500

    return jsonify({'mode': mode, 'data': crt_data})


@metrics_bp.route('/api/trades')
def api_trades():
    ctx = _ctx()
    mode = request.args.get('mode', 'ultimate').lower()
    trader = _pick_trader(ctx, mode)
    if not trader:
        return jsonify({'error': f"Trader for mode '{mode}' is unavailable"}), 503

    page = request.args.get('page', 1, type=int)
    symbol = request.args.get('symbol')
    days = request.args.get('days', type=int)
    execution_mode = request.args.get('execution_mode')

    filters: dict[str, Any] = {}
    if symbol:
        filters['symbol'] = symbol
    if days:
        filters['days'] = days
    default_real_only = bool(getattr(trader, 'real_trading_enabled', False))
    if execution_mode:
        filters['execution_mode'] = execution_mode
    elif default_real_only:
        filters['execution_mode'] = 'real'

    try:
        trades = trader.trade_history.get_trade_history(filters)
    except Exception as exc:  # pragma: no cover - runtime defensive log
        print(f"❌ Error fetching trade history: {exc}")
        return jsonify({'error': str(exc)}), 500

    trades.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

    per_page = 20
    start_idx = (page - 1) * per_page
    paginated = trades[start_idx:start_idx + per_page]

    for trade in paginated:
        for key, value in list(trade.items()):
            if isinstance(value, float):
                trade[key] = round(value, 4)

    return jsonify({
        'trades': paginated,
        'total_trades': len(trades),
        'current_page': page,
        'total_pages': max(1, (len(trades) + per_page - 1) // per_page),
        'per_page': per_page,
        'mode': mode,
        'execution_mode': filters.get('execution_mode', 'all' if not default_real_only else 'real'),
        'real_only_default': default_real_only,
        'timestamp': time.time(),
    })


@metrics_bp.route('/api/signal_source_performance')
@login_required
def api_signal_source_performance():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User context unavailable'}), 401

    user_trades = UserTrade.query.filter_by(user_id=user_id).all()
    if not user_trades:
        return jsonify({
            'error': 'No trade data available for analysis',
            'signal_sources': {},
            'total_trades': 0,
        }), 404

    signal_performance: dict[str, dict[str, float | int]] = {}
    total_trades = len(user_trades)

    for trade in user_trades:
        signal_source = trade.signal_source or 'unknown'
        perf = signal_performance.setdefault(signal_source, {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
        })

        perf['total_trades'] += 1
        pnl = trade.pnl or 0.0
        perf['total_pnl'] += pnl
        if pnl > 0:
            perf['winning_trades'] += 1
            count = perf['winning_trades']
            perf['avg_win'] = ((perf['avg_win'] * (count - 1)) + pnl) / count
        else:
            perf['losing_trades'] += 1
            count = perf['losing_trades']
            perf['avg_loss'] = ((perf['avg_loss'] * (count - 1)) + abs(pnl)) / count if count else perf['avg_loss']

    for signal_source, perf in signal_performance.items():
        trades = perf['total_trades'] or 1
        perf['win_rate'] = (perf['winning_trades'] / trades) * 100
        total_wins = perf['winning_trades'] * perf['avg_win']
        total_losses = perf['losing_trades'] * perf['avg_loss']
        perf['profit_factor'] = total_wins / total_losses if total_losses > 0 else float('inf')
        related_returns = [trade.pnl or 0 for trade in user_trades if (trade.signal_source or 'unknown') == signal_source]
        if len(related_returns) > 1:
            avg_return = sum(related_returns) / len(related_returns)
            variance = sum((r - avg_return) ** 2 for r in related_returns) / len(related_returns)
            perf['sharpe_ratio'] = (avg_return / (variance ** 0.5)) if variance > 0 else 0.0
        else:
            perf['sharpe_ratio'] = 0.0

    sorted_sources = sorted(signal_performance.items(), key=lambda item: item[1]['total_pnl'], reverse=True)
    return jsonify({
        'signal_sources': dict(sorted_sources),
        'total_trades': total_trades,
        'best_performing_source': sorted_sources[0][0] if sorted_sources else None,
        'timestamp': time.time(),
    })


@metrics_bp.route('/api/confidence_score_analysis')
@login_required
def api_confidence_score_analysis():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User context unavailable'}), 401

    user_trades = UserTrade.query.filter(
        UserTrade.user_id == user_id,
        UserTrade.confidence_score.isnot(None)
    ).all()

    if not user_trades:
        return jsonify({
            'error': 'No trade data with confidence scores available',
            'confidence_buckets': {},
            'total_trades': 0,
        }), 404

    buckets = {
        '0.0-0.2': {'min': 0.0, 'max': 0.2, 'trades': [], 'total_pnl': 0.0, 'win_rate': 0.0},
        '0.2-0.4': {'min': 0.2, 'max': 0.4, 'trades': [], 'total_pnl': 0.0, 'win_rate': 0.0},
        '0.4-0.6': {'min': 0.4, 'max': 0.6, 'trades': [], 'total_pnl': 0.0, 'win_rate': 0.0},
        '0.6-0.8': {'min': 0.6, 'max': 0.8, 'trades': [], 'total_pnl': 0.0, 'win_rate': 0.0},
        '0.8-1.0': {'min': 0.8, 'max': 1.0, 'trades': [], 'total_pnl': 0.0, 'win_rate': 0.0},
    }

    correlation_points = []
    for trade in user_trades:
        confidence = trade.confidence_score or 0.0
        for bucket in buckets.values():
            if bucket['min'] <= confidence < bucket['max']:
                bucket['trades'].append(trade)
                bucket['total_pnl'] += trade.pnl or 0.0
                correlation_points.append((confidence, trade.pnl or 0.0))
                break

    for bucket in buckets.values():
        trades = bucket['trades']
        if not trades:
            continue
        wins = sum(1 for trade in trades if (trade.pnl or 0.0) > 0)
        bucket['win_rate'] = (wins / len(trades)) * 100

    confidence_scores = [point[0] for point in correlation_points]
    pnl_values = [point[1] for point in correlation_points]
    correlation = _pearson_corr(confidence_scores, pnl_values)

    best_bucket = max(buckets.items(), key=lambda item: item[1]['total_pnl'])

    return jsonify({
        'confidence_buckets': buckets,
        'correlation_confidence_pnl': correlation,
        'total_trades': len(user_trades),
        'best_confidence_bucket': best_bucket[0],
        'recommendation': f"Trades with confidence {best_bucket[0]} show best performance",
        'timestamp': time.time(),
    })


@metrics_bp.route('/api/user_strategy_performance')
@login_required
def api_user_strategy_performance():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User context unavailable'}), 401

    user_trades = UserTrade.query.filter_by(user_id=user_id).all()
    if not user_trades:
        return jsonify({
            'error': 'No trade data available for strategy analysis',
            'strategies': {},
            'total_trades': 0,
        }), 404

    strategy_performance: dict[str, dict[str, float | int]] = {}
    total_trades = len(user_trades)

    for trade in user_trades:
        strategy = trade.signal_source or 'unknown'
        perf = strategy_performance.setdefault(strategy, {
            'total_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0.0,
            'win_rate': 0.0,
            'avg_trade_pnl': 0.0,
            'max_win': float('-inf'),
            'max_loss': float('inf'),
            'sharpe_ratio': 0.0,
            'profit_factor': 0.0,
            'total_wins': 0.0,
            'total_losses': 0.0,
        })

        perf['total_trades'] += 1
        pnl = trade.pnl or 0.0
        perf['total_pnl'] += pnl
        if pnl > 0:
            perf['winning_trades'] += 1
            perf['total_wins'] += pnl
            perf['max_win'] = max(perf['max_win'], pnl)
        else:
            perf['total_losses'] += abs(pnl)
            perf['max_loss'] = min(perf['max_loss'], pnl)

    for strategy, perf in strategy_performance.items():
        trades = perf['total_trades'] or 1
        losses = trades - perf['winning_trades']
        perf['win_rate'] = (perf['winning_trades'] / trades) * 100
        perf['avg_trade_pnl'] = perf['total_pnl'] / trades
        avg_win = perf['total_wins'] / perf['winning_trades'] if perf['winning_trades'] else 0.0
        avg_loss = perf['total_losses'] / losses if losses else 0.0
        perf['avg_win'] = avg_win
        perf['avg_loss'] = avg_loss
        perf['profit_factor'] = perf['total_wins'] / perf['total_losses'] if perf['total_losses'] > 0 else float('inf')

        strategy_returns = [trade.pnl or 0.0 for trade in user_trades if (trade.signal_source or 'unknown') == strategy]
        if len(strategy_returns) > 1:
            avg_return = sum(strategy_returns) / len(strategy_returns)
            variance = sum((r - avg_return) ** 2 for r in strategy_returns) / len(strategy_returns)
            perf['sharpe_ratio'] = (avg_return / (variance ** 0.5)) if variance > 0 else 0.0
        else:
            perf['sharpe_ratio'] = 0.0

    rankings = {}
    for strategy, perf in strategy_performance.items():
        profit_factor = perf['profit_factor'] if perf['profit_factor'] != float('inf') else 10
        sharpe_component = (perf['sharpe_ratio'] * 10 + 5)
        sample_score = min(perf['total_trades'] / 10, 5)
        overall_score = (
            perf['win_rate'] * 0.3 +
            profit_factor * 0.3 +
            sharpe_component * 0.2 +
            sample_score * 0.2
        )
        rankings[strategy] = overall_score

    sorted_rankings = sorted(rankings.items(), key=lambda item: item[1], reverse=True)
    return jsonify({
        'strategies': strategy_performance,
        'rankings': [
            {'strategy': strategy, 'score': score, 'rank': idx + 1}
            for idx, (strategy, score) in enumerate(sorted_rankings)
        ],
        'total_trades': total_trades,
        'best_strategy': sorted_rankings[0][0] if sorted_rankings else None,
        'ranking_methodology': {
            'win_rate': '30%',
            'profit_factor': '30%',
            'sharpe_ratio': '20%',
            'sample_size': '20%',
        },
        'timestamp': time.time(),
    })
