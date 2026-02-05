from prometheus_client import Gauge, Counter

class MetricsService:
    """
    Centralized Prometheus Metrics Registry.
    """
    # 1. BRAIN HEALTH
    BRAIN_HEARTBEAT = Gauge('brain_heartbeat', 'Unix timestamp of last health check')
    BRAIN_SIGNALS_PAUSED = Gauge('brain_signals_paused', '1 if Global Kill Switch is ACTIVE, 0 otherwise')
    
    # 2. TRAINING
    TRAINING_JOBS_RUNNING = Gauge('training_jobs_running', 'Number of active training jobs')
    TRAINING_JOB_FAILURES_TOTAL = Counter('training_job_failures_total', 'Total number of failed training jobs')
    
    # 3. SIGNALS
    SIGNAL_PUBLISH_COUNT = Counter('signal_publish_count', 'Total trade signals published')

    @staticmethod
    def update_heartbeat():
        import time
        MetricsService.BRAIN_HEARTBEAT.set(time.time())

    @staticmethod
    def set_pause_state(is_paused: bool):
        MetricsService.BRAIN_SIGNALS_PAUSED.set(1 if is_paused else 0)

    @staticmethod
    def record_job_failure():
        MetricsService.TRAINING_JOB_FAILURES_TOTAL.inc()

    @staticmethod
    def record_signal_publish():
        MetricsService.SIGNAL_PUBLISH_COUNT.inc()
