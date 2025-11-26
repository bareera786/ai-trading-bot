#!/usr/bin/env python3
"""
Simple test server for market data API
"""

from flask import Flask, jsonify
import random

app = Flask(__name__)

@app.route('/api/realtime/market_data')
def get_realtime_market_data():
    """Get current market data for polling fallback"""
    try:
        # Top 10 Binance symbols by trading volume
        top_symbols = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'XRPUSDT',
            'SOLUSDT', 'DOTUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LTCUSDT'
        ]

        market_data = {}
        for symbol in top_symbols:
            # Generate mock data for top symbols
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
                'volume_24h': random.randint(1000000, 100000000),
                'symbol': symbol
            }

        return jsonify({
            'success': True,
            'data': market_data,
            'timestamp': 1234567890
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': 1234567890
        }), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)