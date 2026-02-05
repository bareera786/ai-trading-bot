import multiprocessing
import threading
import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
from cachetools import TTLCache
from joblib import Parallel, delayed
from app.services import get_real_market_data

class ParallelPredictionEngine:
    def __init__(self):
        # provide a logger to avoid attribute errors when methods call self.logger
        self.logger = logging.getLogger(__name__)
        self.num_cores = multiprocessing.cpu_count()
        self.max_workers = 8 # Increased to support multi-symbol trading (was 2)
        self.parallel_backend = "threading"
        self.logger.info(
            f"🚀 Parallel Prediction Engine Initialized with {self.num_cores} cores"
            f" (using up to {self.max_workers} {self.parallel_backend} workers)"
        )

    def parallel_predict(self, symbols, market_data, ml_system):
        """Optimized parallel prediction using performance optimizer"""
        try:
            return performance_optimizer.optimized_parallel_predict(
                symbols, market_data, ml_system
            )
        except Exception as e:
            # Fallback to original implementation
            return self.sequential_predict(symbols, market_data, ml_system)

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop("logger", None)
        return state

    def __reduce__(self):
        # When this module is reloaded in-process (e.g., across a large test run),
        # instances created from an older class object can fail default pickling.
        # Reconstruct via the current module-level class.
        from app.ml.components.parallel import ParallelPredictionEngine as Current

        return (Current, (), self.__getstate__())

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.logger = logging.getLogger(__name__)

    def sequential_predict(self, symbols, market_data, ml_system):
        """Sequential fallback prediction"""
        predictions = {}
        for symbol in symbols:
            if symbol in market_data:
                pred = ml_system.predict_professional(symbol, market_data[symbol])
                if pred:
                    predictions[symbol] = pred
        return predictions

    def parallel_train_models(self, symbols, ml_system, use_real_data=True):
        """Optimized parallel training using performance optimizer"""
        try:
            return performance_optimizer.optimized_parallel_train(
                symbols, ml_system, use_real_data
            )
        except Exception as e:
            # Fallback to sequential training
            return self._sequential_train_models(symbols, ml_system, use_real_data)

    def _sequential_train_models(self, symbols, ml_system, use_real_data):
        """Sequential fallback for training when parallel execution fails"""
        success_count = 0
        for symbol in symbols:
            try:
                success = ml_system.train_advanced_model(
                    symbol, use_real_data=use_real_data
                )
                if success:
                    success_count += 1
            except Exception as e:
                print(f"❌ Sequential training failed for {symbol}: {e}")
        print(
            f"✅ Sequential training completed: {success_count}/{len(symbols)} successful"
        )
        return success_count


class PerformanceOptimizer:
    """Advanced performance optimization system with caching and async processing"""

    def __init__(self, max_workers=None, cache_ttl=300):
        self.max_workers = max_workers or 4 # Hard cap to 4 threads (was up to 32)
        self.cache_ttl = cache_ttl

        # ML prediction cache (5 minute TTL)
        self.prediction_cache = TTLCache(maxsize=1000, ttl=cache_ttl)

        # Market data cache (30 second TTL)
        self.market_data_cache = TTLCache(maxsize=500, ttl=30)

        # Feature computation cache (10 minute TTL)
        self.feature_cache = TTLCache(maxsize=2000, ttl=600)

        # Thread pools for different workloads
        self.cpu_executor = ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="cpu_worker"
        )
        self.io_executor = ThreadPoolExecutor(
            max_workers=min(16, self.max_workers), thread_name_prefix="io_worker"
        )

        # Async event loop for non-blocking operations
        self.loop = asyncio.new_event_loop()
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()

    def _run_event_loop(self):
        """Run async event loop in background thread"""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _cache_key(self, *args, **kwargs):
        """Generate cache key from function arguments"""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    def cached_predict(self, symbol, market_data, ml_system):
        """Cached ML prediction to avoid redundant computations"""
        return ml_system.predict_professional(symbol, market_data)

    def cached_market_data(self, symbol):
        """Cached market data retrieval"""
        # This would integrate with your market data service
        return get_real_market_data(symbol)

    def cached_feature_computation(self, df, symbol):
        """Cached feature computation for training data"""
        return self.compute_training_features(df)  # type: ignore

    async def async_predict_batch(self, symbols, market_data, ml_system):
        """Async batch prediction with caching"""
        tasks = []
        for symbol in symbols:
            if symbol in market_data:
                task = self.loop.run_in_executor(
                    self.cpu_executor,
                    self.cached_predict,
                    symbol,
                    market_data[symbol],
                    ml_system,
                )
                tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            predictions = {}
            for i, result in enumerate(results):
                symbol = symbols[i]
                if not isinstance(result, Exception):
                    predictions[symbol] = result
            return predictions
        return {}

    def optimized_parallel_predict(self, symbols, market_data, ml_system):
        """Optimized parallel prediction with caching and async processing"""
        try:
            # Try async processing first
            future = asyncio.run_coroutine_threadsafe(
                self.async_predict_batch(symbols, market_data, ml_system), self.loop
            )
            return future.result(timeout=30)  # 30 second timeout
        except Exception:
            # Fallback to cached parallel processing
            return self._fallback_parallel_predict(symbols, market_data, ml_system)

    def _fallback_parallel_predict(self, symbols, market_data, ml_system):
        """Fallback parallel prediction with caching"""

        def predict_single(symbol):
            try:
                if symbol in market_data:
                    return symbol, self.cached_predict(
                        symbol, market_data[symbol], ml_system
                    )
                return symbol, None
            except Exception as e:
                return symbol, None

        results = Parallel(n_jobs=self.max_workers, backend="threading")(
            delayed(predict_single)(symbol) for symbol in symbols
        )

        return {symbol: pred for symbol, pred in results or [] if pred is not None}  # type: ignore

    def optimized_parallel_train(self, symbols, ml_system, use_real_data=True):
        """Optimized parallel training with resource management"""

        def train_single(symbol):
            try:
                # Use cached features if available
                success = ml_system.train_advanced_model(
                    symbol, use_real_data=use_real_data
                )
                return symbol, success
            except Exception as e:
                return symbol, False

        results = Parallel(
            n_jobs=min(self.max_workers, len(symbols)), backend="threading"
        )(delayed(train_single)(symbol) for symbol in symbols)

        success_count = sum(1 for _, success in results or [] if success)  # type: ignore
        return success_count

    def preload_market_data(self, symbols):
        """Preload market data for symbols to reduce latency"""

        def load_single(symbol):
            try:
                return self.cached_market_data(symbol)
            except Exception:
                return None

        Parallel(n_jobs=min(8, len(symbols)), backend="threading")(
            delayed(load_single)(symbol) for symbol in symbols
        )

    def get_cache_stats(self):
        """Get cache performance statistics"""
        return {
            "prediction_cache": {
                "size": len(self.prediction_cache),
                "maxsize": self.prediction_cache.maxsize,
                "ttl": self.prediction_cache.ttl,
            },
            "market_data_cache": {
                "size": len(self.market_data_cache),
                "maxsize": self.market_data_cache.maxsize,
                "ttl": self.market_data_cache.ttl,
            },
            "feature_cache": {
                "size": len(self.feature_cache),
                "maxsize": self.feature_cache.maxsize,
                "ttl": self.feature_cache.ttl,
            },
        }


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()
