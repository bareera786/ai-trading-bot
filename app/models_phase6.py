"""
Phase 6 Database Models
Import these in app/models.py with: from app.models_phase6 import *
"""
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base
from app.extensions import db

# Base = declarative_base() # REMOVED: Causing registry conflicts with db.Model


class ModelPerformanceMetric(db.Model):
    """
    Time-series performance metrics for models.
    Tracks rolling windows of performance data for health monitoring.
    """
    __tablename__ = "model_performance_metric"
    
    id = db.Column(db.Integer, primary_key=True)
    model_id = db.Column(db.Integer, db.ForeignKey("ml_model.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Performance Metrics (Rolling Windows)
    win_rate_7d = db.Column(db.Float)
    win_rate_30d = db.Column(db.Float)
    avg_confidence_7d = db.Column(db.Float)
    avg_confidence_30d = db.Column(db.Float)
    max_drawdown_pct = db.Column(db.Float)
    current_drawdown_pct = db.Column(db.Float)
    
    # Risk Metrics
    consecutive_losses = db.Column(db.Integer, default=0)
    signal_bias_long_pct = db.Column(db.Float)
    signal_bias_short_pct = db.Column(db.Float)
    signal_bias_flat_pct = db.Column(db.Float)
    
    # System Metrics
    inference_latency_ms = db.Column(db.Float)
    heartbeat_age_seconds = db.Column(db.Integer)
    
    # Health State
    health_state = db.Column(db.String(20), nullable=False, index=True)  # HEALTHY, DEGRADING, FAILING
    health_score = db.Column(db.Float)  # 0.0 to 1.0
    
    # Metadata
    total_signals_7d = db.Column(db.Integer, default=0)
    total_signals_30d = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            "id": self.id,
            "model_id": self.model_id,
            "timestamp": self.timestamp.isoformat(),
            "win_rate_7d": self.win_rate_7d,
            "win_rate_30d": self.win_rate_30d,
            "avg_confidence_7d": self.avg_confidence_7d,
            "avg_confidence_30d": self.avg_confidence_30d,
            "max_drawdown_pct": self.max_drawdown_pct,
            "current_drawdown_pct": self.current_drawdown_pct,
            "consecutive_losses": self.consecutive_losses,
            "signal_bias": {
                "long": self.signal_bias_long_pct,
                "short": self.signal_bias_short_pct,
                "flat": self.signal_bias_flat_pct
            },
            "health_state": self.health_state,
            "health_score": self.health_score,
            "total_signals_7d": self.total_signals_7d
        }


class WatchdogEvent(db.Model):
    """
    Audit log for watchdog automated actions.
    Records all protective actions taken by the system.
    """
    __tablename__ = "watchdog_event"
    
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)  # SOFT_KILL, HEALTH_DEGRADED, METRIC_BREACH
    severity = db.Column(db.String(20), nullable=False, index=True)  # INFO, WARNING, CRITICAL
    
    model_id = db.Column(db.Integer, db.ForeignKey("ml_model.id"), nullable=True)
    
    trigger_reason = db.Column(db.Text, nullable=False)
    trigger_metrics = db.Column(db.JSON)  # Snapshot of metrics that triggered event
    
    action_taken = db.Column(db.String(100))  # PAUSED_SIGNALS, SENT_ALERT, NONE
    auto_resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by = db.Column(db.String(100), nullable=True)
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "severity": self.severity,
            "model_id": self.model_id,
            "trigger_reason": self.trigger_reason,
            "trigger_metrics": self.trigger_metrics or {},
            "action_taken": self.action_taken,
            "auto_resolved": self.auto_resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by
        }
