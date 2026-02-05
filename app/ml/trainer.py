from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
import logging
from app.ml.memory_efficient_loader import ChunkedDataLoader

logger = logging.getLogger(__name__)

class EfficientMLTrainer:
    def __init__(self):
        self.data_loader = ChunkedDataLoader()
        self.model_performance = {}  # Track model performance
        self.best_models = ['rf', 'gb']  # Start with best performers

    def select_best_models(self) -> List[str]:
        """Select only the best performing models based on recent performance"""
        if not self.model_performance:
            return self.best_models  # Default to best known models

        # Sort models by recent performance and return top performers
        sorted_models = sorted(
            self.model_performance.items(),
            key=lambda x: x[1].get('accuracy', 0),
            reverse=True
        )
        return [model[0] for model in sorted_models[:3]]  # Top 3 models

    def retrain_models_parallel(self, data_path: str) -> Dict:
        """Train models in parallel for better performance"""
        models_to_train = self.select_best_models()
        logger.info(f"Training {len(models_to_train)} models in parallel: {models_to_train}")

        results = {}
        with ThreadPoolExecutor(max_workers=min(4, len(models_to_train))) as executor:
            # Submit training tasks
            future_to_model = {
                executor.submit(self.train_model, model_name, data_path): model_name
                for model_name in models_to_train
            }

            # Collect results as they complete
            for future in future_to_model:
                model_name = future_to_model[future]
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    results[model_name] = result
                    self.model_performance[model_name] = result
                    logger.info(f"✅ {model_name} training completed: {result}")
                except Exception as e:
                    logger.error(f"❌ {model_name} training failed: {e}")
                    results[model_name] = {'error': str(e)}

        return results

    def train_model(self, model_name: str, data_path: str) -> Dict:
        """Train a single model with memory-efficient loading"""
        try:
            # Use memory-efficient loader for large datasets
            model = self._create_model(model_name)

            # Train incrementally on chunks
            self.data_loader.train_incremental(model, data_path)

            # Evaluate performance (simplified - implement based on your metrics)
            performance = self._evaluate_model(model, data_path)

            # Save model
            self._save_model(model, model_name)

            return {
                'model_name': model_name,
                'accuracy': performance.get('accuracy', 0),
                'training_time': performance.get('time', 0),
                'status': 'completed'
            }

        except Exception as e:
            logger.error(f"Training failed for {model_name}: {e}")
            return {
                'model_name': model_name,
                'error': str(e),
                'status': 'failed'
            }

    def _create_model(self, model_name: str):
        """Create model instance based on name"""
        if model_name == 'rf':
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(n_estimators=100, random_state=42)
        elif model_name == 'gb':
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(n_estimators=100, random_state=42)
        elif model_name == 'svm':
            from sklearn.svm import SVC
            return SVC(probability=True, random_state=42)
        elif model_name == 'nn':
            from sklearn.neural_network import MLPClassifier
            return MLPClassifier(hidden_layer_sizes=(100, 50), random_state=42)
        else:
            raise ValueError(f"Unknown model: {model_name}")

    def _evaluate_model(self, model, data_path: str) -> Dict:
        """Evaluate model performance"""
        # Simplified evaluation - implement based on your validation approach
        return {
            'accuracy': 0.85,  # Placeholder
            'time': 120  # Placeholder training time
        }

    def _save_model(self, model, model_name: str):
        """Save trained model"""
        # Implement model saving logic
