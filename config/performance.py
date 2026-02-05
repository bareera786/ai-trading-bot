"""
Performance Configuration Settings
Critical performance tuning parameters for the AI trading bot
"""

from __future__ import annotations

# Performance Settings
PERFORMANCE_SETTINGS = {
    'ENABLE_CACHING': True,
    'CACHE_TTL_SECONDS': 300,
    'MAX_MEMORY_MB': 1024,  # Alert if exceeded
    'DATABASE_POOL_SIZE': 20,
    'CHUNK_SIZE_PROCESSING': 10000,
    'PARALLEL_WORKERS': 4,
    'COMPRESS_RESPONSES': True,
    'LOG_PERFORMANCE': True
}

# Memory Management
MEMORY_SETTINGS = {
    'GC_THRESHOLD': (700, 10, 10),  # Python GC thresholds
    'MEMORY_CHECK_INTERVAL': 60,    # Check every 60 seconds
    'MEMORY_WARNING_THRESHOLD': 0.8,  # 80% of MAX_MEMORY_MB
    'MEMORY_CRITICAL_THRESHOLD': 0.9,  # 90% of MAX_MEMORY_MB
    'AUTO_GC_COLLECT': True,
    'TRACK_MEMORY_LEAKS': True
}

# Database Performance
DATABASE_SETTINGS = {
    'CONNECTION_TIMEOUT': 30,
    'COMMAND_TIMEOUT': 60,
    'POOL_RECYCLE': 3600,  # Recycle connections every hour
    'POOL_PRE_PING': True,  # Test connections before use
    'ECHO_SQL': False,      # Don't log SQL in production
    'BATCH_SIZE': 1000,
    'FETCH_SIZE': 5000
}

# Caching Configuration
CACHE_SETTINGS = {
    'REDIS_MAX_CONNECTIONS': 20,
    'REDIS_SOCKET_TIMEOUT': 5,
    'REDIS_SOCKET_CONNECT_TIMEOUT': 5,
    'LOCAL_CACHE_MAX_SIZE': 10000,
    'CACHE_SERIALIZATION': 'pickle',  # pickle, json, msgpack
    'COMPRESSION_ENABLED': True,
    'COMPRESSION_LEVEL': 6
}

# ML Performance
ML_SETTINGS = {
    'MODEL_CACHE_SIZE': 50,      # Keep 50 models in memory
    'FEATURE_CACHE_SIZE': 1000,  # Cache 1000 feature sets
    'BATCH_PREDICTION_SIZE': 100,
    'PARALLEL_TRAINING': True,
    'GPU_ACCELERATION': False,   # Enable if GPU available
    'MODEL_COMPRESSION': True
}

# API Performance
API_SETTINGS = {
    'RATE_LIMIT_REQUESTS': 1000,
    'RATE_LIMIT_WINDOW': 60,     # per minute
    'RESPONSE_TIMEOUT': 30,
    'CONNECTION_POOL_SIZE': 100,
    'KEEP_ALIVE_TIMEOUT': 75,
    'MAX_REQUEST_SIZE': '10MB'
}

# Monitoring and Alerting
MONITORING_SETTINGS = {
    'ENABLE_PROMETHEUS': True,
    'METRICS_PORT': 9090,
    'ALERT_EMAIL_ENABLED': True,
    'PERFORMANCE_LOG_LEVEL': 'INFO',
    'SLOW_QUERY_THRESHOLD': 1.0,  # Log queries > 1 second
    'HIGH_MEMORY_ALERT': True,
    'HIGH_CPU_ALERT': True
}

# Background Processing
BACKGROUND_SETTINGS = {
    'MAX_WORKER_THREADS': 8,
    'QUEUE_SIZE': 1000,
    'TASK_TIMEOUT': 300,  # 5 minutes
    'RETRY_ATTEMPTS': 3,
    'RETRY_DELAY': 5,     # seconds
    'CLEANUP_INTERVAL': 3600  # Clean old tasks every hour
}

# Security Performance
SECURITY_SETTINGS = {
    'ENCRYPTION_ENABLED': True,
    'TOKEN_EXPIRY': 3600,  # 1 hour
    'SESSION_TIMEOUT': 7200,  # 2 hours
    'RATE_LIMIT_ENABLED': True,
    'IP_WHITELIST_ENABLED': False,
    'LOG_SECURITY_EVENTS': True
}

# Development/Production Overrides
import os

# Override settings based on environment
ENV = os.getenv('FLASK_ENV', 'development')

if ENV == 'production':
    PERFORMANCE_SETTINGS.update({
        'LOG_PERFORMANCE': True,
        'MAX_MEMORY_MB': 2048  # Higher limit for production
    })

    MONITORING_SETTINGS.update({
        'ENABLE_PROMETHEUS': True,
        'ALERT_EMAIL_ENABLED': True
    })

elif ENV == 'development':
    PERFORMANCE_SETTINGS.update({
        'LOG_PERFORMANCE': False,  # Less logging in dev
        'MAX_MEMORY_MB': 512
    })

    MONITORING_SETTINGS.update({
        'ENABLE_PROMETHEUS': False,
        'ALERT_EMAIL_ENABLED': False
    })

# Export all settings
__all__ = [
    'PERFORMANCE_SETTINGS',
    'MEMORY_SETTINGS',
    'DATABASE_SETTINGS',
    'CACHE_SETTINGS',
    'ML_SETTINGS',
    'API_SETTINGS',
    'MONITORING_SETTINGS',
    'BACKGROUND_SETTINGS',
    'SECURITY_SETTINGS'
]