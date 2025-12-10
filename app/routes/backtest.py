"""Blueprint containing backtest endpoints."""
from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.auth.decorators import login_required
from app.runtime.symbols import get_active_trading_universe

backtest_bp = Blueprint("backtest", __name__, url_prefix="/api")

@backtest_bp.route("/backtest/run", methods=["POST"])
@login_required
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
            return jsonify({"error": f"Symbol {symbol} not allowed for this user."}), 403

        # Placeholder for actual backtest logic
        # In a real implementation, this would call the bot's backtesting functions
        # For now, return mock results
        results = [
            {"metric": "Total Trades", "value": "150"},
            {"metric": "Win Rate", "value": "68.5%"},
            {"metric": "Profit Factor", "value": "1.45"},
            {"metric": "Max Drawdown", "value": "12.3%"},
            {"metric": "Sharpe Ratio", "value": "1.23"},
            {"metric": "Total Return", "value": "45.6%"},
        ]

        return jsonify({"results": results})
    except Exception as exc:
        print(f"Error in POST /api/backtest/run: {exc}")
        return jsonify({"error": "Backtest failed"}), 500