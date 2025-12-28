"""
Integration module for existing dashboard with new monitoring
"""
import json
import time
import threading
from typing import Dict, Any, Optional
import logging
from dataclasses import dataclass, asdict
from datetime import datetime

from config.resource_manager import ResourceManager, SystemResources
from training.smart_trainer import SmartTrainingScheduler
from config.dashboard_config import DashboardConfig
from monitoring.alert_manager import AlertManager

@dataclass
class DashboardMetrics:
    """Standardized metrics for dashboard integration"""
    # System Metrics
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    load_avg_1min: float
    disk_usage_percent: float
    nvme_read_mb_s: float
    nvme_write_mb_s: float

    # Bot Metrics
    bot_status: str  # "running", "paused", "training", "error"
    trading_pairs_active: int
    total_trades_today: int
    daily_pnl_percent: float
    current_position_size: float

    # Model Metrics
    current_model: str
    model_performance: float
    last_training_time: str
    training_queue_size: int

    # Training Metrics
    is_training: bool
    training_progress: float  # 0-100
    estimated_training_completion: str
    training_cores_used: int

    # Alert Metrics
    alerts: list
    warnings: list
    errors: list

    @classmethod
    def from_components(cls,
                       resource_manager: ResourceManager,
                       training_scheduler: Optional[SmartTrainingScheduler] = None,
                       trading_data: Optional[Dict] = None):
        """Create metrics from system components"""

        # Get system resources
        resources = resource_manager.get_system_resources()

        # Default trading data
        trading_data = trading_data or {
            'pairs_active': 0,
            'trades_today': 0,
            'daily_pnl': 0.0,
            'position_size': 0.0
        }

        # Determine bot status
        bot_status = "running"
        if resources.cpu_percent > 85:
            bot_status = "high_load"
        elif resources.memory_percent > 90:
            bot_status = "high_memory"

        # Training info
        if training_scheduler:
            is_training = time.time() - training_scheduler.last_training_time < 300
            training_progress = 0.0  # Calculate based on your training
        else:
            is_training = False
            training_progress = 0.0

        return cls(
            # System
            cpu_percent=resources.cpu_percent,
            memory_percent=resources.memory_percent,
            memory_available_gb=resources.memory_available_gb,
            load_avg_1min=resources.load_avg_1min,
            disk_usage_percent=resources.disk_usage_percent,
                nvme_read_mb_s=resources.nvme_read_mb,
                nvme_write_mb_s=resources.nvme_write_mb,

            # Bot
            bot_status=bot_status,
            trading_pairs_active=trading_data['pairs_active'],
            total_trades_today=trading_data['trades_today'],
            daily_pnl_percent=trading_data['daily_pnl'],
            current_position_size=trading_data['position_size'],

            # Model
            current_model=(training_scheduler.current_model_id 
                          if training_scheduler and training_scheduler.current_model_id 
                          else "No model loaded"),
            model_performance=training_scheduler.best_performance if training_scheduler else 0.0,
            last_training_time=datetime.fromtimestamp(
                training_scheduler.last_training_time
            ).strftime("%H:%M") if training_scheduler and training_scheduler.last_training_time > 0 else "Never",
            training_queue_size=len(training_scheduler.model_versions) if training_scheduler else 0,

            # Training
            is_training=is_training,
            training_progress=training_progress,
            estimated_training_completion="N/A",
            training_cores_used=len(resource_manager.training_cores),

            # Alerts
            alerts=[],
            warnings=[],
            errors=[]
        )

