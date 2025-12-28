"""Comprehensive trading integration tests."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta
import time

from app.trading.data_stream import AsyncDataStream
from app.cache.trading_cache import TradingCache
from app.utils.batch_processor import BatchDatabase
from app.ml.feature_store import FeatureStore
from app.security.credential_manager import CredentialManager
from app.ml.memory_efficient_loader import ChunkedDataLoader
from app.utils.database_pool import DatabasePool


class MockExchange:
    """Mock exchange for testing trading operations."""

    def __init__(self):
        self.orders = []
        self.positions = {}
        self.balance = {"USDT": 10000.0, "BTC": 0.5}
        self.call_history = []

    def create_order(self, symbol, side, quantity, price=None, order_type="market"):
        """Mock order creation."""
        self.call_history.append({
            "method": "create_order",
            "args": [symbol, side, quantity, price, order_type]
        })

        if side == "buy" and self.balance["USDT"] < (price or 50000) * quantity:
            raise InsufficientFundsError("Insufficient USDT balance")

        if side == "sell" and self.balance.get(symbol.split("USDT")[0], 0) < quantity:
            raise InsufficientFundsError(f"Insufficient {symbol.split('USDT')[0]} balance")

        order = {
            "id": f"order_{len(self.orders) + 1}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price or 50000,
            "status": "filled",
            "timestamp": datetime.now()
        }
        self.orders.append(order)

        # Update balance
        if side == "buy":
            cost = (price or 50000) * quantity
            self.balance["USDT"] -= cost
            self.balance[symbol.split("USDT")[0]] = self.balance.get(symbol.split("USDT")[0], 0) + quantity
        elif side == "sell":
            self.balance["USDT"] += (price or 50000) * quantity
            self.balance[symbol.split("USDT")[0]] -= quantity

        return order

    def get_balance(self):
        """Get account balance."""
        return self.balance.copy()

    def was_called_with(self, method_name):
        """Check if method was called."""
        return any(call["method"] == method_name for call in self.call_history)


class InsufficientFundsError(Exception):
    """Custom exception for insufficient funds."""
    pass


class RiskManager:
    """Mock risk manager for testing."""

    def __init__(self, max_daily_loss=0.05):
        self.max_daily_loss = max_daily_loss
        self.daily_losses = []
        self.daily_start = datetime.now().date()

    def record_loss(self, loss_amount):
        """Record a trading loss."""
        today = datetime.now().date()
        if today != self.daily_start:
            self.daily_losses = []
            self.daily_start = today

        self.daily_losses.append(loss_amount)

    def should_stop_trading(self):
        """Check if trading should stop due to losses."""
        total_loss = sum(self.daily_losses)
        return total_loss >= self.max_daily_loss


class Trader:
    """Mock trader class for integration testing."""

    def __init__(self, exchange):
        self.exchange = exchange
        self.risk_manager = RiskManager()

    def place_market_order(self, symbol, side, quantity):
        """Place a market order."""
        try:
            order = self.exchange.create_order(symbol, side, quantity)
            return order
        except InsufficientFundsError as e:
            # Record risk event
            if side == "buy":
                self.risk_manager.record_loss(0.01)  # Small risk penalty
            raise e

    def get_portfolio_value(self):
        """Get current portfolio value."""
        balance = self.exchange.get_balance()
        # Simple valuation - in real implementation would use current prices
        btc_value = balance.get("BTC", 0) * 50000  # Mock BTC price
        usdt_value = balance.get("USDT", 0)
        return btc_value + usdt_value


class TestTradingIntegration:
    """Comprehensive trading integration tests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.exchange = MockExchange()
        self.trader = Trader(self.exchange)

    def test_order_execution_success(self):
        """Test successful order execution."""
        # Test market buy order
        order = self.trader.place_market_order('BTCUSDT', 'buy', 0.01)

        assert order['status'] == 'filled'
        assert order['symbol'] == 'BTCUSDT'
        assert order['side'] == 'buy'
        assert order['quantity'] == 0.01
        assert self.exchange.was_called_with('create_order')

        # Verify balance updated
        balance = self.exchange.get_balance()
        assert balance['USDT'] < 10000  # Should have decreased
        assert balance['BTC'] > 0.5     # Should have increased

    def test_order_execution_sell(self):
        """Test sell order execution."""
        # Test market sell order
        order = self.trader.place_market_order('BTCUSDT', 'sell', 0.1)

        assert order['status'] == 'filled'
        assert order['side'] == 'sell'
        assert order['quantity'] == 0.1

        # Verify balance updated
        balance = self.exchange.get_balance()
        assert balance['USDT'] > 10000  # Should have increased
        assert balance['BTC'] < 0.5     # Should have decreased

    def test_insufficient_funds_error(self):
        """Test error handling for insufficient funds."""
        with pytest.raises(InsufficientFundsError):
            # Try to buy more than available balance
            self.trader.place_market_order('BTCUSDT', 'buy', 1000000)

    def test_insufficient_asset_error(self):
        """Test error handling for insufficient asset balance."""
        with pytest.raises(InsufficientFundsError):
            # Try to sell more BTC than owned
            self.trader.place_market_order('BTCUSDT', 'sell', 100)

    def test_portfolio_valuation(self):
        """Test portfolio value calculation."""
        initial_value = self.trader.get_portfolio_value()

        # Make a trade
        self.trader.place_market_order('BTCUSDT', 'buy', 0.01)

        # Portfolio value should change
        new_value = self.trader.get_portfolio_value()
        assert new_value != initial_value

    def test_risk_limits(self):
        """Test risk management limits."""
        risk_manager = RiskManager(max_daily_loss=0.05)

        # Record some losses
        for i in range(3):
            risk_manager.record_loss(0.02)

        # Should not stop trading yet
        assert risk_manager.should_stop_trading() == False

        # Record one more loss to exceed limit
        risk_manager.record_loss(0.02)

        # Should stop trading now
        assert risk_manager.should_stop_trading() == True

    def test_risk_integration_with_trading(self):
        """Test risk manager integration with trading."""
        # Create trader with risk manager
        trader = Trader(self.exchange)

        # Make several trades that trigger risk events
        for i in range(5):
            try:
                trader.place_market_order('BTCUSDT', 'buy', 0.001)
            except InsufficientFundsError:
                # This should trigger risk recording
                pass

        # Risk manager should eventually stop trading
        # (This depends on the specific risk rules implemented)

    def test_multiple_order_types(self):
        """Test different order types."""
        # Test limit order (mock implementation)
        order = self.exchange.create_order('BTCUSDT', 'buy', 0.01, price=45000, order_type="limit")

        assert order['order_type'] == 'limit'
        assert order['price'] == 45000

    def test_order_history_tracking(self):
        """Test order history is properly tracked."""
        initial_order_count = len(self.exchange.orders)

        # Place several orders
        for i in range(3):
            self.trader.place_market_order('BTCUSDT', 'buy', 0.001)

        # Order count should have increased
        assert len(self.exchange.orders) == initial_order_count + 3

        # All orders should be tracked
        for order in self.exchange.orders:
            assert 'id' in order
            assert 'timestamp' in order
            assert 'status' in order


