import time
import threading
from collections import deque
import psutil

class PerformanceMonitor:
    """Real-time performance monitoring and metrics collection"""

    def __init__(self):
        self.metrics = {
            "predictions_per_second": 0.0,
            "training_time_avg": 0.0,
            "cache_hit_rate": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0,
            "api_latency": 0.0,
            "active_threads": 0,
        }
        self.prediction_count = 0
        self.training_times = deque(maxlen=100)
        self.api_latencies = deque(maxlen=100)
        self.start_time = time.time()

    def record_prediction(self, duration=None):
        """Record prediction performance"""
        self.prediction_count += 1
        if duration:
            self.api_latencies.append(duration)

    def record_training(self, duration):
        """Record training performance"""
        self.training_times.append(duration)

    def update_metrics(self, performance_optimizer=None):
        """Update real-time metrics
        
        Args:
            performance_optimizer: Optional reference to the global optimizer 
                                 to fetch cache stats.
        """
        elapsed = time.time() - self.start_time
        self.metrics["predictions_per_second"] = self.prediction_count / max(elapsed, 1)

        if self.training_times:
            self.metrics["training_time_avg"] = sum(self.training_times) / len(
                self.training_times
            )

        if self.api_latencies:
            self.metrics["api_latency"] = sum(self.api_latencies) / len(
                self.api_latencies
            )

        # System metrics
        self.metrics["memory_usage"] = psutil.virtual_memory().percent
        self.metrics["cpu_usage"] = psutil.cpu_percent(interval=0.1)
        self.metrics["active_threads"] = threading.active_count()

        # Cache metrics
        if performance_optimizer:
            cache_stats = performance_optimizer.get_cache_stats()
            total_cache_requests = sum(stats["size"] for stats in cache_stats.values())
            if total_cache_requests > 0:
                self.metrics["cache_hit_rate"] = (
                    total_cache_requests / (total_cache_requests + 1)
                ) * 100

    def get_metrics(self, performance_optimizer=None):
        """Get current performance metrics"""
        self.update_metrics(performance_optimizer)
        return self.metrics.copy()
