"""
Configuration for dashboard integration
"""
from typing import Optional, Dict, Any

class DashboardConfig:
    """Configuration for existing dashboard"""

    def __init__(self):
        # Dashboard connection
        self.endpoint: str = "http://localhost:3000/api/metrics"  # Your dashboard endpoint
        self.api_key: Optional[str] = None  # If your dashboard requires authentication
        self.update_interval: int = 5  # seconds

        # What to monitor
        self.monitor_system: bool = True
        self.monitor_training: bool = True
        self.monitor_trading: bool = True
        self.monitor_alerts: bool = True

        # Alert thresholds
        self.thresholds: Dict[str, float] = {
            'cpu_critical': 90,
            'cpu_warning': 80,
            'memory_critical': 95,
            'memory_warning': 85,
            'disk_warning': 90,
            'load_warning': 6.0,
        }

        # Dashboard widgets to update
        self.widgets: Dict[str, bool] = {
            'system_health': True,
            'resource_usage': True,
            'training_status': True,
            'trading_performance': True,
            'alerts_panel': True,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith('_')
        }

    @classmethod
    def from_dashboard_url(cls, dashboard_url: str) -> 'DashboardConfig':
        """Create config from dashboard URL"""
        config = cls()
        config.endpoint = f"{dashboard_url.rstrip('/')}/api/metrics"
        return config