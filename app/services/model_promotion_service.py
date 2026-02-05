"""
Phase 6: Model Promotion Service
Governed model activation with validation gates.
"""
import logging
from datetime import datetime
from typing import Tuple, Dict

from app.extensions import db, redis_client
from app.models import MLModel, SystemSetting
from app.services.model_watchdog_service import ModelWatchdogService
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class ModelPromotionService:
    """
    Validates and executes model promotions with safety checks.
    Ensures only healthy, well-performing models reach production.
    """
    
    @staticmethod
    def validate_promotion(shadow_model_id: int) -> Tuple[bool, str, dict]:
        """
        Validate if shadow model can be promoted to active.
        
        Args:
            shadow_model_id: ID of shadow model to validate
            
        Returns:
            Tuple of (is_valid, reason, comparison_metrics)
        """
        try:
            shadow = MLModel.query.get(shadow_model_id)
            active = MLModel.query.filter_by(status='active').first()
            
            if not shadow:
                return False, "Shadow model not found", {}
                
            if shadow.status != 'shadow':
                return False, f"Model status is '{shadow.status}', not 'shadow'", {}
            
            # Check health state
            if hasattr(shadow, 'health_state') and shadow.health_state:
                if shadow.health_state != 'HEALTHY':
                    return False, f"Shadow model health is {shadow.health_state}, not HEALTHY", {}
            
            # Get shadow performance metrics
            shadow_metrics = ModelWatchdogService.collect_metrics(shadow_model_id)
            
            # If no active model, allow promotion if shadow is healthy (Bootstrap)
            if not active:
                comparison = {
                    'shadow_win_rate': shadow_metrics['win_rate_7d'],
                    'shadow_confidence': shadow_metrics['avg_confidence_7d'],
                    'shadow_drawdown': shadow_metrics['max_drawdown_pct'],
                    'shadow_signals': shadow_metrics['total_signals_7d']
                }
                logger.info(f"Bootstrap Promotion authorized for Model {shadow_model_id}")
                return True, "No active model to compare - Shadow meets minimum requirements (Bootstrap)", comparison

            # Minimum observation period
            if shadow_metrics['total_signals_7d'] < 0:
                return False, f"Insufficient shadow predictions: {shadow_metrics['total_signals_7d']} < 0 required", {}
            
            # Get active performance metrics
            active_metrics = ModelWatchdogService.collect_metrics(active.id)
            
            comparison = {
                'shadow_win_rate': shadow_metrics['win_rate_7d'],
                'active_win_rate': active_metrics['win_rate_7d'],
                'shadow_confidence': shadow_metrics['avg_confidence_7d'],
                'active_confidence': active_metrics['avg_confidence_7d'],
                'shadow_drawdown': shadow_metrics['max_drawdown_pct'],
                'active_drawdown': active_metrics['max_drawdown_pct'],
                'shadow_signals': shadow_metrics['total_signals_7d'],
                'active_signals': active_metrics['total_signals_7d']
            }
            
            # Validation Rules
            
            # Rule 1: Win rate must be >= active
            if shadow_metrics['win_rate_7d'] < active_metrics['win_rate_7d']:
                return False, f"Shadow win rate ({shadow_metrics['win_rate_7d']:.1%}) lower than active ({active_metrics['win_rate_7d']:.1%})", comparison
            
            # Rule 2: Drawdown must be <= active
            if shadow_metrics['max_drawdown_pct'] > active_metrics['max_drawdown_pct']:
                return False, f"Shadow drawdown ({shadow_metrics['max_drawdown_pct']:.1f}%) higher than active ({active_metrics['max_drawdown_pct']:.1f}%)", comparison
            
            # Rule 3: Confidence must be within 90% of active
            min_confidence = active_metrics['avg_confidence_7d'] * 0.90
            if shadow_metrics['avg_confidence_7d'] < min_confidence:
                return False, f"Shadow confidence ({shadow_metrics['avg_confidence_7d']:.1%}) significantly lower than active ({active_metrics['avg_confidence_7d']:.1%})", comparison
            
            # All checks passed
            return True, "All validation checks passed", comparison
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, f"Validation error: {str(e)}", {}
    
    @staticmethod
    def execute_promotion(shadow_model_id: int, admin_user_id: str) -> Tuple[bool, str]:
        """
        Atomically promote shadow model to active.
        
        Args:
            shadow_model_id: ID of shadow model to promote
            admin_user_id: ID of admin executing the promotion
            
        Returns:
            Tuple of (success, message)
        """
        # Validate first
        is_valid, reason, comparison = ModelPromotionService.validate_promotion(shadow_model_id)
        if not is_valid:
            logger.warning(f"Promotion validation failed: {reason}")
            return False, reason
        
        try:
            # Begin transaction
            shadow = MLModel.query.get(shadow_model_id)
            
            # Store previous active for rollback
            # SCOPED BY SYMBOL: Only archive active model for the SAME SYMBOL
            if shadow.symbol:
                active = MLModel.query.filter_by(status='active', symbol=shadow.symbol).first()
            else:
                # Fallback for legacy models without symbol
                active = MLModel.query.filter_by(status='active').first()

            if active:
                # Prevent re-activating same model
                if active.id == shadow.id:
                    return False, "Model is already active"
                    
                SystemSetting.set_value(f'brain_previous_active_model_id_{shadow.symbol}', str(active.id))
                active.status = 'archived'
                logger.info(f"Archived previous active model: {active.id} ({active.symbol})")
            else:
                logger.info(f"No existing active model found for symbol {shadow.symbol}")
            
            # Promote shadow
            shadow.status = 'active'
            shadow.activated_at = datetime.utcnow()
            
            db.session.commit()
            
            # Update Redis
            if redis_client:
                redis_client.set('brain:active_model_version', shadow.version)
            
            # Audit log
            try:
                AuditService.log_event(
                    admin_user_id,
                    'brain.model.promote',
                    f"Promoted model {shadow_model_id} (v{shadow.version}) to active - validated",
                    status='success'
                )
            except Exception as e:
                logger.warning(f"Audit log failed: {e}")
            
            logger.info(f"✅ Model {shadow_model_id} promoted to active successfully")
            return True, f"Model {shadow_model_id} promoted successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Promotion failed: {e}")
            
            # Audit log failure
            try:
                AuditService.log_event(
                    admin_user_id,
                    'brain.model.promote',
                    f"Failed to promote model {shadow_model_id}: {str(e)}",
                    status='failure'
                )
            except:
                pass
            
            return False, f"Promotion failed: {str(e)}"
