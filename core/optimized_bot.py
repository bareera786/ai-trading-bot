"""
Core optimized bot with minimal changes to your existing code
"""
import time
import logging
from typing import Optional

class OptimizedTradingBot:
    """
    Wrapper class to add optimization to your existing bot
    Minimal changes required
    """

    def __init__(self, existing_bot, config_path: Optional[str] = None):
        self.bot = existing_bot
        self.logger = logging.getLogger(__name__)

        # Import optimization modules
        from config.resource_manager import ResourceManager
        from training.smart_trainer import SmartTrainingScheduler
        from integrations.dashboard_integration import DashboardExporter

        # Initialize optimizers
        self.resource_manager = ResourceManager()
        self.training_scheduler = SmartTrainingScheduler(self.resource_manager)
        self.dashboard_exporter = DashboardExporter(self.resource_manager)

        # Override existing methods
        self._patch_existing_methods()

        self.logger.info("Optimization wrapper initialized")

    def _patch_existing_methods(self):
        """Patch existing bot methods with optimized versions"""

        # Store original methods
        self.original_train = getattr(self.bot, 'train_model', None)
        self.original_trade = getattr(self.bot, 'execute_trade', None)

        # Replace with optimized versions
        if self.original_train:
            setattr(self.bot, 'train_model', self.optimized_train)

        if self.original_trade:
            setattr(self.bot, 'execute_trade', self.optimized_trade)

    def optimized_train(self, *args, **kwargs):
        """Optimized training with resource awareness"""

        # Check if we have an original training method
        if self.original_train is None:
            self.logger.warning("No train_model method found on bot")
            return None

        # Check if training should proceed
        if not self.training_scheduler._should_train():
            self.logger.info("Training deferred due to system load")
            return None

        # Apply resource limits
        @self.resource_manager.enforce_limits(timeout_seconds=300)
        def safe_training():
            # Set CPU affinity
            self.resource_manager.set_cpu_affinity(for_training=True)

            # Call original training (guaranteed to be not None due to check above)
            assert self.original_train is not None
            result = self.original_train(*args, **kwargs)

            # Update scheduler
            self.training_scheduler.last_training_time = time.time()

            # Export metrics
            training_metrics = {
                'duration': time.time() - start_time,
                'success': result is not None,
                'cores_used': len(self.resource_manager.training_cores)
            }
            self.dashboard_exporter.export_training_metrics(training_metrics)

            return result

        start_time = time.time()
        try:
            return safe_training()
        except Exception as e:
            self.logger.error(f"Optimized training failed: {e}")
            return None

    def optimized_trade(self, *args, **kwargs):
        """Optimized trading with resource awareness"""

        # Check if we have an original trading method
        if self.original_trade is None:
            self.logger.warning("No execute_trade method found on bot")
            return None

        # Check system health before trading
        if not self.resource_manager.is_safe_for_training():
            self.logger.warning("Trading with limited resources")

        # Set CPU affinity for trading
        self.resource_manager.set_cpu_affinity(for_training=False)

        # Call original trade
        result = self.original_trade(*args, **kwargs)

        # Export trade metrics
        trade_metrics = {
            'timestamp': time.time(),
            'result': 'success' if result else 'failed',
            'resource_usage': self.resource_manager.get_system_resources().__dict__
        }
        self.dashboard_exporter.export_trade_metrics(trade_metrics)

        return result

    def run_optimized(self):
        """Run bot with optimizations"""

        # Export initial metrics
        self.dashboard_exporter.export_metrics(self.training_scheduler)

        # Start scheduler in background
        import threading
        scheduler_thread = threading.Thread(
            target=self.training_scheduler.run_scheduler,
            daemon=True
        )
        scheduler_thread.start()

        # Run original bot
        if hasattr(self.bot, 'run'):
            return self.bot.run()

        return None

    def get_optimization_status(self):
        """Get optimization status for dashboard"""
        resources = self.resource_manager.get_system_resources()

        return {
            'optimization_active': True,
            'resource_limits': {
                'max_cpu': self.resource_manager.max_cpu_percent,
                'max_memory': self.resource_manager.max_memory_percent,
                'training_cores': self.resource_manager.training_cores,
                'trading_cores': self.resource_manager.trading_cores,
            },
            'current_resources': resources.__dict__,
            'training_schedule': {
                'last_training': self.training_scheduler.last_training_time,
                'next_window': self.training_scheduler.training_windows,
            }
        }