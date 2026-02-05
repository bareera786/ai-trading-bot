from __future__ import annotations
import logging
import time
from typing import Dict, Any, Optional

from app.ml.inference.manager import AsyncInferenceManager

class ModelOracle:
    """
    The Oracle sits between Strategies and ML Models.
    Strategies ask the Oracle for "Advice" (probabilities, regime, volatility),
    instead of querying models directly.
    """
    
    def __init__(self, inference_manager: AsyncInferenceManager):
        self.inference_manager = inference_manager
        self.logger = logging.getLogger("ai_trading_bot.model_oracle")

    def get_advice(self, symbol: str, market_data: Any) -> Dict[str, Any]:
        """
        Get comprehensive advice for a symbol.
        Triggers inference if needed, but returns immediately (non-blocking).
        """
        # 1. Trigger fresh inference (non-blocking)
        self.inference_manager.request_inference(symbol, market_data)
        
        # 2. Get latest result from cache
        prediction = self.inference_manager.get_result(symbol)
        
        if not prediction:
            return {
                "status": "waiting",
                "confidence": 0.5,
                "regime": "unknown",
                "volatility_forecast": "neutral"
            }
            
        # 3. Interpret prediction
        # Assuming prediction structure from UltimateMLTrainingSystem
        # { "predicted_class": 1, "probabilities": [0.2, 0.7, 0.1], "volatility": ... }
        
        advice = {
            "status": "ready",
            "timestamp": prediction.get("timestamp", time.time()),
            "confidence": self._extract_confidence(prediction),
            "direction": self._extract_direction(prediction),
            "regime": self._extract_regime(prediction),
            "volatility_forecast": self._extract_volatility(prediction),
            "raw_prediction": prediction 
        }
        
        return advice

    def _extract_confidence(self, prediction: Dict) -> float:
        # Tries to find confidence score in various formats
        if "confidence" in prediction:
            return float(prediction["confidence"])
        if "probabilities" in prediction:
            probs = prediction["probabilities"]
            if isinstance(probs, list) and probs:
                return max(probs)
        return 0.5

    def _extract_direction(self, prediction: Dict) -> str:
        # Maps model output to direction
        if "direction" in prediction:
            return str(prediction["direction"])
        
        cls = prediction.get("predicted_class")
        # Assuming 0=SELL, 1=HOLD, 2=BUY (common 3-class)
        # Or 0=DOWN, 1=UP (2-class)
        # This mapping depends on the specific model trained.
        # Ideally model returns 'label'.
        if "label" in prediction:
            return str(prediction["label"]).upper()
            
        return "NEUTRAL"

    def _extract_regime(self, prediction: Dict) -> str:
        # Does the model predict regime?
        if "regime" in prediction:
            return str(prediction["regime"])
        return "standard"

    def _extract_volatility(self, prediction: Dict) -> str:
        if "volatility" in prediction:
            return str(prediction["volatility"])
        return "neutral"
