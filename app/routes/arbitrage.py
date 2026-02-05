
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required
from app.services.arbitrage_scanner import ArbitrageScanner
from app.trading.exchange_adapters import ExchangeType
import asyncio

arbitrage_bp = Blueprint('arbitrage', __name__, url_prefix='/trading/arbitrage')

@arbitrage_bp.route('/')
@login_required
def dashboard():
    """Render the Arbitrage Dashboard."""
    return render_template('trading/arbitrage.html')

@arbitrage_bp.route('/api/opportunities')
@login_required
def get_opportunities():
    """Get live arbitrage opportunities."""
    # In a real app, this would trigger a background task or read from cache.
    # For now, we return mock data for immediate UI feedback as per plan.
    # To enable real scanning, uncomment the async logic below (requires setting up event loop properly in Flask)
    
    # opportunities = asyncio.run(ArbitrageScanner.get_mock_opportunities())
    
    # Since flask is sync by default (unless using async route), we'll use the mock synchronous wrapper for now
    # or just return the data directly.
    import asyncio
    try:
        data = asyncio.run(ArbitrageScanner.get_mock_opportunities())
    except RuntimeError:
        # Loop already running? Fallback
        data = [
            {
                "symbol": "BTC/USDT",
                "buy_exchange": "binance",
                "buy_price": 42000.0,
                "sell_exchange": "kraken",
                "sell_price": 42100.0,
                "spread_abs": 100.0,
                "spread_pct": 0.24,
                "timestamp": "Now"
            }
        ]
        
    return jsonify({"success": True, "data": data})
