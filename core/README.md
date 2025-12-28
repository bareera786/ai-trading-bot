# Optimized Bot Integration

The `OptimizedTradingBot` class provides a wrapper that adds resource optimization to your existing trading bot with minimal code changes.

## Quick Start

### 1. Wrap Your Existing Bot

```python
from core.optimized_bot import OptimizedTradingBot
from your_existing_bot import YourTradingBot

# Your existing bot
existing_bot = YourTradingBot()

# Wrap with optimizations
optimized_bot = OptimizedTradingBot(existing_bot)

# Run with optimizations
optimized_bot.run_optimized()
```

### 2. Automatic Method Patching

The wrapper automatically patches your bot's methods:

- `train_model()` → `optimized_train()` (resource-aware training)
- `execute_trade()` → `optimized_trade()` (resource-aware trading)

Your existing code continues to work unchanged!

### 3. Monitor Optimization Status

```python
# Get optimization status for dashboard
status = optimized_bot.get_optimization_status()

print(f"CPU Limit: {status['resource_limits']['max_cpu']}%")
print(f"Training Cores: {status['resource_limits']['training_cores']}")
print(f"Current CPU: {status['current_resources']['cpu_percent']}%")
```

## Features Added

### Resource Management
- **CPU Affinity**: Automatic CPU core assignment for training vs trading
- **Memory Limits**: Prevents memory exhaustion during training
- **Timeout Protection**: Training operations can't run indefinitely

### Smart Scheduling
- **Market Hours Training**: Trains only during optimal market conditions
- **Load Balancing**: Defers training during high system load
- **Background Processing**: Training runs in background threads

### Real-time Monitoring
- **System Metrics**: CPU, memory, disk usage tracking
- **Training Metrics**: Duration, success rate, resource usage
- **Trading Metrics**: Success/failure rates, resource impact

## Configuration

### Default Resource Limits
- **CPU Training Limit**: 70%
- **Memory Training Limit**: 80%
- **Training Timeout**: 300 seconds (5 minutes)
- **Training Cores**: [4, 5, 6, 7] (last 4 cores)
- **Trading Cores**: [0, 1, 2, 3] (first 4 cores)

### Custom Configuration

```python
from core.optimized_bot import OptimizedTradingBot
from config.resource_manager import ResourceManager

# Create custom resource manager
rm = ResourceManager()
rm.max_cpu_percent = 60  # Lower CPU limit
rm.training_cores = [6, 7]  # Use only 2 cores for training

# Create optimized bot with custom config
optimized_bot = OptimizedTradingBot(existing_bot)
optimized_bot.resource_manager = rm  # Override default
```

## Integration Examples

### With Flask Dashboard

```python
from flask import Flask
from core.optimized_bot import OptimizedTradingBot
from integrations.dashboard_integration import integrate_with_existing_dashboard

app = Flask(__name__)

# Your existing bot
bot = YourTradingBot()
optimized_bot = OptimizedTradingBot(bot)

# Add optimization status endpoint
@app.route('/api/optimization-status')
def optimization_status():
    return optimized_bot.get_optimization_status()

# Integrate monitoring
integrate_with_existing_dashboard(app, optimized_bot.resource_manager)

if __name__ == '__main__':
    # Start optimized bot in background
    import threading
    bot_thread = threading.Thread(target=optimized_bot.run_optimized, daemon=True)
    bot_thread.start()
    
    # Run dashboard
    app.run()
```

### With Existing Main Loop

```python
# Your existing main.py
def main():
    bot = YourTradingBot()
    
    # Wrap with optimizations
    from core.optimized_bot import OptimizedTradingBot
    optimized_bot = OptimizedTradingBot(bot)
    
    # Your existing logic continues to work
    while True:
        # These calls now use optimized versions
        bot.train_model()  # Actually calls optimized_train()
        bot.execute_trade()  # Actually calls optimized_trade()
        
        time.sleep(60)

if __name__ == '__main__':
    main()
```

## Benefits

### Minimal Code Changes
- Add just 2-3 lines to wrap your existing bot
- All existing method calls work unchanged
- No refactoring required

### Automatic Optimizations
- Resource limits prevent system overload
- Smart scheduling improves performance
- Real-time monitoring provides insights

### Production Ready
- Error handling and recovery
- Background processing
- Configurable for different environments

## Troubleshooting

### CPU Affinity Warnings
If you see CPU affinity warnings on macOS, this is normal. The optimization still works but CPU pinning isn't available on macOS.

### Training Deferral
Training may be deferred during high system load. Check logs for "Training deferred due to system load" messages.

### Resource Limits
If training fails due to resource limits, the system automatically retries during the next optimal window.