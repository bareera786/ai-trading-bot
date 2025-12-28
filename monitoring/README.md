# Alert Manager Documentation

The `AlertManager` provides comprehensive alert management for your AI trading bot dashboard, with automatic system monitoring, customizable thresholds, and real-time alert handling.

## 🚨 Features

### Alert Types
- **Critical Alerts**: Immediate action required (CPU >90%, Memory >95%)
- **Warning Alerts**: Monitor closely (CPU >80%, Memory >85%)
- **Info Alerts**: General notifications

### Alert Management
- **Automatic Generation**: Based on system metrics and configurable thresholds
- **Acknowledgment System**: Mark alerts as acknowledged
- **Filtering & Search**: Filter by level, category, acknowledgment status
- **History Management**: Automatic cleanup of old alerts
- **Summary Reports**: Dashboard-ready alert summaries

### Integration
- **Dashboard Endpoints**: REST API for alert management
- **Real-time Updates**: WebSocket support for live alerts
- **Configurable Thresholds**: Customize alert levels per environment

## 📊 Quick Start

### Basic Usage

```python
from monitoring.alert_manager import AlertManager

# Initialize alert manager
alert_manager = AlertManager()

# Check system for alerts
system_metrics = {
    'cpu_percent': 95.0,
    'memory_percent': 88.0,
    'load_avg_1min': 6.5
}

alerts = alert_manager.check_system_alerts(system_metrics)
print(f"Generated {len(alerts)} alerts")
```

### Flask Dashboard Integration

```python
from flask import Flask
from monitoring.alert_manager import AlertManager, add_alerts_to_dashboard

app = Flask(__name__)
alert_manager = AlertManager()

# Add alert endpoints to your dashboard
add_alerts_to_dashboard(app, alert_manager)

# Routes added automatically:
# GET /api/alerts - Get alerts with filtering
# POST /api/alerts/acknowledge/<alert_id> - Acknowledge alerts
# GET /api/alerts/summary - Alert summary
```

### With Dashboard Integration

```python
from integrations.dashboard_integration import integrate_with_existing_dashboard
from config.resource_manager import ResourceManager

# This automatically includes alert management
integrate_with_existing_dashboard(app, resource_manager, dashboard_config)
```

## ⚙️ Configuration

### Default Thresholds

```python
alert_manager = AlertManager()

# Default thresholds
alert_manager.thresholds = {
    'cpu': {'warning': 80, 'critical': 90},
    'memory': {'warning': 85, 'critical': 95},
    'disk': {'warning': 85, 'critical': 95},
    'load': {'warning': 5.0, 'critical': 7.0},
    'training_failed': {'warning': 1, 'critical': 3},
    'api_errors': {'warning': 5, 'critical': 10},
}
```

### Custom Thresholds

```python
# Customize for your environment
alert_manager.thresholds['cpu']['critical'] = 95  # Higher tolerance
alert_manager.thresholds['memory']['warning'] = 90  # Lower warning
```

### Dashboard Config Integration

```python
from config.dashboard_config import DashboardConfig

config = DashboardConfig()
config.thresholds.update({
    'cpu_warning': 75,
    'cpu_critical': 85,
    'memory_warning': 80,
    'memory_critical': 90,
})

# Alert manager automatically uses these thresholds
exporter = DashboardExporter(resource_manager, config)
```

## 📡 API Endpoints

### Get Alerts

```http
GET /api/alerts?level=critical&unacknowledged=true
```

**Parameters:**
- `level`: `critical`, `warning`, or omit for all
- `unacknowledged`: `true` for unacknowledged only

**Response:**
```json
{
  "alerts": [
    {
      "id": "critical_CPU_1640000000.123",
      "level": "critical",
      "category": "CPU",
      "message": "CPU usage critical: 95.2%",
      "action": "Pause training, check processes",
      "timestamp": "2023-12-20T10:30:00.123456",
      "acknowledged": false
    }
  ],
  "summary": {
    "total_alerts": 5,
    "critical_unacknowledged": 2,
    "warning_unacknowledged": 1,
    "latest_alert": {...}
  },
  "count": 3
}
```

### Acknowledge Alert

```http
POST /api/alerts/acknowledge/critical_CPU_1640000000.123
```

**Response:**
```json
{
  "success": true,
  "alert_id": "critical_CPU_1640000000.123"
}
```

### Alert Summary

```http
GET /api/alerts/summary
```

