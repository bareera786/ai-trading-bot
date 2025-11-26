#!/usr/bin/env python3
"""Test script to verify Binance testnet market data fetching"""

import sys
import os
sys.path.append('/Users/tahir/Desktop/ai-bot')

# Import the function we want to test
from ai_ml_auto_bot_final import get_real_market_data

def test_market_data():
    """Test fetching market data for a few symbols"""
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']

    print("Testing Binance testnet market data fetching...")
    print("=" * 50)

    for symbol in symbols:
        try:
            data = get_real_market_data(symbol)
            print(f"✅ {symbol}:")
            print(f"   Price: ${data['price']:.2f}")
            print(f"   Change: {data['change']:.2f}%")
            print(f"   Volume: {data['volume']:.0f}")
            print(f"   High: ${data['high']:.2f}")
            print(f"   Low: ${data['low']:.2f}")
            print()
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
            print()

if __name__ == "__main__":
    test_market_data()