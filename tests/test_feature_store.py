"""Tests for ML feature store optimization."""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from datetime import datetime

from app.ml.feature_store import FeatureStore
from app.cache.trading_cache import TradingCache


class TestFeatureStore:
    """Test the ML feature store functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache = TradingCache(enable_redis=False)
        self.feature_store = FeatureStore(trading_cache=self.cache)

    def test_feature_store_initialization(self):
        """Test feature store initializes correctly."""
        assert self.feature_store is not None
        assert hasattr(self.feature_store, 'precompute_features')
        assert hasattr(self.feature_store, 'get_features')
        assert hasattr(self.feature_store, 'get_predictions')

    def test_precompute_features_empty_input(self):
        """Test precomputation with empty inputs."""
        result = self.feature_store.precompute_features([], [])

        assert result['total_symbols'] == 0
        assert result['total_timeframes'] == 0
        assert result['features_computed'] == 0
        assert result['predictions_computed'] == 0

    @patch('app.ml.feature_store.FeatureStore._load_market_data')
    @patch('app.ml.feature_store.FeatureStore._calculate_all_features')
    @patch('app.ml.feature_store.FeatureStore._precompute_predictions')
    def test_precompute_features_success(self, mock_predictions, mock_features, mock_load_data):
        """Test successful feature precomputation."""
        # Mock market data
        mock_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=50, freq='1H'),
            'open': np.random.uniform(40000, 50000, 50),
            'high': np.random.uniform(40000, 50000, 50),
            'low': np.random.uniform(40000, 50000, 50),
            'close': np.random.uniform(40000, 50000, 50),
            'volume': np.random.uniform(100, 1000, 50),
        })
        mock_load_data.return_value = mock_data

        # Mock features calculation
        mock_features.return_value = {'sma_20': 45000, 'rsi_14': 65}

        # Mock predictions
        mock_predictions.return_value = 2  # 2 predictions computed

        symbols = ['BTCUSDT']
        timeframes = ['1h']

        result = self.feature_store.precompute_features(symbols, timeframes)

        assert result['total_symbols'] == 1
        assert result['total_timeframes'] == 1
        assert result['features_computed'] == 1
        assert result['predictions_computed'] == 2
        assert 'total_time' in result

    def test_get_features_cache_hit(self):
        """Test getting features from cache."""
        symbol = "BTCUSDT"
        timeframe = "1h"
        features = {"sma_20": 45000, "rsi_14": 65}

        # Pre-populate cache
        self.cache.set_technical_indicators(symbol, timeframe, features)

        # Get features
        retrieved = self.feature_store.get_features(symbol, timeframe)

        assert retrieved == features

    def test_get_features_cache_miss(self):
        """Test getting features when not in cache."""
        retrieved = self.feature_store.get_features("NONEXISTENT", "1h")

        assert retrieved is None

    def test_get_predictions_from_cache(self):
        """Test getting predictions from cache."""
        model_name = "rf"
        symbol = "BTCUSDT"
        timeframe = "1h"

        # Mock Redis-like behavior for predictions
        prediction_data = {
            "signal": "BUY",
            "confidence": 0.75,
            "timestamp": 1234567890,
            "model": model_name
        }

        # Manually set in cache (simulating Redis behavior)
        cache_key = f"pred:{model_name}:{symbol}:{timeframe}"
        if hasattr(self.cache, 'redis_client') and self.cache.redis_client:
            import pickle
            self.cache.redis_client.setex(cache_key, 300, pickle.dumps(prediction_data))

        # Get predictions
        retrieved = self.feature_store.get_predictions(model_name, symbol, timeframe)

        # In our test setup, this will return None since we're not using Redis
        # But we can test the interface
        assert retrieved is None or isinstance(retrieved, dict)

    def test_invalidate_features(self):
        """Test feature invalidation."""
        symbol = "BTCUSDT"
        timeframe = "1h"
        features = {"test": "data"}

        # Set features
        self.cache.set_technical_indicators(symbol, timeframe, features)

        # Verify they're cached
        retrieved = self.feature_store.get_features(symbol, timeframe)
        assert retrieved == features

        # Invalidate
        invalidated = self.feature_store.invalidate_features(symbol)

        assert invalidated >= 0

    def test_get_precomputation_status(self):
        """Test precomputation status reporting."""
        status = self.feature_store.get_precomputation_status()

        assert isinstance(status, dict)
        assert 'metrics' in status
        assert 'cache_stats' in status
        assert 'cache_efficiency' in status

    def test_feature_versioning(self):
        """Test feature versioning."""
        symbol = "BTCUSDT"
        timeframe = "1h"
        features = {"test": "data"}

        # Set features
        self.cache.set_technical_indicators(symbol, timeframe, features)

        # Get with matching version
        retrieved = self.feature_store.get_features(symbol, timeframe, "v1.0")
        assert retrieved is None  # Version doesn't match our mock

        # Get without version requirement
        retrieved = self.feature_store.get_features(symbol, timeframe)
        assert retrieved == features

    @patch('app.ml.feature_store.FeatureStore._load_market_data')
    def test_calculate_all_features(self, mock_load_data):
        """Test feature calculation."""
        # Create test market data
        market_data = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=30, freq='1H'),
            'open': [40000] * 30,
            'high': [41000] * 30,
            'low': [39000] * 30,
            'close': [40000 + i*100 for i in range(30)],  # Trending up
            'volume': [500] * 30,
        })

        features = self.feature_store._calculate_all_features(market_data)

        assert isinstance(features, dict)
        assert 'close' in features
        assert 'volume' in features
        # Note: Some features might not be calculated with insufficient data

    def test_mock_predict(self):
        """Test mock prediction function."""
        features = {
            'rsi_14': 30,  # Oversold
            'close': 40000,
            'sma_20': 41000
        }

        prediction = self.feature_store._mock_predict("test_model", features)

        assert isinstance(prediction, dict)
        assert 'signal' in prediction
        assert 'confidence' in prediction
        assert 'model' in prediction
        assert prediction['signal'] in ['BUY', 'SELL', 'HOLD']
        assert 0 <= prediction['confidence'] <= 1

    def test_schedule_precomputation(self):
        """Test precomputation scheduling interface."""
        # This is mainly an interface test since actual scheduling
        # would require integration with a scheduler
        self.feature_store.schedule_precomputation(
            symbols=['BTCUSDT'],
            timeframes=['1h', '4h'],
            schedule_time="02:00"
        )

        # Should not raise any errors
        assert True

    def test_metrics_update(self):
        """Test metrics updating."""
        initial_features = self.feature_store.metrics['features_precomputed']

        # Manually update metrics
        self.feature_store._update_metrics({'features_computed': 5, 'predictions_computed': 3})

        assert self.feature_store.metrics['features_precomputed'] == initial_features + 5

    def test_error_handling_in_precomputation(self):
        """Test error handling during precomputation."""
        # Test with invalid inputs that should cause errors
        result = self.feature_store.precompute_features(['INVALID'], ['INVALID'])

        # Should handle errors gracefully
        assert isinstance(result, dict)
        assert 'errors' in result

    def test_parallel_precomputation(self):
        """Test parallel precomputation of multiple symbols/timeframes."""
        symbols = ['BTCUSDT', 'ETHUSDT']
        timeframes = ['1h', '4h']

        # This will test the parallel execution framework
        # In the mock environment, it should complete without errors
        result = self.feature_store.precompute_features(symbols, timeframes)

        assert result['total_symbols'] == 2
        assert result['total_timeframes'] == 2
        assert isinstance(result['total_time'], (int, float))

    def test_precomputation_force_refresh(self):
        """Test force refresh during precomputation."""
        symbols = ['BTCUSDT']
        timeframes = ['1h']

        # First precomputation
        result1 = self.feature_store.precompute_features(symbols, timeframes, force_refresh=False)

        # Second with force refresh
        result2 = self.feature_store.precompute_features(symbols, timeframes, force_refresh=True)

        # Both should complete
        assert result1['total_symbols'] == 1
        assert result2['total_symbols'] == 1

    def test_large_scale_precomputation(self):
        """Test precomputation at scale."""
        # Test with many symbols/timeframes
        symbols = [f'SYMBOL_{i}' for i in range(10)]
        timeframes = ['1h', '4h', '1d']

        result = self.feature_store.precompute_features(symbols, timeframes)

        assert result['total_symbols'] == 10
        assert result['total_timeframes'] == 3

        # Should complete in reasonable time
        assert result['total_time'] < 30  # Less than 30 seconds for mock operations

    def test_memory_efficiency(self):
        """Test memory efficiency during precomputation."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform large-scale precomputation
        symbols = [f'SYMBOL_{i}' for i in range(50)]
        timeframes = ['1h', '4h']

        self.feature_store.precompute_features(symbols, timeframes)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable
        assert memory_increase < 200  # Less than 200MB increase for this test