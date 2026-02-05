"""Blueprint containing backtest endpoints."""
from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from app.auth.decorators import subscription_required
from app.runtime.symbols import get_active_trading_universe

backtest_bp = Blueprint("backtest", __name__, url_prefix="/api")


def _ctx() -> dict:
    ctx = current_app.extensions.get("ai_bot_context")
    if not ctx:
        raise RuntimeError("AI bot context is not initialized")
    return ctx


@backtest_bp.route("/backtest/run", methods=["POST"])
@subscription_required
def api_run_backtest():
    try:
        data = request.get_json() or {}
        symbol = data.get("symbol", "BTCUSDT")
        date_range = data.get("date_range", "2024-01-01 to 2024-12-31")
        strategy = data.get("strategy", "Ultimate Ensemble")

        # Validate symbol: must be in user's selected, custom, or default universe
        user_symbols = current_user.get_selected_symbols()
        if getattr(current_user, "is_premium", False):
            user_symbols.extend(current_user.get_custom_symbols())
        allowed_symbols = set(user_symbols) | set(get_active_trading_universe())
        if symbol not in allowed_symbols:
            return (
                jsonify({"error": f"Symbol {symbol} not allowed for this user."}),
                403,
            )

        # Get the bot instance from the runtime context
        ctx = _ctx()
        ultimate_ml_system = ctx.get("ultimate_ml_system")
        if not ultimate_ml_system:
            return jsonify({"error": "AI bot system is not available"}), 503

        # Parse date range for backtest parameters
        # For now, we'll use default parameters, but this could be enhanced
        # to parse the date_range string and calculate years accordingly
        years = 0.5  # Default to 6 months for faster testing
        interval = "1d"  # Daily data

        # Run the real backtest
        backtest_result = ultimate_ml_system.comprehensive_backtest(
            symbol=symbol,
            years=years,
            interval=interval,
            initial_balance=1000.0,
            use_real_data=True,
        )

        if not backtest_result or backtest_result.get("notes") == "insufficient data":
            return jsonify({"error": "Insufficient data for backtest"}), 400

        # Format results for the frontend
        results = [
            {
                "metric": "Total Trades",
                "value": str(len(backtest_result.get("trades", []))),
            },
            {
                "metric": "Win Rate",
                "value": f"{backtest_result.get('win_rate', 0):.1f}%",
            },
            {
                "metric": "Profit Factor",
                "value": f"{backtest_result.get('profit_factor', 0):.2f}"
                if backtest_result.get("profit_factor")
                else "N/A",
            },
            {
                "metric": "Max Drawdown",
                "value": f"{backtest_result.get('max_drawdown', 0):.1%}",
            },
            {
                "metric": "Sharpe Ratio",
                "value": f"{backtest_result.get('sharpe_ratio', 0):.2f}",
            },
            {
                "metric": "Total Return",
                "value": f"{backtest_result.get('total_return', 0):.1%}",
            },
            {
                "metric": "Final Balance",
                "value": f"${backtest_result.get('final_balance', 0):.2f}",
            },
            {
                "metric": "Model Accuracy",
                "value": f"{backtest_result.get('accuracy', 0):.1%}",
            },
        ]

        return jsonify({"results": results})
    except Exception as exc:
        print(f"Error in POST /api/backtest/run: {exc}")
        return jsonify({"error": "Backtest failed"}), 500


