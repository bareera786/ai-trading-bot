#!/usr/bin/env python3
"""Test script to verify Binance testnet market data fetching"""

import sys
import os

sys.path.append("/Users/tahir/Desktop/ai-bot")

# Import the function we want to test
from app.services.binance_market import BinanceMarketDataHelper
import logging


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except:
        return float(default)


helper = BinanceMarketDataHelper(
    bot_logger=logging.getLogger(),
    safe_float=_safe_float,
    testnet_detector=lambda: True,  # Use testnet for testing
)


def test_market_data():
    """Test fetching market data for a few symbols"""
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    print("Testing Binance testnet market data fetching...")
    print("=" * 50)

    for symbol in symbols:
        try:
            data = helper.get_real_market_data(symbol)
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
