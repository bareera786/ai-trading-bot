"""
Phase 6: Model Watchdog Service
Continuous performance monitoring with automatic protective actions.
"""
import logging
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional

from app.extensions import db, redis_client
from app.models import MLModel, ModelPerformanceMetric, WatchdogEvent, ShadowPrediction

logger = logging.getLogger(__name__)


class ModelWatchdogService:
    """
    Background service for continuous model health monitoring.
    Evaluates performance metrics and triggers protective actions.
    """
    
    @staticmethod
    def compute_health_state(metrics: dict) -> Tuple[str, float]:
        """
        Compute health state from performance metrics.
        
        Args:
            metrics: Dictionary of performance metrics
            
        Returns:
            Tuple of (health_state, health_score)
            health_state: HEALTHY | DEGRADING | FAILING
            health_score: 0.0 to 1.0
        """
        score = 1.0
        
        # Win Rate Check (30% weight)
        win_rate = metrics.get('win_rate_7d', 0.50)
        if win_rate < 0.45:
            score -= 0.3
        elif win_rate < 0.50:
            score -= 0.15
            
        # Confidence Check (20% weight)
        confidence = metrics.get('avg_confidence_7d', 0.60)
        if confidence < 0.50:
            score -= 0.2
        elif confidence < 0.60:
            score -= 0.1
            
        # Drawdown Check (40% weight - most critical)
        drawdown = metrics.get('current_drawdown_pct', 0.0)
        if drawdown > 25:
            score -= 0.4
        elif drawdown > 15:
            score -= 0.2
            
        # Loss Streak Check (30% weight)
        losses = metrics.get('consecutive_losses', 0)
        if losses >= 10:
            score -= 0.3
        elif losses >= 7:
            score -= 0.15
            
        # Bias Check - detect stuck model (20% weight)
        bias_long = metrics.get('signal_bias_long_pct', 0.33)
        bias_short = metrics.get('signal_bias_short_pct', 0.33)
        bias_flat = metrics.get('signal_bias_flat_pct', 0.34)
        max_bias = max(bias_long, bias_short, bias_flat)
        
        if max_bias > 0.85:  # >85% in one direction
            score -= 0.2
            
        # Clamp score
        score = max(0.0, min(1.0, score))
        
        # Determine state
        if score >= 0.75:
            return 'HEALTHY', score
        elif score >= 0.50:
            return 'DEGRADING', score
        else:
            return 'FAILING', score
    
    @staticmethod
    def should_trigger_soft_kill(health_state: str, metrics: dict) -> Tuple[bool, str]:
        """
        Determine if automatic signal pause is warranted.
        
        Args:
            health_state: Current health state
            metrics: Performance metrics
            
        Returns:
            Tuple of (should_pause, reason)
        """
        # Primary trigger: FAILING health state
        if health_state == 'FAILING':
            return True, "Model health degraded to FAILING state"
            
        # Hard limit: Consecutive losses
        losses = metrics.get('consecutive_losses', 0)
        if losses >= 12:
            return True, f"Consecutive loss streak: {losses}"
            
        # Hard limit: Drawdown breach
        drawdown = metrics.get('current_drawdown_pct', 0.0)
        if drawdown > 30:
            return True, f"Drawdown breach: {drawdown:.1f}%"
            
        # Hard limit: Heartbeat stale
        heartbeat_age = metrics.get('heartbeat_age_seconds', 0)
        if heartbeat_age > 300:  # 5 minutes
            return True, f"Inference heartbeat stale: {heartbeat_age}s"
            
        return False, ""
    
    @staticmethod
    def collect_metrics(model_id: int) -> dict:
        """
        Collect performance metrics for a model.
        
        Args:
            model_id: Model ID to collect metrics for
            
        Returns:
            Dictionary of performance metrics
        """
        try:
            # Get model
            model = MLModel.query.get(model_id)
            if not model:
                logger.warning(f"Model {model_id} not found")
                return ModelWatchdogService._default_metrics()
            
            # Time windows
            now = datetime.utcnow()
            window_7d = now - timedelta(days=7)
            window_30d = now - timedelta(days=30)
            
            # Query shadow predictions for this model
            predictions_7d = ShadowPrediction.query.filter(
                ShadowPrediction.model_id == model.id,
                ShadowPrediction.timestamp >= window_7d
            ).all()
            
            predictions_30d = ShadowPrediction.query.filter(
                ShadowPrediction.model_id == model.id,
                ShadowPrediction.timestamp >= window_30d
            ).all()
            
            # Calculate metrics
            metrics = {
                'win_rate_7d': ModelWatchdogService._calculate_win_rate(predictions_7d),
                'win_rate_30d': ModelWatchdogService._calculate_win_rate(predictions_30d),
                'avg_confidence_7d': ModelWatchdogService._calculate_avg_confidence(predictions_7d),
                'avg_confidence_30d': ModelWatchdogService._calculate_avg_confidence(predictions_30d),
                'max_drawdown_pct': 0.0,  # TODO: Implement from trade history
                'current_drawdown_pct': 0.0,  # TODO: Implement from trade history
                'consecutive_losses': 0,  # TODO: Implement from trade history
                'signal_bias_long_pct': ModelWatchdogService._calculate_bias(predictions_7d, 'LONG'),
                'signal_bias_short_pct': ModelWatchdogService._calculate_bias(predictions_7d, 'SHORT'),
                'signal_bias_flat_pct': ModelWatchdogService._calculate_bias(predictions_7d, 'FLAT'),
                'inference_latency_ms': 0.0,  # TODO: Implement from metrics
                'heartbeat_age_seconds': ModelWatchdogService._get_heartbeat_age(),
                'total_signals_7d': len(predictions_7d),
                'total_signals_30d': len(predictions_30d)
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics for model {model_id}: {e}")
            return ModelWatchdogService._default_metrics()
    
    @staticmethod
    def _default_metrics() -> dict:
        """Return default metrics when collection fails."""
        return {
            'win_rate_7d': 0.50,
            'win_rate_30d': 0.50,
            'avg_confidence_7d': 0.60,
            'avg_confidence_30d': 0.60,
            'max_drawdown_pct': 0.0,
            'current_drawdown_pct': 0.0,
            'consecutive_losses': 0,
            'signal_bias_long_pct': 0.33,
            'signal_bias_short_pct': 0.33,
            'signal_bias_flat_pct': 0.34,
            'inference_latency_ms': 0.0,
            'heartbeat_age_seconds': 0,
            'total_signals_7d': 0,
            'total_signals_30d': 0
        }
    
    @staticmethod
    def _calculate_win_rate(predictions: list) -> float:
        """Calculate win rate from predictions (placeholder)."""
        if not predictions:
            return 0.50
        # TODO: Implement actual win rate calculation from trade outcomes
        return 0.55  # Placeholder
    
    @staticmethod
    def _calculate_avg_confidence(predictions: list) -> float:
        """Calculate average confidence from predictions."""
        if not predictions:
            return 0.60
        confidences = [p.confidence for p in predictions]
        return sum(confidences) / len(confidences) if confidences else 0.60
    
    @staticmethod
    def _calculate_bias(predictions: list, signal_type: str) -> float:
        """Calculate signal bias percentage."""
        if not predictions:
            return 0.33
        count = sum(1 for p in predictions if p.signal == signal_type)
        return count / len(predictions) if predictions else 0.33
    
    @staticmethod
    def _get_heartbeat_age() -> int:
        """Get age of last inference heartbeat in seconds."""
        try:
            if not redis_client:
                return 0
            last_beat = redis_client.get("brain:heartbeat")
            if last_beat:
                last_ts = float(last_beat)
                age = int(datetime.utcnow().timestamp() - last_ts)
                return age
        except Exception as e:
            logger.error(f"Error getting heartbeat age: {e}")
        return 0
    
    @staticmethod
    def execute_soft_kill(model_id: int, reason: str):
        """
        Execute automatic signal pause (soft kill).
        IDEMPOTENT - safe to call multiple times.
        
        Args:
            model_id: Model ID that triggered the pause
            reason: Human-readable reason for the pause
        """
        try:
            # Set Redis pause flag
            if redis_client:
                redis_client.set('brain:signals:paused', 'true')
            
            # Update model
            model = MLModel.query.get(model_id)
            if model:
                model.auto_paused = True
                model.auto_pause_reason = reason
                db.session.commit()
            
            # Log event
            event = WatchdogEvent(
                event_type='SOFT_KILL',
                severity='CRITICAL',
                model_id=model_id,
                trigger_reason=reason,
                action_taken='PAUSED_SIGNALS'
            )
            db.session.add(event)
            db.session.commit()
            
            logger.critical(f"🛑 SOFT KILL TRIGGERED: {reason} (Model: {model_id})")
            
        except Exception as e:
            logger.error(f"Error executing soft kill: {e}")
            db.session.rollback()
    
    @staticmethod
    def run_watchdog_cycle():
        """
        Execute one watchdog evaluation cycle.
        Called by background thread every 60 seconds.
        
        FAIL-SAFE: Errors do NOT block trading.
        """
        try:
            # Get active model
            active_model = MLModel.query.filter_by(status='active').first()
            if not active_model:
                logger.debug("No active model, skipping watchdog cycle")
                return
            
            logger.debug(f"Watchdog cycle for model {active_model.id}")
            
            # Collect metrics
            metrics = ModelWatchdogService.collect_metrics(active_model.id)
            
            # Compute health
            health_state, health_score = ModelWatchdogService.compute_health_state(metrics)
            
            # Store metrics
            perf_metric = ModelPerformanceMetric(
                model_id=active_model.id,
                health_state=health_state,
                health_score=health_score,
                win_rate_7d=metrics['win_rate_7d'],
                win_rate_30d=metrics['win_rate_30d'],
                avg_confidence_7d=metrics['avg_confidence_7d'],
                avg_confidence_30d=metrics['avg_confidence_30d'],
                max_drawdown_pct=metrics['max_drawdown_pct'],
                current_drawdown_pct=metrics['current_drawdown_pct'],
                consecutive_losses=metrics['consecutive_losses'],
                signal_bias_long_pct=metrics['signal_bias_long_pct'],
                signal_bias_short_pct=metrics['signal_bias_short_pct'],
                signal_bias_flat_pct=metrics['signal_bias_flat_pct'],
                inference_latency_ms=metrics['inference_latency_ms'],
                heartbeat_age_seconds=metrics['heartbeat_age_seconds'],
                total_signals_7d=metrics['total_signals_7d'],
                total_signals_30d=metrics['total_signals_30d']
            )
            db.session.add(perf_metric)
            
            # Update model health state
            active_model.health_state = health_state
            active_model.last_health_check = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Model {active_model.id} health: {health_state} (score: {health_score:.2f})")
            
            # Check for soft kill trigger
            should_pause, pause_reason = ModelWatchdogService.should_trigger_soft_kill(
                health_state, metrics
            )
            
            if should_pause and not active_model.auto_paused:
                ModelWatchdogService.execute_soft_kill(active_model.id, pause_reason)
                
        except Exception as e:
            logger.error(f"Watchdog cycle failed: {e}")
            # FAIL SAFE: Do NOT block trading on watchdog failure
