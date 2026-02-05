"""
Intelligent training scheduler with resource awareness
"""
import time
import schedule
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import logging
from pathlib import Path

from config.resource_manager import ResourceManager

class ModelVersion:
    """Manages model versions and metadata"""

    def __init__(self, model_id: str, performance: float,
                 resources_used: Dict, training_time: float):
        self.model_id = model_id
        self.performance = performance
        self.resources_used = resources_used
        self.training_time = training_time
        self.timestamp = datetime.now()
        self.file_path = Path(f"models/{model_id}.pkl")

    def save(self):
        self.file_path.parent.mkdir(exist_ok=True)
        with open(self.file_path, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, model_id: str):
        file_path = Path(f"models/{model_id}.pkl")
        with open(file_path, 'rb') as f:
            return pickle.load(f)

class SmartTrainingScheduler:
    """
    Manages training schedules based on:
    1. Market hours
    2. System resources
    3. Model performance degradation
    4. Time-based triggers
    """

    def __init__(self, resource_manager: ResourceManager):
        self.rm = resource_manager
        self.logger = logging.getLogger(__name__)

        # Training configuration
        self.training_windows = [
            (2, 5),    # 2-5 AM UTC (after US market close)
            (14, 17),  # 2-5 PM UTC (before US market open)
        ]

        # Performance thresholds
        self.performance_degradation_threshold = 0.02  # 2%
        self.minimum_retrain_interval = 3600  # 1 hour
        self.full_retrain_interval = 86400    # 24 hours

        # State tracking
        self.last_training_time = 0
        self.best_performance = 0.0
        self.current_model_id = None
        self.model_versions = []

        # Initialize schedules
        self._setup_schedules()

    def _setup_schedules(self):
        """Setup automated training schedules"""

        # Light incremental update every 15 minutes (if safe)
        schedule.every(15).minutes.do(self._conditional_light_update)

        # Full retraining during optimal windows
        schedule.every().day.at("02:30").do(self._conditional_full_training)
        schedule.every().day.at("14:30").do(self._conditional_full_training)

        # Performance-based check every 30 minutes
        schedule.every(30).minutes.do(self._performance_based_check)

        # Cleanup old models daily
        schedule.every().day.at("03:00").do(self._cleanup_old_models)

    def is_training_window(self) -> bool:
        """Check if current time is within training window"""
        current_hour = datetime.now().hour

        for start, end in self.training_windows:
            if start <= current_hour <= end:
                return True
        return False

    def _conditional_light_update(self):
        """Perform light update only if conditions are met"""
        if self._should_train(lightweight=True):
            self.logger.info("Starting scheduled light update")
            self.light_update()

    def _conditional_full_training(self):
        """Perform full training only if conditions are met"""
        if self._should_train(lightweight=False):
            self.logger.info("Starting scheduled full training")
            self.full_training()

    def _should_train(self, lightweight: bool = True) -> bool:
        """
        Determine if training should proceed based on multiple factors
        """
        # Check 1: System resources
        if not self.rm.is_safe_for_training():
            self.logger.warning("System resources insufficient for training")
            return False

        # Check 2: Training window (only required for full training)
        if not lightweight and not self.is_training_window():
            self.logger.info("Outside training window, skipping full training")
            return False

        # Check 3: Minimum interval between trainings
        time_since_last = time.time() - self.last_training_time
        min_interval = 900 if lightweight else self.minimum_retrain_interval

        if time_since_last < min_interval:
            self.logger.debug(f"Too soon since last training: {time_since_last:.0f}s")
            return False

        # Check 4: Market volatility (simplified)
        if self._is_high_volatility_period():
            self.logger.warning("High volatility period, deferring training")
            return False

        return True

    def _is_high_volatility_period(self) -> bool:
        """Check if we're in a high volatility market period"""
        # Placeholder - implement based on your market data
        # Check for major economic events, earnings, etc.
        current_hour = datetime.now().hour

        # Avoid training during market open/close
        market_open_hours = [
            (13, 30, 14, 30),  # US market open 9:30-10:30 EST
            (20, 0, 21, 0),    # US market close 4:00-5:00 EST
        ]

        for start_h, start_m, end_h, end_m in market_open_hours:
            current_time = datetime.now()
            start_time = current_time.replace(hour=start_h, minute=start_m, second=0)
            end_time = current_time.replace(hour=end_h, minute=end_m, second=0)

            if start_time <= current_time <= end_time:
                return True

        return False

    def light_update(self) -> Optional[str]:
        """
        Perform incremental/lightweight model update
        Returns model ID if successful
        """
        try:
            self.logger.info("Starting light model update")

            # Set CPU affinity for training
            self.rm.set_cpu_affinity(for_training=True)

            # Your incremental training logic here
            # Example: Update model with new data
            model_id = f"light_{int(time.time())}"

            # Simulate training
            time.sleep(60)  # Replace with actual training

            self.last_training_time = time.time()
            self.logger.info(f"Light update completed: {model_id}")

            return model_id

        except Exception as e:
            self.logger.error(f"Light update failed: {e}")
            return None

    def full_training(self) -> Optional[str]:
        """
        Perform full model retraining
        Returns model ID if successful
        """
        try:
            self.logger.info("Starting full model training")

            # Decorate with resource limits
            @self.rm.enforce_limits(timeout_seconds=600)
            def train_with_limits():
                # Set CPU affinity
                self.rm.set_cpu_affinity(for_training=True)

                # Your full training logic here
                # Example: Train new model from scratch
                model_id = f"full_{int(time.time())}"

                # Simulate training
                time.sleep(300)  # Replace with actual training

                # Calculate performance
                performance = self._evaluate_model()

                # Create and save model version
                model_version = ModelVersion(
                    model_id=model_id,
                    performance=performance,
                    resources_used=self.rm.get_system_resources().__dict__,
                    training_time=300
                )
                model_version.save()

                # Update best performance
                if performance > self.best_performance:
                    self.best_performance = performance
                    self.current_model_id = model_id

                self.model_versions.append(model_version)

                return model_id

            model_id = train_with_limits()
            self.last_training_time = time.time()

            self.logger.info(f"Full training completed: {model_id}")
            return model_id

        except Exception as e:
            self.logger.error(f"Full training failed: {e}")
            return None

    def _performance_based_check(self):
        """Check model performance and retrain if degraded"""
        if not self.current_model_id:
            return

        # Get current performance (implement based on your metrics)
        current_performance = self._get_current_performance()

        # Calculate degradation
        if self.best_performance > 0:
            degradation = (self.best_performance - current_performance) / self.best_performance

            if degradation > self.performance_degradation_threshold:
                self.logger.warning(
                    f"Performance degradation detected: {degradation:.2%}. "
                    f"Triggering retrain."
                )

                if self._should_train(lightweight=False):
                    self.full_training()

    def _get_current_performance(self) -> float:
        """Get current model performance (implement your metrics)"""
        # Placeholder - implement your performance tracking
        return 0.85  # Example performance metric

    def _evaluate_model(self) -> float:
        """Evaluate model performance (implement your evaluation)"""
        # Placeholder - implement your evaluation logic
        return np.random.uniform(0.8, 0.95)

    def _cleanup_old_models(self, keep_last_n: int = 5):
        """Clean up old model files to save disk space"""
        try:
            model_dir = Path("models")
            if not model_dir.exists():
                return

            # Get all model files sorted by modification time
            model_files = sorted(
                model_dir.glob("*.pkl"),
                key=lambda x: x.stat().st_mtime,
                reverse=True
            )

            # Keep only the most recent N files
            files_to_delete = model_files[keep_last_n:]

            for file_path in files_to_delete:
                file_path.unlink()
                self.logger.info(f"Deleted old model: {file_path.name}")

            self.logger.info(f"Cleaned up {len(files_to_delete)} old models")

        except Exception as e:
            self.logger.error(f"Model cleanup failed: {e}")

    def run_scheduler(self):
        """Main scheduler loop"""
        self.logger.info("Starting smart training scheduler")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")