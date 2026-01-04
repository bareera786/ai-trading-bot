#!/usr/bin/env python3
"""
User Models Service
Handles user-specific ML model training and management
"""

import os
import redis
import json
import numpy as np
from flask import Flask, request, jsonify
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from datetime import datetime
from typing import Optional, cast, List, Dict, Any
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Redis configuration
redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
# Parse Redis URL for explicit client creation
from urllib.parse import urlparse

parsed = urlparse(redis_url)
redis_client = redis.Redis(
    host=parsed.hostname or "localhost", port=parsed.port or 6379, decode_responses=True
)


class UserModelManager:
    def __init__(self):
        self.models_dir = "user_models"
        os.makedirs(self.models_dir, exist_ok=True)

    def train_user_model(
        self, user_id: str, features: np.ndarray, targets: np.ndarray
    ) -> Dict[str, Any]:
        """Train a personalized model for a user"""
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, targets, test_size=0.2, random_state=42
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            model.fit(X_train_scaled, y_train)

            # Evaluate
            train_score = model.score(X_train_scaled, y_train)
            test_score = model.score(X_test_scaled, y_test)

            # Save model and scaler
            model_path = os.path.join(self.models_dir, f"{user_id}_model.joblib")
            scaler_path = os.path.join(self.models_dir, f"{user_id}_scaler.joblib")

            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)

            # Cache model info in Redis
            model_info = {
                "user_id": user_id,
                "train_score": float(train_score),
                "test_score": float(test_score),
                "created_at": datetime.utcnow().isoformat(),
                "model_path": model_path,
                "scaler_path": scaler_path,
            }

            redis_client.setex(
                f"user_model:{user_id}", 86400, json.dumps(model_info)
            )  # Cache for 24 hours

            return model_info

        except Exception as e:
            logger.error(f"Model training failed for user {user_id}: {e}")
            raise

    def get_user_model(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get cached model info for a user"""
        try:
            cached_info = cast(Optional[str], redis_client.get(f"user_model:{user_id}"))
            if cached_info:
                return json.loads(cached_info)
            return None
        except Exception as e:
            logger.error(f"Failed to get model for user {user_id}: {e}")
            return None

    def predict_with_user_model(
        self, user_id: str, features: np.ndarray
    ) -> Optional[np.ndarray]:
        """Make predictions using user's personalized model"""
        try:
            model_info = self.get_user_model(user_id)
            if not model_info:
                return None

            # Load model and scaler
            model = joblib.load(model_info["model_path"])
            scaler = joblib.load(model_info["scaler_path"])

            # Scale features and predict
            features_scaled = scaler.transform(features)
            predictions = model.predict(features_scaled)

            return predictions

        except Exception as e:
            logger.error(f"Prediction failed for user {user_id}: {e}")
            return None


# Initialize manager
model_manager = UserModelManager()


@app.route("/train", methods=["POST"])
def train_model():
    """Train a model for a user"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        features = np.array(data.get("features", []))
        targets = np.array(data.get("targets", []))

        if not user_id or len(features) == 0 or len(targets) == 0:
            return jsonify({"error": "Missing user_id, features, or targets"}), 400

        result = model_manager.train_user_model(user_id, features, targets)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Training failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/predict/<user_id>", methods=["POST"])
def predict(user_id):
    """Make predictions for a user"""
    try:
        data = request.get_json()
        features = np.array(data.get("features", []))

        if len(features) == 0:
            return jsonify({"error": "Missing features"}), 400

        predictions = model_manager.predict_with_user_model(user_id, features)
        if predictions is None:
            return jsonify({"error": "No model found for user"}), 404

        return jsonify({"predictions": predictions.tolist()})

    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/model/<user_id>", methods=["GET"])
def get_model_info(user_id):
    """Get model information for a user"""
    try:
        model_info = model_manager.get_user_model(user_id)
        if model_info:
            return jsonify(model_info)
        else:
            return jsonify({"error": "Model not found"}), 404

    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_client.ping()
        return jsonify({"status": "healthy", "service": "user-models"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    try:
        # Get model counts (use SCAN to avoid blocking Redis)
        total_models = sum(1 for _ in redis_client.scan_iter(match="user_model:*"))

        metrics_output = f"""# HELP user_models_active_models Total number of active user models
# TYPE user_models_active_models gauge
user_models_active_models {total_models}
"""

        return metrics_output, 200, {"Content-Type": "text/plain"}

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return "Error generating metrics", 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5004))
    app.run(host="0.0.0.0", port=port, debug=False)
