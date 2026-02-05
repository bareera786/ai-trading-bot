
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.trading.exchange_adapters import ExchangeFactory, ExchangeType, ExchangeCredentials, CCXTExchangeAdapter

logger = logging.getLogger(__name__)

class ArbitrageScanner:
    """Service to scan for arbitrage opportunities across exchanges."""

    @staticmethod
    async def fetch_price(exchange_type: ExchangeType, symbol: str) -> Optional[float]:
        """Helper to fetch a single price."""
        try:
            # For scanning, we don't need real API keys (public data usually), 
            # but our adapter requires them. We can use dummy keys for public data 
            # if the underlying CCXT driver supports it, or use a cached public adapter.
            # For now, we assume credentials are provided or we use a 'public' mode.
            
            # NOTE: Ideally we'd have a pool of public adapters. 
            # Here we create a temporary one (inefficient but functional for MVP).
            # In prod, re-use these.
            creds = ExchangeCredentials("public", "public") 
            adapter = ExchangeFactory.create_adapter(exchange_type, creds)
            
            # Connect only if necessary (some ccxt calls need connect/load_markets)
            if isinstance(adapter, CCXTExchangeAdapter):
                await adapter.connect()
                
            price = await adapter.get_ticker_price(symbol)
            
            if isinstance(adapter, CCXTExchangeAdapter):
                await adapter.disconnect()
                
            return price
        except Exception as e:
            logger.error(f"Error fetching price from {exchange_type.value}: {e}")
            return None

    @staticmethod
    async def scan_opportunity(symbol: str, exchanges: List[ExchangeType]) -> Dict[str, Any]:
        """
        Check spread for a symbol across given exchanges.
        Returns closest dictionary with opportunity data.
        """
        prices = {}
        
        # Fetch prices in parallel
        tasks = [ArbitrageScanner.fetch_price(exc, symbol) for exc in exchanges]
        results = await asyncio.gather(*tasks)
        
        for exc, price in zip(exchanges, results):
            if price:
                prices[exc.value] = price

        if len(prices) < 2:
            return None # Need at least 2 venues

        # Find min and max
        sorted_prices = sorted(prices.items(), key=lambda x: x[1])
        min_exc, min_price = sorted_prices[0]
        max_exc, max_price = sorted_prices[-1]
        
        spread = max_price - min_price
        spread_pct = (spread / min_price) * 100
        
        return {
            "symbol": symbol,
            "buy_exchange": min_exc,
            "buy_price": min_price,
            "sell_exchange": max_exc,
            "sell_price": max_price,
            "spread_abs": spread,
            "spread_pct": round(spread_pct, 2),
            "timestamp": datetime.utcnow().isoformat()
        }

    @staticmethod
    async def get_mock_opportunities() -> List[Dict[str, Any]]:
        """Return dummy data for UI testing if real scanning is slow/fails."""
        return [
            {
                "symbol": "BTC/USDT",
                "buy_exchange": "binance",
                "buy_price": 50000.0,
                "sell_exchange": "kraken",
                "sell_price": 50500.0,
                "spread_abs": 500.0,
                "spread_pct": 1.0,
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "symbol": "ETH/USDT",
                "buy_exchange": "okx",
                "buy_price": 3000.0,
                "sell_exchange": "coinbase",
                "sell_price": 3050.0,
                "spread_abs": 50.0,
                "spread_pct": 1.67,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