# Enhanced backtest endpoints for Phase 3
@backtest_bp.route("/backtest/run-enhanced", methods=["POST"])
@subscription_required
def api_run_backtest_enhanced():
    """Enhanced backtest with full visualization data"""
    try:
        import random
        import numpy as np
        from datetime import datetime, timedelta
        
        data = request.get_json() or {}
        strategy = data.get("strategy", "ML-Based")
        symbols = data.get("symbols", ["BTCUSDT"])
        start_date = data.get("start_date", "2024-01-01")
        end_date = data.get("end_date", "2024-12-31")
        initial_capital = float(data.get("initial_capital", 10000))
        
        # Generate sample results (TODO: Replace with real backtest engine)
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        days = (end - start).days
        
        # Generate equity curve
        equity_curve = [initial_capital]
        current_equity = initial_capital
        
        for i in range(days):
            daily_return = random.uniform(-0.03, 0.05)
            current_equity *= (1 + daily_return)
            equity_curve.append(current_equity)
        
        # Calculate metrics
        final_equity = equity_curve[-1]
        total_return = ((final_equity - initial_capital) / initial_capital) * 100
        
        returns = np.diff(equity_curve) / equity_curve[:-1]
        sharpe_ratio = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        downside_returns = returns[returns < 0]
        sortino_ratio = (np.mean(returns) / np.std(downside_returns)) * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = (np.array(equity_curve) - running_max) / running_max * 100
        max_drawdown = np.min(drawdown)
        
        # Generate equity data points
        equity_data = []
        for i, equity in enumerate(equity_curve):
            date = start + timedelta(days=i)
            equity_data.append({
                "date": date.strftime("%Y-%m-%d"),
                "equity": round(equity, 2),
                "drawdown": round(drawdown[i], 2) if i < len(drawdown) else 0
            })
        
        # Generate sample trades
        num_trades = random.randint(50, 150)
        trades = []
        wins = 0
        
        for i in range(num_trades):
            symbol = random.choice(symbols)
            side = random.choice(['BUY', 'SELL'])
            entry_price = random.uniform(100, 50000)
            exit_price = entry_price * random.uniform(0.95, 1.08)
            amount = random.uniform(0.01, 0.5)
            
            pnl = (exit_price - entry_price) * amount if side == "BUY" else (entry_price - exit_price) * amount
            if pnl > 0:
                wins += 1
            
            trade_date = start + timedelta(days=random.randint(0, days))
            
            trades.append({
                "timestamp": trade_date.isoformat(),
                "symbol": symbol,
                "side": side,
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "amount": round(amount, 6),
                "pnl": round(pnl, 2)
            })
        
        trades.sort(key=lambda x: x['timestamp'])
        
        win_rate = (wins / num_trades * 100) if num_trades > 0 else 0
        total_pnl = sum(t['pnl'] for t in trades)
        avg_profit = total_pnl / num_trades if num_trades > 0 else 0
        
        return jsonify({
            "success": True,
            "backtest_id": f"bt_{int(datetime.now().timestamp())}",
            "metrics": {
                "total_return": round(total_return, 2),
                "final_equity": round(final_equity, 2),
                "sharpe_ratio": round(sharpe_ratio, 2),
                "sortino_ratio": round(sortino_ratio, 2),
                "max_drawdown": round(max_drawdown, 2),
                "win_rate": round(win_rate, 1),
                "total_trades": num_trades,
                "winning_trades": wins,
                "losing_trades": num_trades - wins,
                "avg_profit_per_trade": round(avg_profit, 2),
                "total_pnl": round(total_pnl, 2)
            },
            "equity_curve": equity_data,
            "trades": trades[:50]  # Return first 50 trades for display
        })
        
    except Exception as exc:
        print(f"Error in enhanced backtest: {exc}")
        return jsonify({"error": str(exc)}), 500


@backtest_bp.route("/backtest/strategies", methods=["GET"])
def api_get_strategies():
    """Get available strategies for backtesting"""
    strategies = [
        {"id": "ml_based", "name": "ML-Based", "description": "Machine learning ensemble"},
        {"id": "trend_following", "name": "Trend Following", "description": "Follow market trends"},
        {"id": "mean_reversion", "name": "Mean Reversion", "description": "Trade reversals"},
        {"id": "breakout", "name": "Breakout", "description": "Breakout trading"},
        {"id": "momentum", "name": "Momentum", "description": "Momentum strategy"},
    ]
    return jsonify({"success": True, "strategies": strategies})


@backtest_bp.route("/backtest/symbols", methods=["GET"])
def api_get_symbols():
    """Get available symbols for backtesting"""
    symbols = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT",
        "XRPUSDT", "DOTUSDT", "UNIUSDT", "LINKUSDT", "LTCUSDT"
    ]
    return jsonify({"success": True, "symbols": symbols})
