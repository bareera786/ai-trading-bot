from datetime import datetime, timedelta
import logging
from app.extensions import db
from app.models import ShadowPrediction, MLModel

logger = logging.getLogger("shadow_service")

class ShadowService:
    """
    Manages Shadow Model logic: persistence, comparison, and analysis.
    Does NOT interact with trading execution.
    """

    @staticmethod
    def record_prediction(
        timestamp: datetime,
        symbol: str, 
        model_version: str, 
        signal: str, 
        confidence: float, 
        price: float,
        active_ref: str = None
    ):
        """
        Persist a shadow prediction to the DB.
        This runs in a background thread, so we must be careful with DB sessions.
        """
        try:
            # Create transient object
            pred = ShadowPrediction(
                timestamp=timestamp,
                symbol=symbol,
                model_version=model_version,
                signal=signal,
                confidence=confidence,
                price=price,
                active_prediction_ref=active_ref
            )
            db.session.add(pred)
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to record shadow prediction: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def get_comparison_stats(time_window_hours=24):
        """
        Compare Active vs Shadow models over a time window.
        Returns a dictionary of stats per model.
        """
        since = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # This is a simplified analysis. Phase 4.1 will enhance this with PnL simulation.
        stats = {}
        
        # Get all shadow predictions
        preds = ShadowPrediction.query.filter(ShadowPrediction.timestamp >= since).all()
        
        for p in preds:
            if p.model_version not in stats:
                stats[p.model_version] = {"count": 0, "avg_confidence": 0.0, "signals": {}}
                
            s = stats[p.model_version]
            s["count"] += 1
            s["avg_confidence"] += p.confidence
            s["signals"][p.signal] = s["signals"].get(p.signal, 0) + 1

        # Normalize
        for ver, s in stats.items():
            if s["count"] > 0:
                s["avg_confidence"] /= s["count"]
                
        return stats
