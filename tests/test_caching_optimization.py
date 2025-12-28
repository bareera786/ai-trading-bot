"""Tests for caching layer optimization."""

import pytest
import time
from unittest.mock import Mock, patch

from app.cache.trading_cache import TradingCache


class TestTradingCache:
    """Test the trading cache functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = TradingCache(enable_redis=False)

    def test_cache_initialization(self):
        """Test cache initializes correctly."""
        assert self.cache is not None
        assert hasattr(self.cache, 'get_technical_indicators')
        assert hasattr(self.cache, 'set_technical_indicators')
        assert hasattr(self.cache, 'invalidate_on_new_data')

    def test_set_and_get_indicators(self):
        """Test setting and getting technical indicators."""
        symbol = "BTCUSDT"
        timeframe = "1h"
        indicators = {
            "sma_20": 45000.5,
            "rsi_14": 65.2,
            "macd_line": 123.4,
            "bb_upper": 47000.0
        }

        # Set indicators
        success = self.cache.set_technical_indicators(symbol, timeframe, indicators)
        assert success is True

        # Get indicators
        retrieved = self.cache.get_technical_indicators(symbol, timeframe)
        assert retrieved == indicators

    def test_cache_miss(self):
        """Test cache miss behavior."""
        retrieved = self.cache.get_technical_indicators("NONEXISTENT", "1h")
        assert retrieved is None

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        symbol = "BTCUSDT"
        timeframe = "1h"
        indicators = {"test": "data"}

        # Set data
        self.cache.set_technical_indicators(symbol, timeframe, indicators)

        # Verify it's cached
        retrieved = self.cache.get_technical_indicators(symbol, timeframe)
        assert retrieved == indicators

        # Invalidate
        invalidated = self.cache.invalidate_on_new_data(symbol)
        assert invalidated >= 0

        # Should be gone after invalidation
        retrieved = self.cache.get_technical_indicators(symbol, timeframe)
        assert retrieved is None

    def test_cache_ttl_behavior(self):
        """Test TTL behavior (simulated)."""
        symbol = "BTCUSDT"
        timeframe = "1h"
        indicators = {"test": "data"}

        # Set with short TTL (this is simulated since we're not using Redis)
        success = self.cache.set_technical_indicators(symbol, timeframe, indicators, ttl_seconds=1)
        assert success is True

        # Should still be available immediately
        retrieved = self.cache.get_technical_indicators(symbol, timeframe)
        assert retrieved == indicators

    def test_force_refresh(self):
        """Test force refresh functionality."""
        symbol = "BTCUSDT"
        timeframe = "1h"
        old_indicators = {"old": "data"}
        new_indicators = {"new": "data"}

        # Set initial data
        self.cache.set_technical_indicators(symbol, timeframe, old_indicators)

        # Get with force refresh should return None (simulating recalculation needed)
        retrieved = self.cache.get_technical_indicators(symbol, timeframe, force_refresh=True)
        assert retrieved is None

    def test_cache_statistics(self):
        """Test cache statistics reporting."""
        stats = self.cache.get_cache_stats()

        assert isinstance(stats, dict)
        assert "local_cache_entries" in stats
        assert "redis_enabled" in stats

    def test_multiple_symbols_timeframes(self):
        """Test caching multiple symbols and timeframes."""
        test_data = [
            ("BTCUSDT", "1h", {"btc_1h": "data"}),
            ("ETHUSDT", "1h", {"eth_1h": "data"}),
            ("BTCUSDT", "4h", {"btc_4h": "data"}),
            ("ETHUSDT", "4h", {"eth_4h": "data"}),
        ]

        # Set all data
        for symbol, timeframe, indicators in test_data:
            self.cache.set_technical_indicators(symbol, timeframe, indicators)

        # Verify all can be retrieved
        for symbol, timeframe, expected_indicators in test_data:
            retrieved = self.cache.get_technical_indicators(symbol, timeframe)
            assert retrieved == expected_indicators

    def test_cache_performance(self):
        """Test cache performance under load."""
        import time

        # Performance test with many operations
        start_time = time.time()

        # Perform many cache operations
        for i in range(100):
            symbol = f"SYMBOL_{i}"
            timeframe = "1h"
            indicators = {"value": i}

            self.cache.set_technical_indicators(symbol, timeframe, indicators)
            retrieved = self.cache.get_technical_indicators(symbol, timeframe)

            assert retrieved == indicators

        end_time = time.time()
        duration = end_time - start_time

        # Should complete quickly (less than 1 second for 200 operations)
        assert duration < 1.0

    @patch('app.cache.trading_cache.redis')
    def test_redis_fallback(self, mock_redis):
        """Test Redis fallback behavior."""
        # Mock Redis import failure
        mock_redis.Redis.side_effect = ImportError("Redis not available")

        cache = TradingCache(enable_redis=True)

        # Should fallback to local cache
        assert cache.enable_redis is False
        assert cache.redis_client is None

        # Should still work
        success = cache.set_technical_indicators("BTCUSDT", "1h", {"test": "data"})
        assert success is True

    def test_warmup_functionality(self):
        """Test cache warmup functionality."""
        symbols = ["BTCUSDT", "ETHUSDT"]
        timeframes = ["1h", "4h"]

        # This would normally preload data, but we can test the interface
        stats = self.cache.warmup_cache(symbols, timeframes)

        assert isinstance(stats, dict)
        assert "preloaded_sets" in stats

    def test_memory_efficiency(self):
        """Test memory efficiency of cache."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Add many cache entries
        for i in range(1000):
            self.cache.set_technical_indicators(f"SYMBOL_{i}", "1h", {"data": f"value_{i}"})

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable
        # Allow some increase for the test data
        assert memory_increase < 100  # Less than 100MB increase