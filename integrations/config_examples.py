"""
Example: Using Dashboard Configuration

This shows how to configure and use the dashboard integration system.
"""

from config.dashboard_config import DashboardConfig
from integrations.dashboard_integration import DashboardExporter
from config.resource_manager import ResourceManager

# Method 1: Use default configuration
def example_default_config():
    """Use default dashboard configuration"""
    config = DashboardConfig()
    print(f"Default endpoint: {config.endpoint}")
    print(f"Default update interval: {config.update_interval}s")

# Method 2: Configure for production
def example_production_config():
    """Configure for production dashboard"""
    config = DashboardConfig()

    # Set production endpoint
    config.endpoint = "https://your-production-dashboard.com/api/metrics"
    config.api_key = "your-production-api-key"

    # Adjust monitoring settings
    config.update_interval = 10  # Update every 10 seconds
    config.monitor_alerts = True

    # Customize alert thresholds for your environment
    config.thresholds.update({
        'cpu_critical': 95,      # Critical at 95% CPU
        'cpu_warning': 85,       # Warning at 85% CPU
        'memory_critical': 98,   # Critical at 98% memory
        'memory_warning': 90,    # Warning at 90% memory
        'disk_warning': 95,      # Warning at 95% disk usage
        'load_warning': 8.0,     # Warning at load 8.0
    })

    # Configure which widgets to update
    config.widgets.update({
        'system_health': True,
        'resource_usage': True,
        'training_status': True,
        'trading_performance': True,
        'alerts_panel': True,
    })

    return config

# Method 3: Create from dashboard URL
def example_from_url():
    """Create configuration from dashboard URL"""
    dashboard_url = "https://my-dashboard.com"
    config = DashboardConfig.from_dashboard_url(dashboard_url)

    # The endpoint will be: https://my-dashboard.com/api/metrics
    print(f"Generated endpoint: {config.endpoint}")

    return config

# Method 4: Use in main application
def example_main_integration():
    """Integrate with main bot"""
    from main import AITradingBot

    # Create custom configuration
    config = example_production_config()

    # Initialize bot (it will use the config automatically)
    bot = AITradingBot()

    # Override the default config if needed
    bot.dashboard_config = config
    bot.dashboard_exporter = DashboardExporter(bot.resource_manager, config)

    return bot

# Method 5: Environment-specific configurations
def create_environment_config(env: str) -> DashboardConfig:
    """Create configuration based on environment"""
    config = DashboardConfig()

    if env == "development":
        config.endpoint = "http://localhost:3000/api/metrics"
        config.update_interval = 2  # Fast updates for development
        config.thresholds['cpu_warning'] = 50  # Lower thresholds for dev

    elif env == "staging":
        config.endpoint = "https://staging-dashboard.com/api/metrics"
        config.update_interval = 5
        config.api_key = "staging-api-key"

    elif env == "production":
        config.endpoint = "https://prod-dashboard.com/api/metrics"
        config.update_interval = 10
        config.api_key = "prod-api-key"
        # Stricter thresholds for production
        config.thresholds.update({
            'cpu_critical': 90,
            'memory_critical': 95,
        })

    return config

if __name__ == "__main__":
    print("🔧 Dashboard Configuration Examples")
    print("=" * 40)

    # Test different configurations
    print("\n1. Default Configuration:")
    example_default_config()

    print("\n2. Production Configuration:")
    prod_config = example_production_config()
    print(f"Production endpoint: {prod_config.endpoint}")
    print(f"CPU critical threshold: {prod_config.thresholds['cpu_critical']}%")

    print("\n3. URL-based Configuration:")
    example_from_url()

    print("\n4. Environment Configurations:")
    for env in ["development", "staging", "production"]:
        config = create_environment_config(env)
        print(f"  {env.capitalize()}: {config.endpoint} (interval: {config.update_interval}s)")

    print("\n✅ Configuration examples ready!")
    print("\n💡 Usage Tips:")
    print("   • Use environment variables to set endpoints")
    print("   • Adjust thresholds based on your server capacity")
    print("   • Test configurations in staging before production")
    print("   • Use API keys for secure dashboard communication")