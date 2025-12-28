"""
Exchange Adapters for Multi-Tenant Trading Engine
Provides real exchange integration with support for multiple exchanges.
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime
from enum import Enum

try:
    from binance.client import Client as BinanceClient

    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False
    BinanceClient = None

logger = logging.getLogger(__name__)


class ExchangeType(Enum):
    BINANCE = "binance"
    COINBASE = "coinbase"
    KRAKEN = "kraken"
    PAPER = "paper"  # Paper trading mode


@dataclass
class ExchangeCredentials:
    """Exchange API credentials."""

    api_key: str
    api_secret: str
    testnet: bool = False


@dataclass
class MarketData:
    """Real-time market data."""

    symbol: str
    price: float
    bid: float
    ask: float
    volume: float
    timestamp: datetime


@dataclass
class OrderBook:
    """Order book snapshot."""

    symbol: str
    bids: List[Tuple[float, float]]  # [(price, quantity), ...]
    asks: List[Tuple[float, float]]  # [(price, quantity), ...]
    timestamp: datetime


@dataclass
class AccountBalance:
    """Account balance information."""

    asset: str
    free: float
    locked: float
    total: float


@dataclass
class OrderStatus:
    """Order execution status."""

    order_id: str
    symbol: str
    side: str
    type: str
    quantity: float
    price: float
    status: str
    filled: float
    remaining: float
    timestamp: datetime


@dataclass
class KlineData:
    """Historical candlestick data."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class ExchangeAdapter:
    """Base class for exchange adapters."""

    def __init__(self, credentials: ExchangeCredentials):
        self.credentials = credentials
        self.client = None
        self.is_connected = False

    async def connect(self) -> bool:
        """Connect to exchange."""
        raise NotImplementedError

    async def disconnect(self):
        """Disconnect from exchange."""
        raise NotImplementedError

    async def get_balance(self, asset: Optional[str] = None) -> List[AccountBalance]:
        """Get account balance."""
        raise NotImplementedError

    async def get_ticker_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        raise NotImplementedError

    async def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[OrderBook]:
        """Get order book for symbol."""
        raise NotImplementedError

    async def get_historical_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> List[KlineData]:
        """Get historical candlestick data."""
        raise NotImplementedError

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderStatus:
        """Place an order."""
        raise NotImplementedError

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel an order."""
        raise NotImplementedError

    async def get_order_status(
        self, symbol: str, order_id: str
    ) -> Optional[OrderStatus]:
        """Get order status."""
        raise NotImplementedError

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderStatus]:
        """Get open orders."""
        raise NotImplementedError


class BinanceAdapter(ExchangeAdapter):
    """Binance exchange adapter."""

    def __init__(self, credentials: ExchangeCredentials):
        super().__init__(credentials)
        if not BINANCE_AVAILABLE:
            raise ImportError("python-binance library not available")

        # Initialize Binance client
        assert BinanceClient is not None, "Binance client not available"
        self.client = BinanceClient(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            testnet=credentials.testnet,
        )

    async def connect(self) -> bool:
        """Connect to Binance."""
        try:
            # Test connection by getting server time
            self.client.get_server_time()
            self.is_connected = True
            logger.info("Connected to Binance API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self.is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from Binance."""
        self.is_connected = False
        logger.info("Disconnected from Binance API")

    async def get_balance(self, asset: Optional[str] = None) -> List[AccountBalance]:
        """Get account balance from Binance."""
        try:
            account = self.client.get_account()
            balances = []

            for balance in account["balances"]:
                free = float(balance["free"])
                locked = float(balance["locked"])
                total = free + locked

                if total > 0:  # Only include assets with balance
                    balances.append(
                        AccountBalance(
                            asset=balance["asset"],
                            free=free,
                            locked=locked,
                            total=total,
                        )
                    )

            return balances
        except Exception as e:
            logger.error(f"Error getting Binance balance: {e}")
            return []

    async def get_ticker_price(self, symbol: str) -> Optional[float]:
        """Get current price from Binance."""
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            logger.error(f"Error getting Binance price for {symbol}: {e}")
            return None

    async def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[OrderBook]:
        """Get order book from Binance."""
        try:
            depth = self.client.get_order_book(symbol=symbol, limit=limit)

            bids = [(float(bid[0]), float(bid[1])) for bid in depth["bids"]]
            asks = [(float(ask[0]), float(ask[1])) for ask in depth["asks"]]

            return OrderBook(
                symbol=symbol, bids=bids, asks=asks, timestamp=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Error getting Binance orderbook for {symbol}: {e}")
            return None

    async def get_historical_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> List[KlineData]:
        """Get historical candlestick data from Binance."""
        try:
            # Map interval to Binance format
            interval_map = {
                "1m": "1m",
                "3m": "3m",
                "5m": "5m",
                "15m": "15m",
                "30m": "30m",
                "1h": "1h",
                "2h": "2h",
                "4h": "4h",
                "6h": "6h",
                "8h": "8h",
                "12h": "12h",
                "1d": "1d",
                "3d": "3d",
                "1w": "1w",
                "1M": "1M",
            }

            binance_interval = interval_map.get(interval, "1h")

            # Get klines from Binance
            klines = self.client.get_klines(
                symbol=symbol, interval=binance_interval, limit=limit
            )

            # Convert to KlineData objects
            result = []
            for kline in klines:
                result.append(
                    KlineData(
                        timestamp=datetime.fromtimestamp(
                            kline[0] / 1000
                        ),  # Convert from milliseconds
                        open=float(kline[1]),
                        high=float(kline[2]),
                        low=float(kline[3]),
                        close=float(kline[4]),
                        volume=float(kline[5]),
                    )
                )

            return result

        except Exception as e:
            logger.error(f"Error getting historical klines for {symbol}: {e}")
            return []

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderStatus:
        """Place order on Binance."""
        try:
            # Convert order type to Binance format
            binance_order_type = order_type.upper()
            if binance_order_type == "LIMIT" and price is None:
                raise ValueError("Price required for LIMIT orders")

            # Prepare order parameters
            order_params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": binance_order_type,
                "quantity": quantity,
            }

            if price is not None:
                order_params["price"] = price

            # Place order
            response = self.client.create_order(**order_params)

            return OrderStatus(
                order_id=response["orderId"],
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=float(response["origQty"]),
                price=float(response.get("price", 0)),
                status=response["status"].lower(),
                filled=float(response["executedQty"]),
                remaining=float(response["origQty"]) - float(response["executedQty"]),
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error placing Binance order: {e}")
            # Return failed order status
            return OrderStatus(
                order_id="failed",
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                price=price or 0,
                status="failed",
                filled=0,
                remaining=quantity,
                timestamp=datetime.utcnow(),
            )

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel order on Binance."""
        try:
            self.client.cancel_order(symbol=symbol, orderId=order_id)
            return True
        except Exception as e:
            logger.error(f"Error canceling Binance order {order_id}: {e}")
            return False

    async def get_order_status(
        self, symbol: str, order_id: str
    ) -> Optional[OrderStatus]:
        """Get order status from Binance."""
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)

            return OrderStatus(
                order_id=order["orderId"],
                symbol=symbol,
                side=order["side"].lower(),
                type=order["type"].lower(),
                quantity=float(order["origQty"]),
                price=float(order.get("price", 0)),
                status=order["status"].lower(),
                filled=float(order["executedQty"]),
                remaining=float(order["origQty"]) - float(order["executedQty"]),
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Error getting Binance order status for {order_id}: {e}")
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderStatus]:
        """Get open orders from Binance."""
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol

            orders = self.client.get_open_orders(**params)
            order_statuses = []

            for order in orders:
                order_statuses.append(
                    OrderStatus(
                        order_id=order["orderId"],
                        symbol=order["symbol"],
                        side=order["side"].lower(),
                        type=order["type"].lower(),
                        quantity=float(order["origQty"]),
                        price=float(order.get("price", 0)),
                        status=order["status"].lower(),
                        filled=float(order["executedQty"]),
                        remaining=float(order["origQty"]) - float(order["executedQty"]),
                        timestamp=datetime.utcnow(),
                    )
                )

            return order_statuses
        except Exception as e:
            logger.error(f"Error getting Binance open orders: {e}")
            return []


class PaperTradingAdapter(ExchangeAdapter):
    """Paper trading adapter for safe strategy testing."""

    def __init__(self, credentials: ExchangeCredentials):
        super().__init__(credentials)
        self.paper_balances = {
            "USDT": AccountBalance("USDT", 10000.0, 0.0, 10000.0),
            "BTC": AccountBalance("BTC", 0.5, 0.0, 0.5),
            "ETH": AccountBalance("ETH", 5.0, 0.0, 5.0),
        }
        self.paper_orders = []
        self.price_feeds = {}  # Cache for price data

    async def connect(self) -> bool:
        """Connect to paper trading (always succeeds)."""
        self.is_connected = True
        logger.info("Connected to Paper Trading")
        return True

    async def disconnect(self):
        """Disconnect from paper trading."""
        self.is_connected = False
        logger.info("Disconnected from Paper Trading")

    async def get_balance(self, asset: Optional[str] = None) -> List[AccountBalance]:
        """Get paper trading account balance."""
        if asset:
            return [
                self.paper_balances.get(asset, AccountBalance(asset, 0.0, 0.0, 0.0))
            ]
        return list(self.paper_balances.values())

    async def get_ticker_price(self, symbol: str) -> Optional[float]:
        """Get current price (simulated or from real market data)."""
        # In paper trading, we can still use real market data for prices
        # but simulate the trades
        if symbol in self.price_feeds:
            return self.price_feeds[symbol]

        # For demo purposes, return some mock prices
        # In a real implementation, you might fetch from a free API
        mock_prices = {
            "BTCUSDT": 45000.0,
            "ETHUSDT": 2800.0,
            "BNBUSDT": 320.0,
            "ADAUSDT": 0.45,
            "SOLUSDT": 95.0,
        }

        price = mock_prices.get(symbol, 100.0)
        self.price_feeds[symbol] = price
        return price

    async def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[OrderBook]:
        """Get simulated order book."""
        price = await self.get_ticker_price(symbol)
        if not price:
            return None

        # Generate simulated order book around current price
        spread = price * 0.001  # 0.1% spread

        bids = []
        asks = []

        for i in range(limit):
            bid_price = price - spread - (i * spread * 0.1)
            ask_price = price + spread + (i * spread * 0.1)
            quantity = 10.0 / (i + 1)  # Decreasing quantity

            bids.append((max(bid_price, 0.01), quantity))
            asks.append((ask_price, quantity))

        return OrderBook(
            symbol=symbol, bids=bids, asks=asks, timestamp=datetime.utcnow()
        )

    async def get_historical_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> List[KlineData]:
        """Get simulated historical candlestick data for paper trading."""
        try:
            # Generate simulated historical data
            # In a real implementation, you might use real historical data
            # but for paper trading, we'll generate realistic-looking data

            current_price = await self.get_ticker_price(symbol) or 100.0
            volatility = 0.02  # 2% daily volatility

            klines = []
            current_time = datetime.utcnow()

            for i in range(limit):
                # Generate price movement
                price_change = (
                    current_price * volatility * (0.5 - i * 0.001)
                )  # Slight trend
                noise = (
                    current_price * volatility * 0.1 * (0.5 - (i % 2))
                )  # Random noise
                close_price = current_price + price_change + noise

                # Ensure reasonable bounds
                close_price = max(close_price, current_price * 0.5)
                close_price = min(close_price, current_price * 1.5)

                # Generate OHLC
                high = close_price * (1 + abs(price_change) * 0.5)
                low = close_price * (1 - abs(price_change) * 0.5)
                open_price = current_price
                volume = 1000.0 + (i * 10)  # Increasing volume

                klines.append(
                    KlineData(
                        timestamp=current_time,
                        open=open_price,
                        high=high,
                        low=low,
                        close=close_price,
                        volume=volume,
                    )
                )

                # Move to previous candle
                current_price = close_price
                # For hourly candles, subtract 1 hour, etc.
                if interval.endswith("h"):
                    hours = int(interval[:-1]) if interval[:-1].isdigit() else 1
                    current_time = current_time.replace(hour=current_time.hour - hours)
                elif interval.endswith("d"):
                    days = int(interval[:-1]) if interval[:-1].isdigit() else 1
                    current_time = current_time.replace(day=current_time.day - days)
                else:
                    # Default to 1 hour intervals
                    current_time = current_time.replace(hour=current_time.hour - 1)

            return klines[::-1]  # Reverse to get chronological order

        except Exception as e:
            logger.error(f"Error generating paper trading klines for {symbol}: {e}")
            return []

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderStatus:
        """Simulate order placement."""
        current_price = await self.get_ticker_price(symbol)
        if not current_price:
            return OrderStatus(
                order_id="failed",
                symbol=symbol,
                side=side,
                type=order_type,
                quantity=quantity,
                price=price or 0,
                status="failed",
                filled=0,
                remaining=quantity,
                timestamp=datetime.utcnow(),
            )

        # Determine execution price
        if order_type.upper() == "MARKET":
            execution_price = current_price
        elif order_type.upper() == "LIMIT" and price:
            # For paper trading, we'll assume limit orders execute immediately
            # In a more sophisticated simulation, you might delay execution
            execution_price = price
        else:
            execution_price = current_price

        # Calculate trade value
        trade_value = quantity * execution_price

        # Check if user has sufficient balance
        base_asset = symbol[:-4]  # e.g., 'BTC' from 'BTCUSDT'
        quote_asset = symbol[-4:]  # e.g., 'USDT' from 'BTCUSDT'

        if side.upper() == "BUY":
            # Buying: need quote currency (USDT)
            if self.paper_balances[quote_asset].free < trade_value:
                return OrderStatus(
                    order_id="insufficient_balance",
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    price=execution_price,
                    status="failed",
                    filled=0,
                    remaining=quantity,
                    timestamp=datetime.utcnow(),
                )
            # Update balances
            self.paper_balances[quote_asset].free -= trade_value
            self.paper_balances[quote_asset].total -= trade_value
            self.paper_balances[base_asset].free += quantity
            self.paper_balances[base_asset].total += quantity

        elif side.upper() == "SELL":
            # Selling: need base currency (BTC)
            if self.paper_balances[base_asset].free < quantity:
                return OrderStatus(
                    order_id="insufficient_balance",
                    symbol=symbol,
                    side=side,
                    type=order_type,
                    quantity=quantity,
                    price=execution_price,
                    status="failed",
                    filled=0,
                    remaining=quantity,
                    timestamp=datetime.utcnow(),
                )
            # Update balances
            self.paper_balances[base_asset].free -= quantity
            self.paper_balances[base_asset].total -= quantity
            self.paper_balances[quote_asset].free += trade_value
            self.paper_balances[quote_asset].total += trade_value

        # Create order record
        order_id = f"paper_{len(self.paper_orders) + 1}"
        order_status = OrderStatus(
            order_id=order_id,
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity,
            price=execution_price,
            status="filled",
            filled=quantity,
            remaining=0,
            timestamp=datetime.utcnow(),
        )

        self.paper_orders.append(order_status)
        logger.info(f"Paper trade executed: {order_status}")

        return order_status

    async def cancel_order(self, symbol: str, order_id: str) -> bool:
        """Cancel paper order (not applicable for filled orders)."""
        # Paper orders are immediately filled, so cancellation isn't meaningful
        return False

    async def get_order_status(
        self, symbol: str, order_id: str
    ) -> Optional[OrderStatus]:
        """Get paper order status."""
        for order in self.paper_orders:
            if order.order_id == order_id and order.symbol == symbol:
                return order
        return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderStatus]:
        """Get open paper orders (paper orders are immediately filled)."""
        return []  # No open orders in paper trading


class ExchangeFactory:
    """Factory for creating exchange adapters."""

    @staticmethod
    def create_adapter(
        exchange_type: ExchangeType, credentials: ExchangeCredentials
    ) -> ExchangeAdapter:
        """Create exchange adapter instance."""
        if exchange_type == ExchangeType.BINANCE:
            return BinanceAdapter(credentials)
        elif exchange_type == ExchangeType.PAPER:
            return PaperTradingAdapter(credentials)
        else:
            raise ValueError(f"Exchange {exchange_type.value} not supported yet")


class ExchangeManager:
    """Manages multiple exchange connections for multi-tenant trading."""

    def __init__(self):
        self.adapters: Dict[str, ExchangeAdapter] = {}
        self._lock = asyncio.Lock()

    async def get_adapter(
        self,
        user_id: str,
        exchange_type: ExchangeType,
        credentials: ExchangeCredentials,
    ) -> ExchangeAdapter:
        """Get or create exchange adapter for user."""
        adapter_key = f"{user_id}_{exchange_type.value}"

        async with self._lock:
            if adapter_key not in self.adapters:
                adapter = ExchangeFactory.create_adapter(exchange_type, credentials)
                await adapter.connect()
                self.adapters[adapter_key] = adapter

            return self.adapters[adapter_key]

    async def remove_adapter(self, user_id: str, exchange_type: ExchangeType):
        """Remove exchange adapter for user."""
        adapter_key = f"{user_id}_{exchange_type.value}"

        async with self._lock:
            if adapter_key in self.adapters:
                await self.adapters[adapter_key].disconnect()
                del self.adapters[adapter_key]

    async def get_user_balance(
        self,
        user_id: str,
        exchange_type: ExchangeType,
        credentials: ExchangeCredentials,
        asset: Optional[str] = None,
    ) -> List[AccountBalance]:
        """Get user account balance."""
        adapter = await self.get_adapter(user_id, exchange_type, credentials)
        return await adapter.get_balance(asset)

    async def execute_trade(
        self,
        user_id: str,
        exchange_type: ExchangeType,
        credentials: ExchangeCredentials,
        symbol: str,
        side: str,
        quantity: float,
        price: Optional[float] = None,
    ) -> OrderStatus:
        """Execute trade on exchange."""
        adapter = await self.get_adapter(user_id, exchange_type, credentials)

        # Determine order type
        order_type = "MARKET" if price is None else "LIMIT"

        return await adapter.place_order(symbol, side, order_type, quantity, price)


# Global exchange manager instance
exchange_manager = ExchangeManager()
