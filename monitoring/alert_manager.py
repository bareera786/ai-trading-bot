"""
Alert manager for existing dashboard
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

class AlertManager:
    """Manages alerts for dashboard display"""

    def __init__(self):
        self.alerts: List[Dict] = []
        self.max_alerts = 50
        self.logger = logging.getLogger(__name__)

        # Alert thresholds (customize for your needs)
        self.thresholds = {
            'cpu': {'warning': 80, 'critical': 90},
            'memory': {'warning': 85, 'critical': 95},
            'disk': {'warning': 85, 'critical': 95},
            'load': {'warning': 5.0, 'critical': 7.0},
            'training_failed': {'warning': 1, 'critical': 3},
            'api_errors': {'warning': 5, 'critical': 10},
        }

    def check_system_alerts(self, system_metrics: Dict[str, Any]) -> List[Dict]:
        """Generate system alerts from metrics"""
        alerts = []

        # CPU alerts
        cpu = system_metrics.get('cpu_percent', 0)
        if cpu > self.thresholds['cpu']['critical']:
            alerts.append(self._create_alert(
                'critical', 'CPU',
                f'CPU usage critical: {cpu:.1f}%',
                'Pause training, check processes'
            ))
        elif cpu > self.thresholds['cpu']['warning']:
            alerts.append(self._create_alert(
                'warning', 'CPU',
                f'CPU usage high: {cpu:.1f}%',
                'Training using light models'
            ))

        # Memory alerts
        memory = system_metrics.get('memory_percent', 0)
        if memory > self.thresholds['memory']['critical']:
            alerts.append(self._create_alert(
                'critical', 'Memory',
                f'Memory usage critical: {memory:.1f}%',
                'Bot may pause, clearing cache'
            ))
        elif memory > self.thresholds['memory']['warning']:
            alerts.append(self._create_alert(
                'warning', 'Memory',
                f'Memory usage high: {memory:.1f}%',
                'Reducing batch sizes'
            ))

        # Load average alerts
        load = system_metrics.get('load_avg_1min', 0)
        if load > self.thresholds['load']['critical']:
            alerts.append(self._create_alert(
                'critical', 'System Load',
                f'System load critical: {load:.1f}',
                'Check for runaway processes'
            ))
        elif load > self.thresholds['load']['warning']:
            alerts.append(self._create_alert(
                'warning', 'System Load',
                f'System load high: {load:.1f}',
                'Training may be slow'
            ))

        # Add to alert history
        for alert in alerts:
            self.add_alert(alert)

        return alerts

    def _create_alert(self, level: str, category: str,
                     message: str, action: str) -> Dict:
        """Create standardized alert dictionary"""
        return {
            'id': f"{level}_{category}_{datetime.now().timestamp()}",
            'level': level,
            'category': category,
            'message': message,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'acknowledged': False,
        }

    def add_alert(self, alert: Dict):
        """Add alert to history"""
        self.alerts.append(alert)

        # Trim old alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

        # Log critical alerts
        if alert['level'] == 'critical':
            self.logger.critical(f"Critical alert: {alert['message']}")

    def get_alerts(self, level: Optional[str] = None, unacknowledged: bool = False) -> List[Dict]:
        """Get alerts with optional filters"""
        alerts = self.alerts

        if level:
            alerts = [a for a in alerts if a['level'] == level]

        if unacknowledged:
            alerts = [a for a in alerts if not a['acknowledged']]

        return sorted(alerts, key=lambda x: x['timestamp'], reverse=True)

    def acknowledge_alert(self, alert_id: str):
        """Mark alert as acknowledged"""
        for alert in self.alerts:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                break

    def clear_old_alerts(self, hours_old: int = 24):
        """Clear alerts older than specified hours"""
        cutoff = datetime.now().timestamp() - (hours_old * 3600)
        self.alerts = [
            a for a in self.alerts
            if datetime.fromisoformat(a['timestamp']).timestamp() > cutoff
        ]

    def get_alert_summary(self) -> Dict:
        """Get alert summary for dashboard"""
        critical = len(self.get_alerts('critical', unacknowledged=True))
        warning = len(self.get_alerts('warning', unacknowledged=True))

        return {
            'total_alerts': len(self.alerts),
            'critical_unacknowledged': critical,
            'warning_unacknowledged': warning,
            'latest_alert': self.alerts[-1] if self.alerts else None,
        }

# Integration with existing dashboard
def add_alerts_to_dashboard(dashboard_app, alert_manager: AlertManager):
    """Add alert endpoints to existing dashboard"""
    from flask import request

    # Check if routes already exist to avoid conflicts
    existing_routes = [rule.rule for rule in dashboard_app.url_map.iter_rules()]

    if '/api/alerts' not in existing_routes:
        @dashboard_app.route('/api/alerts')
        def get_alerts_api():
            level = request.args.get('level')
            unacknowledged = request.args.get('unacknowledged', 'false').lower() == 'true'

            alerts = alert_manager.get_alerts(level, unacknowledged)
            summary = alert_manager.get_alert_summary()

            return {
                'alerts': alerts,
                'summary': summary,
                'count': len(alerts),
            }

    if '/api/alerts/acknowledge/<alert_id>' not in [rule.rule for rule in dashboard_app.url_map.iter_rules()]:
        @dashboard_app.route('/api/alerts/acknowledge/<alert_id>', methods=['POST'])
        def acknowledge_alert_api(alert_id):
            alert_manager.acknowledge_alert(alert_id)
            return {'success': True, 'alert_id': alert_id}

    if '/api/alerts/summary' not in existing_routes:
        @dashboard_app.route('/api/alerts/summary')
        def alerts_summary_api():
            return alert_manager.get_alert_summary()