class DashboardExporter:
    """Exports metrics to existing dashboard"""
    
    def __init__(self, 
                 resource_manager: ResourceManager,
                 dashboard_config: Optional[DashboardConfig] = None):
        self.rm = resource_manager
        self.config = dashboard_config or DashboardConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize alert manager
        self.alert_manager = AlertManager()
        
        # Sync alert manager thresholds with dashboard config
        self._sync_alert_thresholds()

        # Cache for rate limiting
        self.last_export_time = 0
        # Last exported metrics cache
        self.last_metrics: Dict[str, Any] = {}
        # Lock for thread-safety when exporting metrics
        self._export_lock = threading.Lock()
    
    def _sync_alert_thresholds(self):
        """Sync alert manager thresholds with dashboard config"""
        self.alert_manager.thresholds.update({
            'cpu': {
                'warning': self.config.thresholds.get('cpu_warning', 80),
                'critical': self.config.thresholds.get('cpu_critical', 90)
            },
            'memory': {
                'warning': self.config.thresholds.get('memory_warning', 85),
                'critical': self.config.thresholds.get('memory_critical', 95)
            },
            'disk': {
                'warning': self.config.thresholds.get('disk_warning', 85),
                'critical': self.config.thresholds.get('disk_critical', 95)
            },
            'load': {
                'warning': self.config.thresholds.get('load_warning', 5.0),
                'critical': self.config.thresholds.get('load_critical', 7.0)
            }
        })

    def export_metrics(self,
                      training_scheduler: Optional[SmartTrainingScheduler] = None,
                      trading_data: Optional[Dict] = None,
                      force: bool = False) -> Dict[str, Any]:
        """Export current metrics for dashboard"""

        # Rate limiting using config
        current_time = time.time()
        # If not forcing and within update interval, return cached metrics
        if not force and (current_time - self.last_export_time) < self.config.update_interval:
            return self.last_metrics or {}

        try:
            # Create metrics
            metrics = DashboardMetrics.from_components(
                self.rm, training_scheduler, trading_data
            )

            # Add alerts based on conditions (using config thresholds)
            if self.config.monitor_alerts:
                # Convert metrics to dict for alert manager
                system_metrics = {
                    'cpu_percent': metrics.cpu_percent,
                    'memory_percent': metrics.memory_percent,
                    'memory_available_gb': metrics.memory_available_gb,
                    'load_avg_1min': metrics.load_avg_1min,
                    'disk_usage_percent': metrics.disk_usage_percent,
                }
                
                # Generate alerts using alert manager
                alerts = self.alert_manager.check_system_alerts(system_metrics)
                metrics.alerts = alerts

            # Convert to dictionary
            metrics_dict = asdict(metrics)

            # Add timestamp
            metrics_dict['timestamp'] = datetime.now().isoformat()
            metrics_dict['server_time'] = time.time()

            # Export to dashboard using config endpoint (run in background to avoid slowing API)
            try:
                # send in background thread if endpoint configured
                if self.config.endpoint:
                    t = threading.Thread(target=self._send_to_dashboard, args=(metrics_dict,), daemon=True)
                    t.start()
                else:
                    # If no endpoint, log synchronously
                    self._send_to_dashboard(metrics_dict)
            except Exception:
                # fallback to synchronous send
                self._send_to_dashboard(metrics_dict)

            # Update cache time and last metrics
            with self._export_lock:
                self.last_export_time = current_time
                self.last_metrics = metrics_dict

            return metrics_dict

        except Exception as e:
            self.logger.error(f"Failed to export metrics: {e}")
            return {}

    def _send_to_dashboard(self, metrics: Dict[str, Any]):
        """Send metrics to existing dashboard using config"""
        if not self.config.endpoint:
            # Log locally if no endpoint configured
            self.logger.debug(f"Dashboard metrics: {json.dumps(metrics, default=str)}")
            return

        try:
            # Example: Send via HTTP POST
            import requests
            
            headers = {}
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            
            response = requests.post(
                self.config.endpoint,
                json=metrics,
                headers=headers,
                timeout=2
            )

            if response.status_code != 200:
                self.logger.warning(f"Dashboard POST failed: {response.status_code}")

        except ImportError:
            self.logger.warning("requests module not installed, skipping HTTP export")
        except Exception as e:
            self.logger.debug(f"Could not send to dashboard: {e}")

    def get_system_health_score(self) -> float:
        """Calculate overall system health score (0-100)"""
        resources = self.rm.get_system_resources()

        # Weighted score calculation
        scores = {
            'cpu': max(0, 100 - resources.cpu_percent),
            'memory': max(0, 100 - resources.memory_percent),
            'load': max(0, 100 - min(resources.load_avg_1min * 20, 100)),  # Load >5 = 0
            'disk': max(0, 100 - resources.disk_usage_percent)
        }

        # Weighted average
        weights = {'cpu': 0.3, 'memory': 0.3, 'load': 0.2, 'disk': 0.2}
        health_score = sum(scores[k] * weights[k] for k in scores)

        return round(health_score, 1)

    def export_training_metrics(self, training_data: Dict[str, Any]):
        """Export training-specific metrics"""
        metrics = {
            'type': 'training_update',
            'timestamp': datetime.now().isoformat(),
            'data': training_data
        }

        self._send_to_dashboard(metrics)

    def export_trade_metrics(self, trade_data: Dict[str, Any]):
        """Export trade execution metrics"""
        metrics = {
            'type': 'trade_execution',
            'timestamp': datetime.now().isoformat(),
            'data': trade_data
        }

        self._send_to_dashboard(metrics)