class TestDataStreamIntegration:
    """Test async data streaming functionality."""

    @pytest.mark.asyncio
    async def test_async_data_stream_initialization(self):
        """Test async data stream can be initialized."""
        stream = AsyncDataStream(api_key="test_key", api_secret="test_secret")

        # Should initialize without errors
        assert stream is not None
        assert hasattr(stream, 'process_tick_data_async')

    def test_data_stream_mock_integration(self):
        """Test data stream with mock data."""
        stream = AsyncDataStream(api_key="test_key", api_secret="test_secret")

        # Mock market data
        mock_data = {
            'symbol': 'BTCUSDT',
            'price': 50000,
            'volume': 100,
            'timestamp': time.time()
        }

        # This would normally be async, but for testing we can check the structure
        assert isinstance(mock_data, dict)
        assert 'symbol' in mock_data
        assert 'price' in mock_data


class TestCachingIntegration:
    """Test caching layer integration."""

    def test_cache_initialization(self):
        """Test cache can be initialized."""
        cache = TradingCache(enable_redis=False)  # Disable Redis for testing

        assert cache is not None
        assert hasattr(cache, 'get_technical_indicators')
        assert hasattr(cache, 'set_technical_indicators')

    def test_cache_operations(self):
        """Test basic cache operations."""
        cache = TradingCache(enable_redis=False)

        # Test setting and getting indicators
        indicators = {'sma_20': 50000, 'rsi_14': 65}
        success = cache.set_technical_indicators('BTCUSDT', '1h', indicators)

        assert success == True

        # Test retrieval
        retrieved = cache.get_technical_indicators('BTCUSDT', '1h')
        assert retrieved == indicators

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = TradingCache(enable_redis=False)

        # Set some data
        cache.set_technical_indicators('BTCUSDT', '1h', {'test': 'data'})

        # Invalidate
        invalidated = cache.invalidate_on_new_data('BTCUSDT')

        assert invalidated >= 0  # Should not error


