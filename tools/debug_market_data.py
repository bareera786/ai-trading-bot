import sys
import os
import time

# Add app to path
sys.path.append(os.getcwd())

from app.core.config_trading import TRADING_CONFIG
from app.services.binance_market import BinanceMarketDataService
from app.services.binance_market_futures import BinanceFuturesMarketDataService

def check_data():
    print("🚀 Initializing Market Data Services...")
    spot_service = BinanceMarketDataService()
    futures_service = BinanceFuturesMarketDataService()
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    print("\n🔍 Checking SPOT Prices:")
    spot_data = spot_service.get_market_data(symbols)
    for s, data in spot_data.items():
        print(f"   {s}: {data.get('price')} (Vol: {data.get('volume')})")
        
    print("\n🔍 Checking FUTURES Prices:")
    futures_data = futures_service.get_all_market_data() # This fetches for all, filter for ours
    for s in symbols:
        data = futures_data.get(s)
        if data:
            print(f"   {s}: {data.get('markPrice')} (Funding: {data.get('fundingRate')})")
        else:
            print(f"   {s}: NO DATA")

if __name__ == "__main__":
    check_data()
