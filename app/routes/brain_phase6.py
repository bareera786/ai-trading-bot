"""
Phase 6: Performance Governance API Routes
Add these to brain.py or import as: from app.routes.brain_phase6 import *
"""
from flask import jsonify, request
from flask_login import current_user

from app.models import MLModel
from app.models_phase6 import ModelPerformanceMetric, WatchdogEvent
from app.services.model_promotion_service import ModelPromotionService
from app.services.audit_service import AuditService
from app.extensions import db, redis_client


def register_phase6_routes(brain_bp):
    """Register Phase 6 routes to brain blueprint."""
    
    @brain_bp.route('/performance/active', methods=['GET'])
    def get_active_performance():
        """Get real-time performance metrics and health state of active model."""
        active = MLModel.query.filter_by(status='active').first()
        
        if not active:
            return jsonify({"error": "No active model"}), 404
        
        # Get latest metrics
        latest_metric = ModelPerformanceMetric.query.filter_by(
            model_id=active.id
        ).order_by(ModelPerformanceMetric.timestamp.desc()).first()
        
        if not latest_metric:
            return jsonify({
                "model_id": active.id,
                "model_version": active.version,
                "health_state": active.health_state or "UNKNOWN",
                "health_score": None,
                "message": "No metrics available yet",
                "auto_paused": active.auto_paused,
                "auto_pause_reason": active.auto_pause_reason
            })
        
        return jsonify({
            "model_id": active.id,
            "model_version": active.version,
            "health_state": latest_metric.health_state,
            "health_score": latest_metric.health_score,
            "metrics": {
                "win_rate_7d": latest_metric.win_rate_7d,
                "win_rate_30d": latest_metric.win_rate_30d,
                "avg_confidence_7d": latest_metric.avg_confidence_7d,
                "avg_confidence_30d": latest_metric.avg_confidence_30d,
                "current_drawdown_pct": latest_metric.current_drawdown_pct,
                "max_drawdown_pct": latest_metric.max_drawdown_pct,
                "consecutive_losses": latest_metric.consecutive_losses,
                "signal_bias": {
                    "long": latest_metric.signal_bias_long_pct,
                    "short": latest_metric.signal_bias_short_pct,
                    "flat": latest_metric.signal_bias_flat_pct
                },
                "total_signals_7d": latest_metric.total_signals_7d
            },
            "auto_paused": active.auto_paused,
            "auto_pause_reason": active.auto_pause_reason,
            "last_check": active.last_health_check.isoformat() if active.last_health_check else None
        })
    
    @brain_bp.route('/models/validate-activation/<int:model_id>', methods=['POST'])
    def validate_model_activation(model_id):
        """Validate if shadow model meets promotion criteria."""
        is_valid, reason, comparison = ModelPromotionService.validate_promotion(model_id)
        
        return jsonify({
            "valid": is_valid,
            "reason": reason,
            "comparison_metrics": comparison
        }), 200 if is_valid else 400
    
    @brain_bp.route('/watchdog/events', methods=['GET'])
    def get_watchdog_events():
        """Get recent watchdog events for monitoring."""
        limit = request.args.get('limit', 50, type=int)
        
        events = WatchdogEvent.query.order_by(
            WatchdogEvent.timestamp.desc()
        ).limit(limit).all()
        
        return jsonify({
            "events": [e.to_dict() for e in events]
        })
    
    @brain_bp.route('/watchdog/resume', methods=['POST'])
    def manual_resume_from_autopause():
        """Manually resume signals after auto-pause (requires confirmation)."""
        data = request.json or {}
        confirmation = data.get('confirmation_phrase', '')
        
        if confirmation != 'MANUAL OVERRIDE CONFIRMED':
            return jsonify({"error": "Invalid confirmation phrase"}), 400
        
        # Get active model
        active = MLModel.query.filter_by(status='active').first()
        if not active:
            return jsonify({"error": "No active model"}), 404
        
        if not active.auto_paused:
            return jsonify({"message": "Model is not auto-paused"}), 200
        
        # Clear auto-pause
        active.auto_paused = False
        active.auto_pause_reason = None
        
        # Resume signals
        if redis_client:
            redis_client.set('brain:signals:paused', 'false')
        
        db.session.commit()
        
        # Audit log
        try:
            AuditService.log_event(
                current_user.id if current_user.is_authenticated else 'system',
                'brain.watchdog.manual_resume',
                f"Manually resumed signals after auto-pause (Model: {active.id})",
                status='success'
            )
        except:
            pass
        
        return jsonify({
            "status": "success",
            "message": "Signals resumed - monitor closely"
        })