# Quick integration for existing dashboard
def integrate_with_existing_dashboard(dashboard_app, resource_manager, dashboard_config=None):
    """
    Add new monitoring endpoints to existing dashboard

    Usage in your existing dashboard:
    from integrations.dashboard_integration import integrate_with_existing_dashboard
    integrate_with_existing_dashboard(app, resource_manager, dashboard_config)
    """

    config = dashboard_config or DashboardConfig()
    exporter = DashboardExporter(resource_manager, config)

    # Check if routes already exist to avoid conflicts
    existing_routes = [rule.rule for rule in dashboard_app.url_map.iter_rules()]

    # Add new endpoint for system metrics
    if '/api/system-metrics' not in existing_routes:
        @dashboard_app.route('/api/system-metrics')
        def get_system_metrics():
            # allow forcing a fresh read with ?force=1
            from flask import request

            force = request.args.get('force', '0') in ('1', 'true', 'True')

            # use the exporter instance created above so config is respected
            metrics = exporter.export_metrics(force=force)
            health_score = exporter.get_system_health_score()

            return {
                'metrics': metrics,
                'health_score': health_score,
                'timestamp': datetime.now().isoformat()
            }

    # Add endpoint for resource recommendations
    if '/api/resource-recommendations' not in existing_routes:
        @dashboard_app.route('/api/resource-recommendations')
        def get_recommendations():
            resources = resource_manager.get_system_resources()
            recommendations = []

            if resources.cpu_percent > 80:
                recommendations.append({
                    'priority': 'high',
                    'action': 'Reduce training frequency',
                    'details': 'CPU usage is high, consider increasing training intervals'
                })

            if resources.memory_percent > 85:
                recommendations.append({
                    'priority': 'high',
                    'action': 'Clear memory cache',
                    'details': 'Memory usage is critical, old data will be cleared'
                })

            if resources.disk_usage_percent > 90:
                recommendations.append({
                    'priority': 'medium',
                    'action': 'Cleanup old models',
                    'details': 'Disk space is running low'
                })

            return {'recommendations': recommendations}

    # Add alert endpoints using alert manager
    from monitoring.alert_manager import add_alerts_to_dashboard
    add_alerts_to_dashboard(dashboard_app, exporter.alert_manager)

    # Add WebSocket endpoint for real-time updates
    if hasattr(dashboard_app, 'socketio'):  # If using SocketIO
        @dashboard_app.socketio.on('connect')
        def handle_connect():
            print('Dashboard client connected')

        @dashboard_app.socketio.on('request_metrics')
        def handle_metrics_request():
            # ensure only one background thread sends continuous metrics
            if getattr(dashboard_app, '_metrics_thread_running', False):
                return

            def send_continuous_metrics():
                dashboard_app._metrics_thread_running = True
                try:
                    while True:
                        metrics = exporter.export_metrics()
                        dashboard_app.socketio.emit('metrics_update', metrics)
                        time.sleep(5)
                finally:
                    dashboard_app._metrics_thread_running = False

            thread = threading.Thread(target=send_continuous_metrics, daemon=True)
            thread.start()