# Quick Integration Guide

The `quick_integration.py` script provides the **fastest way** to add optimization to your existing AI trading bot with **minimal code changes**.

## 🚀 Quick Start (2 Minutes)

### Step 1: Add to Your Main File

Add this to the top of your existing `main.py` or bot file:

```python
# Add at the very top of your file
from quick_integration import add_optimization_to_existing_bot

# Initialize optimization
optimization = add_optimization_to_existing_bot()
```

### Step 2: Wrap Your Functions (Optional)

If you want automatic optimization, wrap your training and trading functions:

```python
# Wrap your existing training function
your_train_function = optimization['wrap_training'](your_train_function)

# Wrap your existing trading function
your_trade_function = optimization['wrap_trading'](your_trade_function)
```

### Step 3: Add Metrics Export

Add this to your main trading loop:

```python
while True:
    # Your existing trading logic...
    your_trade_function()
    
    # Export metrics every 5 seconds
    optimization['export_metrics']()
    time.sleep(5)
```

## 📊 What You Get

### Automatic Optimizations
- **Resource Monitoring**: CPU, memory, disk usage tracking
- **Smart Training**: Only trains during optimal market hours
- **Safety Limits**: Prevents system overload
- **Background Processing**: Non-blocking optimization tasks

### Real-time Metrics
- System health scores
- Training performance tracking
- Resource usage statistics
- Automatic dashboard export

## 🔧 Manual Integration (Advanced)

If you prefer more control, access individual components:

```python
# Get individual components
resource_manager = optimization['resource_manager']
training_scheduler = optimization['training_scheduler']
dashboard_exporter = optimization['dashboard_exporter']

# Use them directly in your code
if resource_manager.is_safe_for_training():
    # Safe to train
    pass

if training_scheduler.is_training_window():
    # Good time to train
    pass

# Export custom metrics
dashboard_exporter.export_metrics(training_scheduler, custom_data)
```

## 📈 Integration Examples

### Example 1: Basic Integration

```python
# main.py
from quick_integration import add_optimization_to_existing_bot

# Initialize
optimization = add_optimization_to_existing_bot()

def my_train_function(data):
    # Your training logic
    return train_model(data)

def my_trade_function(symbol, amount):
    # Your trading logic
    return execute_trade(symbol, amount)

# Wrap functions (optional)
my_train_function = optimization['wrap_training'](my_train_function)
my_trade_function = optimization['wrap_trading'](my_trade_function)

# Main loop
while True:
    # Your trading logic
    result = my_trade_function('BTCUSDT', 0.001)
    
    # Export metrics
    optimization['export_metrics']()
    time.sleep(5)
```

### Example 2: Flask Dashboard Integration

```python
from flask import Flask
from quick_integration import add_optimization_to_existing_bot

app = Flask(__name__)
optimization = add_optimization_to_existing_bot()

@app.route('/api/system-metrics')
def get_metrics():
    return optimization['export_metrics']()

@app.route('/api/optimization-status')
def get_status():
    rm = optimization['resource_manager']
    ts = optimization['training_scheduler']
    
    return {
        'resources': rm.get_system_resources().__dict__,
        'training_window': ts.is_training_window(),
        'last_training': ts.last_training_time
    }

if __name__ == '__main__':
    app.run()
```

### Example 3: Custom Training Logic

```python
from quick_integration import add_optimization_to_existing_bot

optimization = add_optimization_to_existing_bot()
rm = optimization['resource_manager']
ts = optimization['training_scheduler']

def smart_train():
    # Check if we should train
    if not ts._should_train():
        print("Skipping training - not optimal time")
        return
    
    # Check resources
    if not rm.is_safe_for_training():
        print("Skipping training - system busy")
        return
    
    # Train with resource limits
    @rm.enforce_limits(timeout_seconds=600)
    def safe_training():
        return your_training_function()
    
    result = safe_training()
    optimization['export_metrics']()
    return result
```

## ⚙️ Configuration

### Default Settings
- **CPU Limit**: 70% for training
- **Memory Limit**: 80% for training
- **Training Timeout**: 300 seconds
- **Training Cores**: [4, 5, 6, 7]
- **Trading Cores**: [0, 1, 2, 3]

### Custom Configuration

```python
from quick_integration import add_optimization_to_existing_bot
from config.resource_manager import ResourceManager

# Create custom resource manager
custom_rm = ResourceManager(
    max_cpu_percent=60.0,      # Lower CPU limit
    max_memory_percent=75.0,   # Lower memory limit
    training_cores=[6, 7],     # Use only 2 cores
    trading_cores=[0, 1, 2, 3, 4, 5]  # Use more cores for trading
)

# Use custom manager
optimization = add_optimization_to_existing_bot()
optimization['resource_manager'] = custom_rm
```

## 🔍 Monitoring & Debugging

### Check System Status

```python
optimization = add_optimization_to_existing_bot()

# Get current system status
metrics = optimization['export_metrics']()
print(f"CPU: {metrics['system']['cpu_percent']}%")
print(f"Memory: {metrics['system']['memory_percent']}%")
print(f"Training Window: {metrics['training']['in_window']}")
```

### Debug Training Decisions

```python
ts = optimization['training_scheduler']
rm = optimization['resource_manager']

print(f"Should train: {ts._should_train()}")
print(f"Safe for training: {rm.is_safe_for_training()}")
print(f"Training window: {ts.is_training_window()}")
print(f"System resources: {rm.get_system_resources().__dict__}")
```

## 🚨 Troubleshooting

### CPU Affinity Warnings
If you see CPU affinity warnings, this is normal on macOS. The optimization still works.

### Training Not Starting
Check if:
- System resources are within limits
- You're in a training window
- No other training is running

### Metrics Not Exporting
Ensure your dashboard endpoint is configured:
```python
from config.dashboard_config import DashboardConfig
config = DashboardConfig()
config.endpoint = "https://your-dashboard.com/api/metrics"
optimization['dashboard_exporter'] = DashboardExporter(optimization['resource_manager'], config)
```

## 🎯 Benefits

### Minimal Changes
- Add 3-5 lines to your existing code
- No refactoring required
- All existing functions work unchanged

### Maximum Performance
- Automatic resource optimization
- Smart training scheduling
- Real-time monitoring

### Production Ready
- Error handling and recovery
- Configurable for different environments
- Comprehensive logging

## 📚 Next Steps

1. **Basic Integration**: Add the quick integration to your main file
2. **Advanced Usage**: Use individual components for more control
3. **Dashboard Integration**: Connect to your existing monitoring system
4. **Custom Configuration**: Adjust settings for your specific environment

The quick integration script gives you enterprise-grade optimization with minimal effort!