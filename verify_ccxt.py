
import asyncio
import sys
from unittest.mock import MagicMock, AsyncMock
import ccxt.async_support as ccxt_async
import os
from cryptography.fernet import Fernet
os.environ['ENCRYPTION_KEY'] = Fernet.generate_key().decode()

# Mock ccxt before importing adapters
sys.modules['ccxt.async_support'] = MagicMock()
ccxt_async.kraken = MagicMock()
ccxt_async.kraken.return_value = AsyncMock()

from app.trading.exchange_adapters import ExchangeFactory, ExchangeType, ExchangeCredentials, CCXTExchangeAdapter

async def verify_ccxt_integration():
    print("Verifying CCXT Adapter Integration...")
    
    # Setup mock
    mock_exchange = AsyncMock()
    mock_exchange.load_markets.return_value = {}
    mock_exchange.fetch_ticker.return_value = {'last': 50000.0}
    mock_exchange.fetch_balance.return_value = {
        'total': {'BTC': 1.5, 'USDT': 1000.0},
        'BTC': {'free': 1.0, 'used': 0.5},
        'USDT': {'free': 1000.0, 'used': 0.0}
    }
    mock_exchange.close.return_value = None
    
    # Inject mock class
    # We need to ensure that when getattr(ccxt_async, 'kraken') is called, it returns a class 
    # that returns our mock_exchange when instantiated.
    MockExchangeClass = MagicMock(return_value=mock_exchange)
    setattr(ccxt_async, 'kraken', MockExchangeClass)
    
    creds = ExchangeCredentials("key", "secret")
    
    # 1. Create Adapter
    adapter = ExchangeFactory.create_adapter(ExchangeType.KRAKEN, creds)
    if not isinstance(adapter, CCXTExchangeAdapter):
        print("FAIL: Factory returned wrong adapter type")
        return False
        
    print("SUCCESS: Factory returned CCXTExchangeAdapter")
    
    # 2. Connect
    connected = await adapter.connect()
    if not connected:
        print("FAIL: Connect failed")
        return False
    print("SUCCESS: Connected (Mocked)")
    
    # 3. Fetch Ticker
    price = await adapter.get_ticker_price("BTC/USDT")
    if price == 50000.0:
         print(f"SUCCESS: Fetched ticker price: {price}")
    else:
         print(f"FAIL: Wrong ticker price: {price}")
         return False

    # 4. Fetch Balance
    balances = await adapter.get_balance()
    if len(balances) == 2:
        print("SUCCESS: Fetched balances correctly")
    else:
        print(f"FAIL: Wrong balance count: {len(balances)}")
        return False

    await adapter.disconnect()
    print("SUCCESS: Disconnected")
    return True

if __name__ == "__main__":
    try:
        if asyncio.run(verify_ccxt_integration()):
            print("VERIFICATION PASSED")
            sys.exit(0)
        else:
            print("VERIFICATION FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
