import asyncio
import aiohttp
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AsyncDataStream:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = "https://testnet.binance.vision" if testnet else "https://api.binance.com"
        self.running = False
        self.processing_tasks = set()

    async def start_stream(self):
        """Start the async data streaming"""
        self.running = True
        logger.info("🚀 Starting async data stream...")

        try:
            async with aiohttp.ClientSession() as session:
                # Start multiple concurrent streams
                tasks = [
                    self.process_tick_data_async(session),
                    self.process_orderbook_async(session),
                    self.process_trades_async(session)
                ]

                await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"❌ Data stream error: {e}")
        finally:
            self.running = False
            logger.info("🛑 Data stream stopped")

    async def process_tick_data_async(self, session: aiohttp.ClientSession):
        """Process tick data asynchronously"""
        symbol = "BTCUSDT"
        url = f"{self.base_url}/api/v3/ticker/price"

        while self.running:
            try:
                data = await self.get_tick_data_async(session, symbol)
                if data:
                    # Create background task to avoid blocking
                    task = asyncio.create_task(self.process_tick_async(data))
                    self.processing_tasks.add(task)
                    task.add_done_callback(self.processing_tasks.discard)

                await asyncio.sleep(0.1)  # Non-blocking yield

            except Exception as e:
                logger.error(f"Tick data error: {e}")
                await asyncio.sleep(1)  # Backoff on error

    async def process_orderbook_async(self, session: aiohttp.ClientSession):
        """Process orderbook data asynchronously"""
        symbol = "BTCUSDT"
        url = f"{self.base_url}/api/v3/depth"

        while self.running:
            try:
                data = await self.get_orderbook_async(session, symbol)
                if data:
                    task = asyncio.create_task(self.process_orderbook_data_async(data))
                    self.processing_tasks.add(task)
                    task.add_done_callback(self.processing_tasks.discard)

                await asyncio.sleep(0.5)  # Less frequent updates for orderbook

            except Exception as e:
                logger.error(f"Orderbook error: {e}")
                await asyncio.sleep(1)

    async def process_trades_async(self, session: aiohttp.ClientSession):
        """Process recent trades asynchronously"""
        symbol = "BTCUSDT"
        url = f"{self.base_url}/api/v3/trades"

        while self.running:
            try:
                trades = await self.get_recent_trades_async(session, symbol)
                if trades:
                    task = asyncio.create_task(self.process_trades_data_async(trades))
                    self.processing_tasks.add(task)
                    task.add_done_callback(self.processing_tasks.discard)

                await asyncio.sleep(1)  # Trades update every second

            except Exception as e:
                logger.error(f"Trades error: {e}")
                await asyncio.sleep(1)

    async def get_tick_data_async(self, session: aiohttp.ClientSession, symbol: str) -> Optional[Dict]:
        """Get ticker data asynchronously"""
        url = f"{self.base_url}/api/v3/ticker/price"
        params = {'symbol': symbol}

        try:
            async with session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'symbol': data['symbol'],
                        'price': float(data['price']),
                        'timestamp': datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.warning(f"Failed to get tick data: {e}")

        return None

    async def get_orderbook_async(self, session: aiohttp.ClientSession, symbol: str) -> Optional[Dict]:
        """Get orderbook data asynchronously"""
        url = f"{self.base_url}/api/v3/depth"
        params = {'symbol': symbol, 'limit': 10}

        try:
            async with session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'symbol': symbol,
                        'bids': data['bids'][:5],  # Top 5 bids
                        'asks': data['asks'][:5],  # Top 5 asks
                        'timestamp': datetime.utcnow().isoformat()
                    }
        except Exception as e:
            logger.warning(f"Failed to get orderbook: {e}")

        return None

    async def get_recent_trades_async(self, session: aiohttp.ClientSession, symbol: str) -> Optional[list]:
        """Get recent trades asynchronously"""
        url = f"{self.base_url}/api/v3/trades"
        params = {'symbol': symbol, 'limit': 5}

        try:
            async with session.get(url, params=params, timeout=5) as response:
                if response.status == 200:
                    trades = await response.json()
                    return [{
                        'symbol': symbol,
                        'price': float(trade['price']),
                        'qty': float(trade['qty']),
                        'timestamp': trade['time'],
                        'is_buyer_maker': trade['isBuyerMaker']
                    } for trade in trades]
        except Exception as e:
            logger.warning(f"Failed to get trades: {e}")

        return None

    async def process_tick_async(self, data: Dict):
        """Process tick data in background"""
        try:
            # Implement your tick processing logic here
            logger.debug(f"📊 Processed tick: {data['symbol']} @ {data['price']}")
            # Add to your trading strategy, indicators, etc.
        except Exception as e:
            logger.error(f"Tick processing error: {e}")

    async def process_orderbook_data_async(self, data: Dict):
        """Process orderbook data in background"""
        try:
            logger.debug(f"📈 Processed orderbook: {data['symbol']}")
            # Implement orderbook analysis
        except Exception as e:
            logger.error(f"Orderbook processing error: {e}")

    async def process_trades_data_async(self, trades: list):
        """Process trades data in background"""
        try:
            logger.debug(f"💰 Processed {len(trades)} trades")
            # Implement trade analysis
        except Exception as e:
            logger.error(f"Trades processing error: {e}")

    async def stop_stream(self):
        """Stop the data stream gracefully"""
        logger.info("🛑 Stopping data stream...")
        self.running = False

        # Wait for all processing tasks to complete
        if self.processing_tasks:
            await asyncio.gather(*self.processing_tasks, return_exceptions=True)

        logger.info("✅ Data stream stopped gracefully")