"""Unified wrapper for CCXT exchange interactions."""
from __future__ import annotations

import ccxt
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class CCXTAdapter:
    """
    Factory and wrapper for connecting to multiple exchanges via CCXT.
    Encapsulates specific exchange quirks and provides a unified interface.
    """
    
    SUPPORTED_EXCHANGES = ['binance', 'bybit', 'kraken', 'kucoin', 'okx', 'coinbasepro']
    
    @staticmethod
    def get_exchange(exchange_id: str, api_key: str = None, secret: str = None, password: str = None, testnet: bool = False) -> Optional[ccxt.Exchange]:
        """
        Initialize and return a configured CCXT exchange instance.
        """
        exchange_id = exchange_id.lower()
        if exchange_id not in CCXTAdapter.SUPPORTED_EXCHANGES and exchange_id != 'binance': # Explicitly allow binance too
             # Attempt dynamic loading if installed but not in my short list
             pass
        
        if not hasattr(ccxt, exchange_id):
            logger.error(f"Exchange {exchange_id} not found in CCXT library.")
            return None

        exchange_class = getattr(ccxt, exchange_id)
        
        config = {
            'apiKey': api_key,
            'secret': secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'} 
        }
        
        if password:
            config['password'] = password # For KuCoin/OKX
            
        if testnet:
            config['sandbox'] = True

        try:
            exchange = exchange_class(config)
            if testnet and exchange_id == 'binance':
                 exchange.set_sandbox_mode(True) # Specific for Binance
            
            return exchange
        except Exception as e:
            logger.error(f"Failed to initialize {exchange_id}: {e}")
            return None

    @staticmethod
    def fetch_balance(exchange: ccxt.Exchange) -> Dict[str, float]:
        """Fetch total and free balance."""
        try:
            return exchange.fetch_balance()
        except Exception as e:
            logger.error(f"Error fetching balance from {exchange.id}: {e}")
            return {}

    @staticmethod
    def fetch_ticker(exchange: ccxt.Exchange, symbol: str) -> Dict[str, Any]:
        """Fetch current ticker price."""
        try:
            return exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            return {}
