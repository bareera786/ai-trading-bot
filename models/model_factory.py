"""
Factory for creating resource-aware models
"""
from typing import Dict, Any, Optional
import logging
from enum import Enum

from config.resource_manager import ResourceManager

class ModelComplexity(Enum):
    LIGHT = "light"      # For high-load periods
    MEDIUM = "medium"    # For normal operation
    HEAVY = "heavy"      # For low-load periods

class ResourceAwareModelFactory:
    """
    Creates models based on available system resources
    """

    def __init__(self, resource_manager: ResourceManager):
        self.rm = resource_manager
        self.logger = logging.getLogger(__name__)

        # Model configurations for different resource levels
        self.model_configs = {
            ModelComplexity.LIGHT: {
                "type": "lightgbm",
                "params": {
                    "n_estimators": 50,
                    "max_depth": 5,
                    "learning_rate": 0.1,
                    "n_jobs": 2,
                    "verbose": -1
                }
            },
            ModelComplexity.MEDIUM: {
                "type": "xgboost",
                "params": {
                    "n_estimators": 100,
                    "max_depth": 8,
                    "learning_rate": 0.05,
                    "n_jobs": 4,
                    "tree_method": "hist",
                    "max_bin": 256
                }
            },
            ModelComplexity.HEAVY: {
                "type": "xgboost",
                "params": {
                    "n_estimators": 200,
                    "max_depth": 12,
                    "learning_rate": 0.01,
                    "n_jobs": 7,  # Leave 1 core for system
                    "tree_method": "hist",
                    "max_bin": 512,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8
                }
            }
        }

    def get_optimal_model_complexity(self) -> ModelComplexity:
        """Determine optimal model complexity based on system load"""
        resources = self.rm.get_system_resources()

        # Decision matrix based on system load
        if resources.load_avg_1min > 6 or resources.cpu_percent > 80:
            return ModelComplexity.LIGHT
        elif resources.load_avg_1min > 3 or resources.cpu_percent > 60:
            return ModelComplexity.MEDIUM
        else:
            return ModelComplexity.HEAVY

    def create_model(self, complexity: Optional[ModelComplexity] = None):
        """Create a model with optimal configuration"""
        if complexity is None:
            complexity = self.get_optimal_model_complexity()

        config = self.model_configs[complexity]

        self.logger.info(
            f"Creating {complexity.value} model with config: {config['params']}"
        )

        if config["type"] == "lightgbm":
            import lightgbm as lgb
            return lgb.LGBMRegressor(**config["params"])

        elif config["type"] == "xgboost":
            import xgboost as xgb
            return xgb.XGBRegressor(**config["params"])

        else:
            from sklearn.ensemble import RandomForestRegressor
            return RandomForestRegressor(**config["params"])

    def get_optimal_batch_size(self, complexity: ModelComplexity) -> int:
        """Get optimal batch size for training"""
        resources = self.rm.get_system_resources()

        # Adjust batch size based on available memory
        memory_factor = resources.memory_available_gb / 16  # 16GB total

        base_batch_sizes = {
            ModelComplexity.LIGHT: 256,
            ModelComplexity.MEDIUM: 128,
            ModelComplexity.HEAVY: 64
        }

        batch_size = int(base_batch_sizes[complexity] * memory_factor)

        # Ensure reasonable limits
        return max(16, min(batch_size, 1024))