**Response:**
```json
{
  "total_alerts": 5,
  "critical_unacknowledged": 2,
  "warning_unacknowledged": 1,
  "latest_alert": {
    "id": "warning_Memory_1640000000.456",
    "level": "warning",
    "category": "Memory",
    "message": "Memory usage high: 87.3%",
    "timestamp": "2023-12-20T10:35:00.456789"
  }
}
```

## 🔍 Alert Categories

### System Alerts
- **CPU**: High CPU usage affecting performance
- **Memory**: Memory pressure requiring attention
- **Disk**: Storage space running low
- **Load**: System load average too high

### Bot Alerts
- **Training Failed**: Model training failures
- **API Errors**: External API communication issues
- **Trading Errors**: Trade execution problems

## 🛠️ Advanced Usage

### Manual Alert Creation

```python
alert = alert_manager._create_alert(
    level='warning',
    category='Custom',
    message='Custom alert message',
    action='Recommended action'
)

alert_manager.add_alert(alert)
```

### Alert History Management

```python
# Get all alerts
all_alerts = alert_manager.get_alerts()

# Get critical alerts only
critical = alert_manager.get_alerts('critical')

# Get unacknowledged alerts
unacked = alert_manager.get_alerts(unacknowledged=True)

# Clear old alerts (older than 24 hours)
alert_manager.clear_old_alerts(hours_old=24)
```

### Custom Alert Logic

```python
class CustomAlertManager(AlertManager):
    def check_custom_alerts(self, custom_metrics):
        alerts = []
        
        if custom_metrics.get('model_accuracy', 1.0) < 0.5:
            alerts.append(self._create_alert(
                'critical', 'Model',
                'Model accuracy critically low',
                'Retraining recommended'
            ))
        
        # Add to alert history
        for alert in alerts:
            self.add_alert(alert)
        
        return alerts
```

## 📊 Dashboard Integration Examples

### Real-time Alert Updates

```javascript
// Frontend JavaScript
function updateAlerts() {
    fetch('/api/alerts/summary')
        .then(response => response.json())
        .then(data => {
            document.getElementById('critical-count').textContent = data.critical_unacknowledged;
            document.getElementById('warning-count').textContent = data.warning_unacknowledged;
            
            if (data.latest_alert) {
                showNotification(data.latest_alert);
            }
        });
}

// Update every 30 seconds
setInterval(updateAlerts, 30000);
```

### Alert Acknowledgment

```javascript
function acknowledgeAlert(alertId) {
    fetch(`/api/alerts/acknowledge/${alertId}`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Remove from UI or mark as acknowledged
                updateAlerts();
            }
        });
}
```

## 🚨 Alert Actions

### Critical Alerts
- **CPU Critical**: Pause training, investigate processes
- **Memory Critical**: Clear caches, reduce batch sizes
- **Load Critical**: Check for runaway processes

### Warning Alerts
- **CPU High**: Switch to light models
- **Memory High**: Reduce concurrent operations
- **Disk High**: Clean up old models/logs

## 🔧 Troubleshooting

### No Alerts Generated
- Check system metrics are being passed correctly
- Verify thresholds are appropriate for your system
- Ensure alert manager is properly initialized

### Too Many Alerts
- Increase threshold values
- Use acknowledgment to clear old alerts
- Implement alert cooldown periods

### Alerts Not Showing in Dashboard
- Verify Flask routes are registered
- Check API endpoint responses
- Ensure frontend is calling correct endpoints

## 📈 Performance

- **Memory Usage**: Minimal (stores last 50 alerts by default)
- **CPU Overhead**: Negligible (simple threshold checks)
- **Storage**: Automatic cleanup prevents unbounded growth
- **API Response**: Sub-millisecond for typical alert volumes

## 🔒 Security

- Alert IDs are timestamp-based (not sensitive)
- No authentication required for read operations
- Consider adding authentication for acknowledgment
- Alert messages are sanitized for display

## 🎯 Best Practices

1. **Set Appropriate Thresholds**: Tune for your specific environment
2. **Regular Acknowledgment**: Clear alerts you've addressed
3. **Monitor Trends**: Use alert history for system health insights
4. **Automate Responses**: Consider automatic actions for critical alerts
5. **Log Critical Events**: Critical alerts are automatically logged

The alert manager provides enterprise-grade monitoring capabilities with minimal configuration, ensuring your trading bot stays healthy and responsive!