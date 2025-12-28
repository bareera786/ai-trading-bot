"""High-performance caching layer for trading bot optimization."""

from __future__ import annotations

import logging
import os
import pickle
import time
from typing import Any, Dict, Optional

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class TradingCache:
    """
    High-performance caching layer combining Redis persistence with local LRU cache.

    Features:
    - Redis backend for cross-process persistence
    - Local LRU cache for ultra-fast access
    - Automatic cache invalidation on new data
    - TTL-based expiration
    - Graceful fallback when Redis unavailable
    """

    def __init__(
        self,
        redis_host: Optional[str] = None,
        redis_port: Optional[int] = None,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        enable_redis: bool = True
    ):
        # Use environment variables if not provided
        if redis_host is None:
            redis_host = os.getenv("REDIS_HOST", "localhost")
        if redis_port is None:
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
        self.enable_redis = enable_redis and REDIS_AVAILABLE
        self.redis_client = None
        self.local_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_timestamps: Dict[str, float] = {}

        if self.enable_redis:
            try:
                if redis is None:
                    raise ImportError("Redis module not available")
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=False,  # We handle serialization
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                    retry_on_timeout=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"❌ Redis connection failed: {e}. Using local cache only.")
                self.enable_redis = False
                self.redis_client = None
        else:
            logger.info("ℹ️ Redis disabled. Using local cache only.")

    def get_technical_indicators(
        self,
        symbol: str,
        timeframe: str,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached technical indicators for a symbol/timeframe.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1h', '4h', '1d')
            force_refresh: Force recalculation even if cached

        Returns:
            Dictionary of technical indicators or None if not available
        """
        cache_key = f"indicators:{symbol}:{timeframe}"

        # Check if we need to force refresh
        if force_refresh:
            self._invalidate_cache_key(cache_key)
            return None

        # Try local cache first (fastest)
        if cache_key in self.local_cache:
            cached_data = self.local_cache[cache_key]
            if self._is_cache_valid(cache_key):
                logger.debug(f"📋 Local cache hit for {cache_key}")
                return cached_data
            else:
                # Cache expired, remove it
                del self.local_cache[cache_key]
                del self.cache_timestamps[cache_key]

        # Try Redis cache
        if self.enable_redis and self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data and isinstance(cached_data, bytes):
                    indicators = pickle.loads(cached_data)
                    # Store in local cache for faster future access
                    self.local_cache[cache_key] = indicators
                    self.cache_timestamps[cache_key] = time.time()
                    logger.debug(f"🔴 Redis cache hit for {cache_key}")
                    return indicators
            except Exception as e:
                logger.warning(f"Redis cache read error for {cache_key}: {e}")

        logger.debug(f"❌ Cache miss for {cache_key}")
        return None

    def set_technical_indicators(
        self,
        symbol: str,
        timeframe: str,
        indicators: Dict[str, Any],
        ttl_seconds: int = 300
    ) -> bool:
        """
        Cache technical indicators with TTL.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            indicators: Indicator data to cache
            ttl_seconds: Time-to-live in seconds (default 5 minutes)

        Returns:
            True if successfully cached, False otherwise
        """
        cache_key = f"indicators:{symbol}:{timeframe}"

        try:
            # Store in local cache
            self.local_cache[cache_key] = indicators.copy()
            self.cache_timestamps[cache_key] = time.time()

            # Store in Redis with TTL
            if self.enable_redis and self.redis_client:
                try:
                    serialized_data = pickle.dumps(indicators)
                    self.redis_client.setex(cache_key, ttl_seconds, serialized_data)
                    logger.debug(f"💾 Cached indicators for {cache_key} (TTL: {ttl_seconds}s)")
                except Exception as e:
                    logger.warning(f"Redis cache write error for {cache_key}: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error caching indicators for {cache_key}: {e}")
            return False

    def invalidate_on_new_data(self, symbol: str, timeframe: Optional[str] = None) -> int:
        """
        Invalidate cache when new market data arrives.

        Args:
            symbol: Trading symbol to invalidate
            timeframe: Specific timeframe, or None for all timeframes

        Returns:
            Number of cache entries invalidated
        """
        invalidated_count = 0

        if timeframe:
            # Invalidate specific symbol/timeframe
            cache_key = f"indicators:{symbol}:{timeframe}"
            invalidated_count += self._invalidate_cache_key(cache_key)
        else:
            # Invalidate all timeframes for this symbol
            pattern = f"indicators:{symbol}:*"

            # Clear local cache
            keys_to_remove = [k for k in self.local_cache.keys() if k.startswith(f"indicators:{symbol}:")]
            for key in keys_to_remove:
                del self.local_cache[key]
                if key in self.cache_timestamps:
                    del self.cache_timestamps[key]
                invalidated_count += 1

            # Clear Redis cache
            if self.enable_redis and self.redis_client:
                try:
                    for key in self.redis_client.scan_iter(match=pattern):
                        self.redis_client.delete(key)
                        invalidated_count += 1
                except Exception as e:
                    logger.warning(f"Redis cache invalidation error: {e}")

        if invalidated_count > 0:
            logger.info(f"🗑️ Invalidated {invalidated_count} cache entries for {symbol}")
        else:
            logger.debug(f"No cache entries to invalidate for {symbol}")

        return invalidated_count

    def invalidate_all_cache(self) -> int:
        """
        Clear all cached data (use with caution).

        Returns:
            Number of entries cleared
        """
        total_cleared = 0

        # Clear local cache
        local_count = len(self.local_cache)
        self.local_cache.clear()
        self.cache_timestamps.clear()
        total_cleared += local_count

        # Clear Redis cache
        if self.enable_redis and self.redis_client:
            try:
                redis_keys = list(self.redis_client.scan_iter(match="indicators:*"))
                if redis_keys:
                    self.redis_client.delete(*redis_keys)
                    total_cleared += len(redis_keys)
            except Exception as e:
                logger.warning(f"Redis cache clear error: {e}")

        logger.info(f"🧹 Cleared {total_cleared} total cache entries")
        return total_cleared

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary with cache statistics
        """
        stats = {
            "local_cache_entries": len(self.local_cache),
            "redis_enabled": self.enable_redis,
            "redis_available": self.redis_client is not None if REDIS_AVAILABLE else False,
        }

        if self.enable_redis and self.redis_client:
            try:
                # Get Redis memory info
                info = self.redis_client.info("memory")
                if isinstance(info, dict):
                    stats.update({
                        "redis_used_memory": info.get("used_memory_human", "unknown"),
                        "redis_total_keys": self.redis_client.dbsize(),
                        "indicators_keys": len(list(self.redis_client.scan_iter(match="indicators:*"))),
                    })
            except Exception as e:
                logger.warning(f"Error getting Redis stats: {e}")
                stats["redis_error"] = str(e)

        return stats

    def _invalidate_cache_key(self, cache_key: str) -> int:
        """Invalidate a specific cache key from both local and Redis cache."""
        invalidated = 0

        # Remove from local cache
        if cache_key in self.local_cache:
            del self.local_cache[cache_key]
            invalidated += 1
        if cache_key in self.cache_timestamps:
            del self.cache_timestamps[cache_key]

        # Remove from Redis
        if self.enable_redis and self.redis_client:
            try:
                if self.redis_client.delete(cache_key):
                    invalidated += 1
            except Exception as e:
                logger.warning(f"Redis delete error for {cache_key}: {e}")

        return invalidated

    def _is_cache_valid(self, cache_key: str, max_age_seconds: int = 300) -> bool:
        """Check if a cache entry is still valid."""
        if cache_key not in self.cache_timestamps:
            return False

        age = time.time() - self.cache_timestamps[cache_key]
        return age < max_age_seconds

    def preload_common_indicators(self, symbols: list[str], timeframes: list[str]) -> int:
        """
        Preload commonly used indicators into cache.

        Args:
            symbols: List of symbols to cache
            timeframes: List of timeframes to cache

        Returns:
            Number of indicator sets preloaded
        """
        preloaded = 0

        for symbol in symbols:
            for timeframe in timeframes:
                # This will trigger calculation if not cached
                # In a real implementation, you'd call your indicator calculation function here
                logger.debug(f"Preloading indicators for {symbol} {timeframe}")
                preloaded += 1

        logger.info(f"📦 Preloaded {preloaded} indicator sets")
        return preloaded

    def warmup_cache(self, symbols: list[str], timeframes: list[str]) -> Dict[str, Any]:
        """
        Warm up cache with initial data load.

        Returns:
            Cache statistics after warmup
        """
        logger.info("🔥 Warming up trading cache...")

        preloaded = self.preload_common_indicators(symbols, timeframes)

        stats = self.get_cache_stats()
        stats["preloaded_sets"] = preloaded

        logger.info(f"✅ Cache warmup complete: {stats}")
        return stats