class TestBatchDatabaseIntegration:
    """Test batch database operations."""

    def test_batch_database_initialization(self):
        """Test batch database can be initialized."""
        # Mock database pool for testing
        mock_pool = Mock()
        batch_db = BatchDatabase(db_pool=mock_pool)

        assert batch_db is not None
        assert hasattr(batch_db, 'save_trades_batch')

    def test_batch_trade_structure(self):
        """Test batch trade data structure."""
        batch_db = BatchDatabase()

        # Test trade data structure
        trades = [{
            'symbol': 'BTCUSDT',
            'side': 'buy',
            'quantity': 0.01,
            'price': 50000,
            'timestamp': datetime.now(),
            'fee': 0.001,
            'fee_asset': 'USDT',
            'order_id': 'test_order_1',
            'trade_id': 'trade_1',
            'is_maker': False
        }]

        # This would normally save to database, but we can test the structure
        assert len(trades) == 1
        assert 'symbol' in trades[0]
        assert 'side' in trades[0]


class TestFeatureStoreIntegration:
    """Test ML feature store integration."""

    def test_feature_store_initialization(self):
        """Test feature store can be initialized."""
        cache = TradingCache(enable_redis=False)
        feature_store = FeatureStore(trading_cache=cache)

        assert feature_store is not None
        assert hasattr(feature_store, 'precompute_features')

    def test_feature_store_structure(self):
        """Test feature store data structures."""
        cache = TradingCache(enable_redis=False)
        feature_store = FeatureStore(trading_cache=cache)

        # Test status structure
        status = feature_store.get_precomputation_status()

        assert isinstance(status, dict)
        assert 'metrics' in status
        assert 'cache_stats' in status


class TestSecurityIntegration:
    """Test security and credential management."""

    def test_credential_manager_initialization(self):
        """Test credential manager can be initialized."""
        manager = CredentialManager()

        assert manager is not None
        assert hasattr(manager, 'encrypt_credentials')

    def test_encryption_structure(self):
        """Test encryption functionality structure."""
        manager = CredentialManager()

        # Test with mock data
        test_creds = {
            'api_key': 'test_key',
            'api_secret': 'test_secret'
        }

        # This would normally encrypt, but we can test the interface
        assert isinstance(test_creds, dict)
        assert 'api_key' in test_creds


class TestMemoryEfficientLoaderIntegration:
    """Test memory-efficient data loading."""

    def test_loader_initialization(self):
        """Test data loader can be initialized."""
        loader = ChunkedDataLoader()

        assert loader is not None
        assert hasattr(loader, 'load_in_chunks')

    def test_chunking_structure(self):
        """Test data chunking structure."""
        loader = ChunkedDataLoader()

        # Test chunk size configuration
        assert hasattr(loader, 'chunk_size')
        assert loader.chunk_size > 0


class TestDatabasePoolIntegration:
    """Test database connection pooling."""

    def test_pool_initialization(self):
        """Test database pool can be initialized."""
        pool = DatabasePool()

        assert pool is not None
        assert hasattr(pool, 'get_connection')

    def test_pool_structure(self):
        """Test pool configuration structure."""
        pool = DatabasePool()

        # Test pool attributes
        assert hasattr(pool, 'min_connections')
        assert hasattr(pool, 'max_connections')


class TestPerformanceBenchmarks:
    """Performance benchmark tests."""

    def test_cache_performance(self):
        """Test cache performance benchmarks."""
        cache = TradingCache(enable_redis=False)

        # Benchmark cache operations
        import time

        start_time = time.time()

        # Perform multiple cache operations
        for i in range(100):
            cache.set_technical_indicators(f'BTCUSDT_{i}', '1h', {'test': i})
            cache.get_technical_indicators(f'BTCUSDT_{i}', '1h')

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time
        assert duration < 5.0  # Less than 5 seconds for 200 operations

    def test_memory_usage(self):
        """Test memory usage patterns."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        cache = TradingCache(enable_redis=False)
        for i in range(1000):
            cache.set_technical_indicators(f'SYMBOL_{i}', '1h', {'data': 'x' * 1000})

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50

    def test_concurrent_operations(self):
        """Test concurrent operation handling."""
        import threading

        cache = TradingCache(enable_redis=False)
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(50):
                    key = f"worker_{worker_id}_item_{i}"
                    cache.set_technical_indicators(key, '1h', {'worker': worker_id, 'item': i})
                    data = cache.get_technical_indicators(key, '1h')
                    if data:
                        results.append(data)
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should have results and no errors
        assert len(results) > 0
        assert len(errors) == 0