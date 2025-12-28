"""Precomputed ML feature store for high-performance trading."""

from __future__ import annotations

import logging
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ..cache.trading_cache import TradingCache

logger = logging.getLogger(__name__)


class FeatureStore:
    """
    Precomputed ML feature store for high-performance trading.

    Features:
    - Precompute features during off-peak hours
    - Cache features and predictions in Redis
    - Parallel processing for multiple symbols/timeframes
    - Feature versioning and invalidation
    - Performance monitoring and optimization
    """

    def __init__(self, trading_cache: Optional[TradingCache] = None):
        self.trading_cache = trading_cache or TradingCache()
        self.feature_cache: Dict[str, Dict[str, Any]] = {}
        self.prediction_cache: Dict[str, Dict[str, Any]] = {}
        self.feature_versions: Dict[str, str] = {}  # Track feature versions
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.metrics: Dict[str, Union[int, float]] = {
            "features_precomputed": 0,
            "predictions_precomputed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "computation_time": 0.0,
        }

    def precompute_features(
        self,
        symbols: List[str],
        timeframes: List[str],
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Precompute features for multiple symbols and timeframes.

        Args:
            symbols: List of trading symbols
            timeframes: List of timeframes
            force_refresh: Force recomputation even if cached

        Returns:
            Precomputation results and performance metrics
        """
        start_time = time.time()
        results: Dict[str, Union[int, float]] = {
            "total_symbols": len(symbols),
            "total_timeframes": len(timeframes),
            "features_computed": 0,
            "predictions_computed": 0,
            "cache_hits": 0,
            "errors": 0,
            "total_time": 0.0,
            "rate": 0.0,
        }

        logger.info(f"🚀 Starting feature precomputation for {len(symbols)} symbols × {len(timeframes)} timeframes")

        # Submit all tasks to thread pool
        futures = []
        for symbol in symbols:
            for timeframe in timeframes:
                future = self.executor.submit(
                    self._precompute_symbol_timeframe,
                    symbol,
                    timeframe,
                    force_refresh
                )
                futures.append((symbol, timeframe, future))

        # Collect results
        for symbol, timeframe, future in futures:
            try:
                result = future.result(timeout=300)  # 5 minute timeout
                results["features_computed"] += result.get("features_computed", 0)
                results["predictions_computed"] += result.get("predictions_computed", 0)
                results["cache_hits"] += result.get("cache_hit", 0)

                if result.get("error"):
                    results["errors"] += 1

            except Exception as e:
                logger.error(f"❌ Precomputation failed for {symbol} {timeframe}: {e}")
                results["errors"] += 1

        elapsed = time.time() - start_time
        results["total_time"] = elapsed
        results["rate"] = (results["features_computed"] + results["predictions_computed"]) / elapsed if elapsed > 0 else 0

        self._update_metrics(results)

        logger.info(f"✅ Feature precomputation completed in {elapsed:.1f}s: "
                   f"{results['features_computed']} features, {results['predictions_computed']} predictions")

        return results

    def get_features(
        self,
        symbol: str,
        timeframe: str,
        feature_version: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get precomputed features for a symbol/timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            feature_version: Specific feature version (optional)

        Returns:
            Precomputed features or None if not available
        """
        cache_key = f"features:{symbol}:{timeframe}"

        # Check version compatibility
        if feature_version and self.feature_versions.get(cache_key) != feature_version:
            logger.debug(f"Version mismatch for {cache_key}: requested {feature_version}, have {self.feature_versions.get(cache_key)}")
            return None

        # Try cache first
        cached = self.trading_cache.get_technical_indicators(symbol, timeframe)
        if cached:
            self.metrics["cache_hits"] += 1
            return cached

        self.metrics["cache_misses"] += 1
        return None

    def get_predictions(
        self,
        model_name: str,
        symbol: str,
        timeframe: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get precomputed predictions for a model/symbol/timeframe.

        Args:
            model_name: ML model name
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            Precomputed predictions or None if not available
        """
        cache_key = f"pred:{model_name}:{symbol}:{timeframe}"

        # Try Redis cache
        try:
            if hasattr(self.trading_cache, 'redis_client') and self.trading_cache.redis_client:
                cached_data = self.trading_cache.redis_client.get(cache_key)
                if cached_data and isinstance(cached_data, bytes):
                    predictions = pickle.loads(cached_data)
                    logger.debug(f"📋 Retrieved cached predictions for {model_name}:{symbol}:{timeframe}")
                    return predictions
        except Exception as e:
            logger.warning(f"Redis prediction cache error: {e}")

        return None

    def invalidate_features(self, symbol: Optional[str] = None, timeframe: Optional[str] = None) -> int:
        """
        Invalidate cached features.

        Args:
            symbol: Specific symbol to invalidate (None for all)
            timeframe: Specific timeframe to invalidate (None for all)

        Returns:
            Number of cache entries invalidated
        """
        invalidated = 0

        if symbol:
            invalidated += self.trading_cache.invalidate_on_new_data(symbol, timeframe)
        else:
            # Invalidate all features
            try:
                if hasattr(self.trading_cache, 'redis_client') and self.trading_cache.redis_client:
                    pattern = "features:*" if not timeframe else f"features:*:{timeframe}"
                    keys = list(self.trading_cache.redis_client.scan_iter(match=pattern))
                    if keys:
                        self.trading_cache.redis_client.delete(*keys)
                        invalidated += len(keys)
            except Exception as e:
                logger.warning(f"Feature invalidation error: {e}")

        if invalidated > 0:
            logger.info(f"🗑️ Invalidated {invalidated} feature cache entries")

        return invalidated

    def get_precomputation_status(self) -> Dict[str, Any]:
        """
        Get current precomputation status and coverage.

        Returns:
            Status information
        """
        status = {
            "metrics": self.metrics.copy(),
            "cache_stats": self.trading_cache.get_cache_stats() if self.trading_cache else {},
            "feature_versions": self.feature_versions.copy(),
        }

        # Calculate cache efficiency
        total_requests = status["metrics"]["cache_hits"] + status["metrics"]["cache_misses"]
        if total_requests > 0:
            status["cache_efficiency"] = status["metrics"]["cache_hits"] / total_requests
        else:
            status["cache_efficiency"] = 0

        return status

    def _precompute_symbol_timeframe(
        self,
        symbol: str,
        timeframe: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Precompute features and predictions for a single symbol/timeframe.

        Returns:
            Computation results
        """
        result = {
            "features_computed": 0,
            "predictions_computed": 0,
            "cache_hit": 0,
            "error": None,
        }

        try:
            # Check if already cached and not forcing refresh
            if not force_refresh:
                existing_features = self.get_features(symbol, timeframe)
                if existing_features:
                    result["cache_hit"] = 1
                    return result

            # Load market data
            market_data = self._load_market_data(symbol, timeframe)
            if market_data is None or len(market_data) < 50:  # Minimum data requirement
                result["error"] = "Insufficient market data"
                return result

            # Compute features
            features = self._calculate_all_features(market_data)
            if features:
                # Cache features
                success = self.trading_cache.set_technical_indicators(
                    symbol, timeframe, features, ttl_seconds=3600  # 1 hour
                )
                if success:
                    result["features_computed"] = 1
                    self.feature_versions[f"features:{symbol}:{timeframe}"] = self._get_feature_version()

            # Precompute predictions for common models
            predictions_computed = self._precompute_predictions(symbol, timeframe, features)
            result["predictions_computed"] = predictions_computed

        except Exception as e:
            logger.error(f"Feature precomputation error for {symbol} {timeframe}: {e}")
            result["error"] = str(e)

        return result

    def _load_market_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Load market data for feature computation.

        In a real implementation, this would load from database or API.
        """
        try:
            # Placeholder - in real implementation, load from database
            # For now, return mock data structure
            return pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=100, freq='1H'),
                'open': np.random.uniform(40000, 50000, 100),
                'high': np.random.uniform(40000, 50000, 100),
                'low': np.random.uniform(40000, 50000, 100),
                'close': np.random.uniform(40000, 50000, 100),
                'volume': np.random.uniform(100, 1000, 100),
            })
        except Exception as e:
            logger.error(f"Error loading market data for {symbol} {timeframe}: {e}")
            return None

    def _calculate_all_features(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate all technical features from market data.

        This is a simplified version - in practice, this would use
        the IncrementalIndicatorCalculator for efficiency.
        """
        try:
            features = {}

            # Basic price features
            features['close'] = market_data['close'].iloc[-1]
            features['volume'] = market_data['volume'].iloc[-1]
            features['returns'] = market_data['close'].pct_change().iloc[-1]

            # Simple moving averages
            for period in [5, 10, 20, 50]:
                if len(market_data) >= period:
                    features[f'sma_{period}'] = market_data['close'].rolling(period).mean().iloc[-1]

            # RSI (simplified)
            if len(market_data) >= 14:
                delta = market_data['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                features['rsi_14'] = 100 - (100 / (1 + rs)).iloc[-1]

            # Volatility
            features['volatility'] = market_data['close'].pct_change().rolling(20).std().iloc[-1]

            return features

        except Exception as e:
            logger.error(f"Error calculating features: {e}")
            return {}

    def _precompute_predictions(
        self,
        symbol: str,
        timeframe: str,
        features: Dict[str, Any]
    ) -> int:
        """
        Precompute predictions for common models.

        Returns:
            Number of predictions computed
        """
        if not features:
            return 0

        computed = 0
        model_names = ['rf', 'gb', 'ensemble']

        for model_name in model_names:
            try:
                # Mock prediction - in real implementation, load actual models
                prediction = self._mock_predict(model_name, features)

                # Cache prediction
                cache_key = f"pred:{model_name}:{symbol}:{timeframe}"
                if hasattr(self.trading_cache, 'redis_client') and self.trading_cache.redis_client:
                    serialized = pickle.dumps(prediction)
                    self.trading_cache.redis_client.setex(cache_key, 300, serialized)  # 5 minutes
                    computed += 1

            except Exception as e:
                logger.warning(f"Prediction precomputation failed for {model_name}: {e}")

        return computed

    def _mock_predict(self, model_name: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock prediction function.

        In real implementation, this would load and use actual ML models.
        """
        # Generate mock prediction based on features
        base_signal = np.random.random()

        # Bias based on some features
        if features.get('rsi_14', 50) < 30:
            base_signal += 0.3  # Oversold bias
        elif features.get('rsi_14', 50) > 70:
            base_signal -= 0.3  # Overbought bias

        return {
            'signal': 'BUY' if base_signal > 0.6 else 'SELL' if base_signal < 0.4 else 'HOLD',
            'confidence': min(abs(base_signal - 0.5) * 2, 1.0),
            'timestamp': time.time(),
            'model': model_name,
        }

    def _get_feature_version(self) -> str:
        """Get current feature version for cache invalidation."""
        return "v1.0"  # In real implementation, this would be dynamic

    def _update_metrics(self, results: Dict[str, Any]):
        """Update internal metrics."""
        self.metrics["features_precomputed"] += int(results.get("features_computed", 0))
        self.metrics["predictions_precomputed"] += int(results.get("predictions_computed", 0))
        self.metrics["computation_time"] += float(results.get("total_time", 0))

    def schedule_precomputation(
        self,
        symbols: List[str],
        timeframes: List[str],
        schedule_time: str = "02:00"  # 2 AM daily
    ):
        """
        Schedule regular precomputation during off-peak hours.

        Args:
            symbols: Symbols to precompute
            timeframes: Timeframes to precompute
            schedule_time: Time to run precomputation (HH:MM format)
        """
        # In a real implementation, this would integrate with a scheduler
        # For now, just log the schedule
        logger.info(f"📅 Precomputation scheduled for {schedule_time} daily: "
                   f"{len(symbols)} symbols × {len(timeframes)} timeframes")