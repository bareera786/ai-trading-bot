# Dashboard Integration

This package provides seamless integration between your AI trading bot's monitoring system and existing dashboards.

## Features

- **Real-time System Monitoring**: CPU, memory, disk, NVMe I/O metrics
- **Trading Bot Metrics**: Status, P&L, active pairs, position sizes
- **Model Performance Tracking**: Current model, training status, performance scores
- **Intelligent Alerts**: Automatic alerts based on configurable system conditions
- **Health Scoring**: Overall system health score (0-100)
- **REST API Endpoints**: Easy integration with existing dashboards
- **WebSocket Support**: Real-time updates (if using SocketIO)
- **Configurable Thresholds**: Customize alert levels for your environment

## Quick Start

### 1. Basic Usage

```python
from config.resource_manager import ResourceManager
from integrations.dashboard_integration import DashboardExporter

# Initialize components
resource_manager = ResourceManager()
exporter = DashboardExporter(resource_manager)

# Export metrics
metrics = exporter.export_metrics()
print(f"System health: {exporter.get_system_health_score()}")
```

### 2. Configure for Your Environment

```python
from config.dashboard_config import DashboardConfig

# Create custom configuration
config = DashboardConfig()
config.endpoint = "https://your-dashboard.com/api/metrics"
config.api_key = "your-api-key"
config.update_interval = 10  # seconds

# Customize alert thresholds
config.thresholds = {
    'cpu_critical': 95,
    'cpu_warning': 85,
    'memory_critical': 98,
    'memory_warning': 90,
    'disk_warning': 95,
    'load_warning': 8.0,
}

# Create exporter with configuration
exporter = DashboardExporter(resource_manager, config)
```

### 3. Integrate with Existing Flask Dashboard

```python
from flask import Flask
from config.resource_manager import ResourceManager
from integrations.dashboard_integration import integrate_with_existing_dashboard
from config.dashboard_config import DashboardConfig

app = Flask(__name__)
resource_manager = ResourceManager()

# Create configuration
config = DashboardConfig()
config.endpoint = "https://your-dashboard.com/api/metrics"

# Add monitoring to your existing dashboard
integrate_with_existing_dashboard(app, resource_manager, config)

# Your existing routes continue to work...
@app.route('/')
def dashboard():
    return "Your dashboard"

if __name__ == '__main__':
    app.run()
```

### 4. New API Endpoints

After integration, these endpoints are automatically available:

- `GET /api/system-metrics` - Complete system and bot status
- `GET /api/resource-recommendations` - AI-powered optimization suggestions

## Configuration

### DashboardConfig Class

The `DashboardConfig` class allows you to customize all aspects of the monitoring system:

```python
from config.dashboard_config import DashboardConfig

config = DashboardConfig()

# Connection settings
config.endpoint = "https://your-dashboard.com/api/metrics"
config.api_key = "your-api-key"  # Optional
config.update_interval = 5  # seconds

# Monitoring options
config.monitor_system = True
config.monitor_training = True
config.monitor_trading = True
config.monitor_alerts = True

# Alert thresholds
config.thresholds = {
    'cpu_critical': 90,      # Critical alert at 90% CPU
    'cpu_warning': 80,       # Warning at 80% CPU
    'memory_critical': 95,   # Critical at 95% memory
    'memory_warning': 85,    # Warning at 85% memory
    'disk_warning': 90,      # Warning at 90% disk
    'load_warning': 6.0,     # Warning at load 6.0
}

# Widget controls
config.widgets = {
    'system_health': True,
    'resource_usage': True,
    'training_status': True,
    'trading_performance': True,
    'alerts_panel': True,
}
```

### Environment-Specific Configurations

```python
def create_config_for_env(env: str) -> DashboardConfig:
    config = DashboardConfig()

    if env == "production":
        config.endpoint = "https://prod-dashboard.com/api/metrics"
        config.update_interval = 10
        config.thresholds['cpu_critical'] = 95  # Stricter in prod
    elif env == "development":
        config.endpoint = "http://localhost:3000/api/metrics"
        config.update_interval = 2  # Faster updates in dev
        config.thresholds['cpu_warning'] = 50  # Lower threshold in dev

    return config
```

### Creating Config from URL

```python
from config.dashboard_config import DashboardConfig

# Automatically creates endpoint: https://my-dashboard.com/api/metrics
config = DashboardConfig.from_dashboard_url("https://my-dashboard.com")
```

## Metrics Included

### System Metrics
- CPU usage percentage
- Memory usage and available GB
- System load average
- Disk usage percentage
- NVMe read/write speeds

### Bot Metrics
- Bot status (running, high_load, high_memory, etc.)
- Active trading pairs
- Daily trade count and P&L
- Current position sizes

### Model Metrics
- Current active model
- Model performance score
- Last training time
- Training queue size

### Training Metrics
- Training status and progress
- Estimated completion time
- CPU cores used for training

### Alert System
- Critical alerts (configurable thresholds)
- Warning alerts (configurable thresholds)
- Actionable recommendations

## Integration with Main Bot

To integrate with your main trading bot:

```python
from main import AITradingBot
from config.dashboard_config import DashboardConfig

class EnhancedTradingBot(AITradingBot):
    def __init__(self, dashboard_config: DashboardConfig = None):
        super().__init__()

        # Use custom configuration
        if dashboard_config:
            self.dashboard_config = dashboard_config
            self.dashboard_exporter = DashboardExporter(
                self.resource_manager, dashboard_config
            )

    def trading_loop(self):
        while self.running:
            # Your existing trading logic...

            # Export metrics with custom configuration
            trading_data = {
                'pairs_active': len(self.active_pairs),
                'trades_today': self.daily_trade_count,
                'daily_pnl': self.calculate_daily_pnl(),
                'position_size': self.get_total_position_size()
            }

            self.dashboard_exporter.export_metrics(
                self.training_scheduler,
                trading_data
            )
```

## Health Score Calculation

The health score is calculated as a weighted average:
- CPU: 30% (100 - cpu_percent)
- Memory: 30% (100 - memory_percent)
- Load: 20% (100 - min(load_avg * 20, 100))
- Disk: 20% (100 - disk_usage_percent)

Scores range from 0-100, where 100 is perfect health.

## Example Response

```json
{
  "metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 67.8,
    "memory_available_gb": 5.2,
    "bot_status": "running",
    "trading_pairs_active": 3,
    "daily_pnl_percent": 2.5,
    "alerts": [
      {
        "type": "warning",
        "message": "Memory usage high: 67.8%",
        "action": "Training batch size reduced"
      }
    ]
  },
  "health_score": 78.5,
  "timestamp": "2025-12-28T10:30:00"
}
```

## Security Considerations

- Use HTTPS endpoints in production
- Store API keys securely (environment variables)
- Consider authentication for dashboard endpoints
- Rate limit API calls to prevent abuse
- Validate configuration values on startup