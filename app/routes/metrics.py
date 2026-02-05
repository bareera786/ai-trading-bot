from flask import Blueprint, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.services.brain_service import BrainService

metrics_bp = Blueprint('metrics', __name__)

@metrics_bp.route('/metrics')
def metrics():
    """
    Expose Prometheus metrics.
    Also force-update some dynamic gauges (like brain status) before scraping.
    """
    try:
        from app.services.metrics_service import MetricsService
        from app.models import TrainingJob
        from app.extensions import db

        # 1. Update Brain Status & Heartbeat
        status = BrainService.get_brain_status()
        MetricsService.update_heartbeat()
        MetricsService.set_pause_state(status.get("status") == "PAUSED")

        # 2. Update Job Counts (Expensive, but necessary for accuracy)
        # We use a fast count query
        running_jobs = db.session.query(TrainingJob).filter_by(status='running').count()
        MetricsService.TRAINING_JOBS_RUNNING.set(running_jobs)

        # Note: Failures are Counters, so we don't set them here as they are cumulative.
        # We rely on the increment calls in catch blocks.
        
    except Exception as e:
        # Don't fail the scrape if DB is down, but maybe log it?
        pass

    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)
