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
