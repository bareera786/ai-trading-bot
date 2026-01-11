"""
Main entry point for AI Trading Bot with optimized resource management
"""
import logging
import time
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config.resource_manager import ResourceManager, ResourceError
from training.smart_trainer import SmartTrainingScheduler
from models.model_factory import ResourceAwareModelFactory, ModelComplexity
from data.nvme_optimized_handler import NVMeOptimizedDataHandler
from integrations.dashboard_integration import DashboardExporter
from config.dashboard_config import DashboardConfig
from utils.compression import get_compressor
from app.services.persistence import ProfessionalPersistence
from app.tasks.self_improvement import SelfImprovementWorker

print("Python executable:", sys.executable)
print("Python path:", sys.path)

class AITradingBot:
    """
    Main AI Trading Bot application with resource optimization
    """

    def __init__(self, config_path: Optional[str] = None):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)

        self.logger.info("Initializing AI Trading Bot with resource optimization")

        # Initialize core components
        self.resource_manager = ResourceManager()
        self.data_handler = NVMeOptimizedDataHandler()
        self.model_factory = ResourceAwareModelFactory(self.resource_manager)
        self.training_scheduler = SmartTrainingScheduler(self.resource_manager)
        
        # Initialize dashboard with configuration
        self.dashboard_config = DashboardConfig()
        self.dashboard_exporter = DashboardExporter(self.resource_manager, self.dashboard_config)

        # Initialize Zstandard compressor and persistence
        self.compression_level = 3  # Balanced compression
        self.compressor = get_compressor(level=self.compression_level)
        self.persistence = ProfessionalPersistence(compression_level=self.compression_level)

        # Initialize self-improvement worker
        self.self_improvement_worker = SelfImprovementWorker(
            ultimate_trader=None,  # Replace with actual trader instance
            optimized_trader=None,  # Replace with actual trader instance
            ultimate_ml_system=None,  # Replace with actual ML system instance
            optimized_ml_system=None,  # Replace with actual ML system instance
            dashboard_data={},
            trading_config={},
            compression_level=self.compression_level
        )

        # Bot state
        self.is_running = False
        self.current_model = None
        
        # Trading metrics
        self.daily_trade_count = 0
        self.daily_pnl = 0.0
        self.active_pairs = set()
        self.total_position_size = 0.0

        self.logger.info("AI Trading Bot initialized successfully")

    def setup_logging(self):
        """Configure application logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'trading_bot.log'),
                logging.StreamHandler()
            ]
        )

    def startup_checks(self) -> bool:
        """Perform system checks before starting"""
        try:
            self.logger.info("Performing startup checks...")

            # Check system resources
            resources = self.resource_manager.get_system_resources()
            self.logger.info(f"System resources: {resources}")

            # Check disk space
            disk_usage = self.data_handler.get_disk_usage()
            disk_size_gb = float(disk_usage["total_size_gb"])
            if disk_size_gb > 120:  # 120GB used of 160GB
                self.logger.warning(f"High disk usage: {disk_size_gb:.1f}GB")

            # Check if safe to run
            if not self.resource_manager.is_safe_for_training():
                self.logger.warning("System resources low at startup")

            # Set CPU affinity for main process (trading)
            self.resource_manager.set_cpu_affinity(for_training=False)
            
            # Reset daily metrics
            self._reset_daily_metrics()

            self.logger.info("Startup checks completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Startup checks failed: {e}")
            return False

    def initialize_model(self):
        """Initialize or load trading model"""
        try:
            self.logger.info("Initializing trading model...")

            # Determine optimal model complexity
            complexity = self.model_factory.get_optimal_model_complexity()
            self.logger.info(f"Selected model complexity: {complexity.value}")

            # Create or load model
            self.current_model = self.model_factory.create_model(complexity)

            # Load training data
            training_data = self.data_handler.load_optimized("training_data.parquet")

            # Train or update model
            batch_size = self.model_factory.get_optimal_batch_size(complexity)
            self.logger.info(f"Training with batch size: {batch_size}")

            # Your training logic here
            # self.current_model.fit(training_data)

            self.logger.info("Model initialization completed")

        except Exception as e:
            self.logger.error(f"Model initialization failed: {e}")
            raise

    def trading_loop(self):
        """Main trading loop"""
        self.logger.info("Starting trading loop")

        try:
            while self.is_running:
                # Check resources before each iteration
                if not self.resource_manager.is_safe_for_training():
                    self.logger.warning("Resources low, pausing trading")
                    time.sleep(60)
                    continue

                # Execute trading logic
                self.execute_trading_cycle()

                # Export dashboard metrics
                self._export_dashboard_metrics()

                # Run scheduled tasks
                self.training_scheduler._conditional_light_update()

                # Sleep to prevent CPU spinning
                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Trading loop interrupted by user")
        except Exception as e:
            self.logger.error(f"Trading loop error: {e}", exc_info=True)

    def execute_trading_cycle(self):
        """Execute one trading cycle"""
        # Your trading logic here
        # 1. Get market data
        # 2. Generate predictions
        # 3. Execute trades
        # 4. Log results

        # Example placeholder - update with your actual trading logic
        if self.current_model:
            # prediction = self.current_model.predict(features)
            pass

    def _export_dashboard_metrics(self):
        """Export current metrics to dashboard"""
        try:
            # Prepare trading data for dashboard
            trading_data = {
                'pairs_active': len(self.active_pairs),
                'trades_today': self.daily_trade_count,
                'daily_pnl': self.daily_pnl,
                'position_size': self.total_position_size
            }

            # Export metrics
            metrics = self.dashboard_exporter.export_metrics(
                self.training_scheduler,
                trading_data
            )

            # Log health score periodically (every 60 cycles ≈ 1 minute)
            if hasattr(self, '_metrics_counter'):
                self._metrics_counter += 1
            else:
                self._metrics_counter = 1

            if self._metrics_counter % 60 == 0:
                health_score = self.dashboard_exporter.get_system_health_score()
                self.logger.info(f"System health score: {health_score}/100")

        except Exception as e:
            self.logger.debug(f"Dashboard metrics export failed: {e}")

    def _reset_daily_metrics(self):
        """Reset daily trading metrics"""
        self.daily_trade_count = 0
        self.daily_pnl = 0.0
        self.active_pairs.clear()
        self.total_position_size = 0.0
        self.logger.info("Daily trading metrics reset")

    def update_trading_metrics(self, trade_count: int = 0, pnl_change: float = 0.0, 
                              pairs: Optional[set] = None, position_size: float = 0.0):
        """Update trading metrics for dashboard"""
        self.daily_trade_count += trade_count
        self.daily_pnl += pnl_change
        if pairs:
            self.active_pairs.update(pairs)
        self.total_position_size = position_size

    def run(self):
        """Main application run method"""
        try:
            self.logger.info("Starting AI Trading Bot")

            # Perform startup checks
            if not self.startup_checks():
                self.logger.error("Startup checks failed, exiting")
                return

            # Initialize model
            self.initialize_model()

            # Start scheduler in background
            import threading
            scheduler_thread = threading.Thread(
                target=self.training_scheduler.run_scheduler,
                daemon=True
            )
            scheduler_thread.start()

            # Start trading
            self.is_running = True
            self.trading_loop()

        except ResourceError as e:
            self.logger.error(f"Resource error: {e}")
        except Exception as e:
            self.logger.error(f"Application error: {e}", exc_info=True)
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown procedure"""
        self.logger.info("Shutting down AI Trading Bot")
        self.is_running = False

        # Save model state
        if self.current_model:
            self.save_model_state()

        # Compress old data
        self.data_handler.compress_old_data(days_old=3)

        self.logger.info("Shutdown completed")

    def save_model_state(self):
        """Save current model state"""
        try:
            model_dir = Path("models")
            model_dir.mkdir(exist_ok=True)

            import joblib
            joblib.dump(
                self.current_model,
                model_dir / f"model_{int(time.time())}.joblib"
            )

            self.logger.info("Model state saved")
        except Exception as e:
            self.logger.error(f"Failed to save model state: {e}")

    def _capture_current_state(self) -> dict:
        """Capture a serializable snapshot of the bot's current runtime state.

        This is a minimal, safe implementation to satisfy static checkers
        and provide useful information for persistence/backups. It should
        be extended later to include richer, application-specific data.
        """
        try:
            state = {
                "timestamp": int(time.time()),
                "is_running": bool(self.is_running),
                "daily_trade_count": int(self.daily_trade_count),
                "daily_pnl": float(self.daily_pnl),
                "active_pairs": list(self.active_pairs) if self.active_pairs else [],
                "total_position_size": float(self.total_position_size),
                "current_model_class": (
                    self.current_model.__class__.__name__
                    if hasattr(self.current_model, "__class__")
                    else str(type(self.current_model))
                ),
            }
        except Exception as e:
            # Never fail capturing state: log and return minimal info
            try:
                self.logger.debug("Failed to capture detailed state: %s", e)
            except Exception:
                pass
            return {"timestamp": int(time.time()), "is_running": bool(self.is_running)}

        return state

    def save_state(self):
        """Compressed state persistence"""
        try:
            state = self._capture_current_state()  # Your existing method

            backup_path = self.persistence.save_complete_state(
                trader=None,  # Replace with actual trader instance
                ml_system=None,  # Replace with actual ML system instance
                config={},
                symbols=[],
                historical_data={},
            )

            self.logger.info(f"State saved successfully: {backup_path}")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def create_snapshot(self):
        """Create a compressed snapshot of the bot's state and models"""
        try:
            snapshot_path = self.self_improvement_worker._create_snapshot()
            self.logger.info(f"Snapshot created successfully: {snapshot_path}")
        except Exception as e:
            self.logger.error(f"Failed to create snapshot: {e}")

def main():
    """Application entry point"""
    bot = AITradingBot()

    try:
        bot.run()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()