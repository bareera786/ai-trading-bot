"""
Quick integration script - minimal changes to your existing code
Run this to add optimization to your bot
"""
import sys
import os

# Add to your main script (usually at the top of your bot's main file)
def add_optimization_to_existing_bot():
    """
    Add this function to your existing main.py file
    Call it before starting your bot
    """

    # Add these imports
    from config.resource_manager import ResourceManager
    from training.smart_trainer import SmartTrainingScheduler
    from integrations.dashboard_integration import DashboardExporter, integrate_with_existing_dashboard

    # Initialize optimization components
    resource_manager = ResourceManager()
    training_scheduler = SmartTrainingScheduler(resource_manager)
    dashboard_exporter = DashboardExporter(resource_manager)

    # Patch training functions
    def wrap_training(original_train_func):
        def optimized_train(*args, **kwargs):
            # Check resources
            if not training_scheduler._should_train():
                print("Training deferred - system resources low")
                return None

            # Apply limits
            from functools import wraps
            @resource_manager.enforce_limits(timeout_seconds=300)
            @wraps(original_train_func)
            def limited_training(*args, **kwargs):
                return original_train_func(*args, **kwargs)

            return limited_training(*args, **kwargs)
        return optimized_train

    # Patch trading functions
    def wrap_trading(original_trade_func):
        def optimized_trade(*args, **kwargs):
            # Set CPU affinity for trading
            resource_manager.set_cpu_affinity(for_training=False)

            # Execute trade
            return original_trade_func(*args, **kwargs)
        return optimized_trade

    # Export to your dashboard
    def export_metrics_to_dashboard():
        """Call this periodically in your main loop"""
        import time
        from datetime import datetime

        metrics = {
            'timestamp': datetime.now().isoformat(),
            'system': resource_manager.get_system_resources().__dict__,
            'training': {
                'last_time': training_scheduler.last_training_time,
                'best_performance': training_scheduler.best_performance,
                'in_window': training_scheduler.is_training_window(),
            }
        }

        # Send to your existing dashboard
        dashboard_exporter.export_metrics(training_scheduler)

        return metrics

    # Return components for use in your bot
    return {
        'resource_manager': resource_manager,
        'training_scheduler': training_scheduler,
        'dashboard_exporter': dashboard_exporter,
        'wrap_training': wrap_training,
        'wrap_trading': wrap_trading,
        'export_metrics': export_metrics_to_dashboard,
    }

# Usage in your existing bot:
"""
# In your existing main.py:

# Add optimization (at the top)
optimization = add_optimization_to_existing_bot()

# Wrap your existing training function
your_train_function = optimization['wrap_training'](your_train_function)

# Wrap your existing trading function
your_trade_function = optimization['wrap_trading'](your_trade_function)

# In your main loop, add metrics export
while True:
    # Your existing trading logic...

    # Export metrics every 5 seconds
    optimization['export_metrics']()
    time.sleep(5)
"""