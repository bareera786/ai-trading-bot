"""Application configuration objects for the Ultimate AI Trading Bot."""
from __future__ import annotations

import os
from pathlib import Path

# Import performance settings
from config.performance import (
    PERFORMANCE_SETTINGS,
    MEMORY_SETTINGS,
    DATABASE_SETTINGS,
    CACHE_SETTINGS,
    ML_SETTINGS,
    API_SETTINGS,
    MONITORING_SETTINGS,
    BACKGROUND_SETTINGS,
    SECURITY_SETTINGS
)


class Config:
    """Base configuration shared across environments."""

    # Core secrets and security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

    # Database
    # In production the DATABASE_URL environment variable MUST be set
    # (use PostgreSQL). Do not fall back to SQLite in production.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Paths used by various subsystems
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "bot_persistence"
    STATIC_DIST_DIR = BASE_DIR / "app" / "static" / "dist"
    MIGRATE_DIRECTORY = BASE_DIR / "app" / "migrations"
    ASSET_MANIFEST_PATH = os.getenv("ASSET_MANIFEST_PATH") or str(
        STATIC_DIST_DIR / "manifest.json"
    )
    ASSET_FALLBACKS = {
        "dashboard.js": "js/dashboard.js",
        "dashboard.css": "css/dashboard.css",
        "auth.css": "css/auth.css",
        "subscription-card.js": "js/subscription-card.js",
        "lead-capture.js": "js/lead-capture.js",
        "admin-leads.js": "js/admin-leads.js",
    }

    # Socket.IO defaults
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.getenv("SOCKETIO_CORS", "")
    SOCKETIO_ASYNC_MODE = os.getenv("SOCKETIO_ASYNC_MODE", "threading")

    # Public landing flag
    SHOW_PUBLIC_LANDING = os.getenv("SHOW_PUBLIC_LANDING", "1") == "1"
    PUBLIC_SUBSCRIPTION_CACHE_SECONDS = int(
        os.getenv("PUBLIC_SUBSCRIPTION_CACHE_SECONDS", "120")
    )

    # Lead capture & marketing
    LEAD_RATE_LIMIT_SECONDS = int(os.getenv("LEAD_RATE_LIMIT_SECONDS", "90"))
    LEAD_NOTIFICATION_WEBHOOK = os.getenv("LEAD_NOTIFICATION_WEBHOOK", "")
    ENABLE_MARKETING_ANALYTICS = os.getenv("ENABLE_MARKETING_ANALYTICS", "0") == "1"
    MARKETING_ANALYTICS_SRC = os.getenv("MARKETING_ANALYTICS_SRC", "")
    MARKETING_ANALYTICS_DOMAIN = os.getenv("MARKETING_ANALYTICS_DOMAIN", "")
    MARKETING_ANALYTICS_API_HOST = os.getenv("MARKETING_ANALYTICS_API_HOST", "")

    # Email configuration for password reset and verification
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "1") == "1"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "0") == "1"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@ai-trading-bot.com")
    MAIL_MAX_EMAILS = int(os.getenv("MAIL_MAX_EMAILS", "10"))
    MAIL_SUPPRESS_SEND = os.getenv("MAIL_SUPPRESS_SEND", "0") == "1"

    # CSRF protection
    WTF_CSRF_ENABLED = False
    WTF_CSRF_SECRET_KEY = os.getenv("WTF_CSRF_SECRET_KEY", SECRET_KEY)

    # Performance Settings Integration
    # Core performance tuning
    ENABLE_CACHING = PERFORMANCE_SETTINGS['ENABLE_CACHING']
    CACHE_TTL_SECONDS = PERFORMANCE_SETTINGS['CACHE_TTL_SECONDS']
    MAX_MEMORY_MB = PERFORMANCE_SETTINGS['MAX_MEMORY_MB']
    DATABASE_POOL_SIZE = PERFORMANCE_SETTINGS['DATABASE_POOL_SIZE']
    CHUNK_SIZE_PROCESSING = PERFORMANCE_SETTINGS['CHUNK_SIZE_PROCESSING']
    PARALLEL_WORKERS = PERFORMANCE_SETTINGS['PARALLEL_WORKERS']
    COMPRESS_RESPONSES = PERFORMANCE_SETTINGS['COMPRESS_RESPONSES']
    LOG_PERFORMANCE = PERFORMANCE_SETTINGS['LOG_PERFORMANCE']

    # Memory management
    GC_THRESHOLD = MEMORY_SETTINGS['GC_THRESHOLD']
    MEMORY_CHECK_INTERVAL = MEMORY_SETTINGS['MEMORY_CHECK_INTERVAL']
    MEMORY_WARNING_THRESHOLD = MEMORY_SETTINGS['MEMORY_WARNING_THRESHOLD']
    MEMORY_CRITICAL_THRESHOLD = MEMORY_SETTINGS['MEMORY_CRITICAL_THRESHOLD']
    AUTO_GC_COLLECT = MEMORY_SETTINGS['AUTO_GC_COLLECT']
    TRACK_MEMORY_LEAKS = MEMORY_SETTINGS['TRACK_MEMORY_LEAKS']

    # Database performance
    CONNECTION_TIMEOUT = DATABASE_SETTINGS['CONNECTION_TIMEOUT']
    COMMAND_TIMEOUT = DATABASE_SETTINGS['COMMAND_TIMEOUT']
    POOL_RECYCLE = DATABASE_SETTINGS['POOL_RECYCLE']
    POOL_PRE_PING = DATABASE_SETTINGS['POOL_PRE_PING']
    ECHO_SQL = DATABASE_SETTINGS['ECHO_SQL']
    BATCH_SIZE = DATABASE_SETTINGS['BATCH_SIZE']
    FETCH_SIZE = DATABASE_SETTINGS['FETCH_SIZE']

    # Caching configuration
    REDIS_MAX_CONNECTIONS = CACHE_SETTINGS['REDIS_MAX_CONNECTIONS']
    REDIS_SOCKET_TIMEOUT = CACHE_SETTINGS['REDIS_SOCKET_TIMEOUT']
    REDIS_SOCKET_CONNECT_TIMEOUT = CACHE_SETTINGS['REDIS_SOCKET_CONNECT_TIMEOUT']
    LOCAL_CACHE_MAX_SIZE = CACHE_SETTINGS['LOCAL_CACHE_MAX_SIZE']
    CACHE_SERIALIZATION = CACHE_SETTINGS['CACHE_SERIALIZATION']
    COMPRESSION_ENABLED = CACHE_SETTINGS['COMPRESSION_ENABLED']
    COMPRESSION_LEVEL = CACHE_SETTINGS['COMPRESSION_LEVEL']

    # ML performance
    MODEL_CACHE_SIZE = ML_SETTINGS['MODEL_CACHE_SIZE']
    FEATURE_CACHE_SIZE = ML_SETTINGS['FEATURE_CACHE_SIZE']
    BATCH_PREDICTION_SIZE = ML_SETTINGS['BATCH_PREDICTION_SIZE']
    PARALLEL_TRAINING = ML_SETTINGS['PARALLEL_TRAINING']
    GPU_ACCELERATION = ML_SETTINGS['GPU_ACCELERATION']
    MODEL_COMPRESSION = ML_SETTINGS['MODEL_COMPRESSION']

    # API performance
    RATE_LIMIT_REQUESTS = API_SETTINGS['RATE_LIMIT_REQUESTS']
    RATE_LIMIT_WINDOW = API_SETTINGS['RATE_LIMIT_WINDOW']
    RESPONSE_TIMEOUT = API_SETTINGS['RESPONSE_TIMEOUT']
    CONNECTION_POOL_SIZE = API_SETTINGS['CONNECTION_POOL_SIZE']
    KEEP_ALIVE_TIMEOUT = API_SETTINGS['KEEP_ALIVE_TIMEOUT']
    MAX_REQUEST_SIZE = API_SETTINGS['MAX_REQUEST_SIZE']

    # Monitoring and alerting
    ENABLE_PROMETHEUS = MONITORING_SETTINGS['ENABLE_PROMETHEUS']
    METRICS_PORT = MONITORING_SETTINGS['METRICS_PORT']
    ALERT_EMAIL_ENABLED = MONITORING_SETTINGS['ALERT_EMAIL_ENABLED']
    PERFORMANCE_LOG_LEVEL = MONITORING_SETTINGS['PERFORMANCE_LOG_LEVEL']
    SLOW_QUERY_THRESHOLD = MONITORING_SETTINGS['SLOW_QUERY_THRESHOLD']
    HIGH_MEMORY_ALERT = MONITORING_SETTINGS['HIGH_MEMORY_ALERT']
    HIGH_CPU_ALERT = MONITORING_SETTINGS['HIGH_CPU_ALERT']

    # Background processing
    MAX_WORKER_THREADS = BACKGROUND_SETTINGS['MAX_WORKER_THREADS']
    QUEUE_SIZE = BACKGROUND_SETTINGS['QUEUE_SIZE']
    TASK_TIMEOUT = BACKGROUND_SETTINGS['TASK_TIMEOUT']
    RETRY_ATTEMPTS = BACKGROUND_SETTINGS['RETRY_ATTEMPTS']
    RETRY_DELAY = BACKGROUND_SETTINGS['RETRY_DELAY']
    CLEANUP_INTERVAL = BACKGROUND_SETTINGS['CLEANUP_INTERVAL']

    # Security performance
    ENCRYPTION_ENABLED = SECURITY_SETTINGS['ENCRYPTION_ENABLED']
    TOKEN_EXPIRY = SECURITY_SETTINGS['TOKEN_EXPIRY']
    SESSION_TIMEOUT = SECURITY_SETTINGS['SESSION_TIMEOUT']
    RATE_LIMIT_ENABLED = SECURITY_SETTINGS['RATE_LIMIT_ENABLED']
    IP_WHITELIST_ENABLED = SECURITY_SETTINGS['IP_WHITELIST_ENABLED']
    LOG_SECURITY_EVENTS = SECURITY_SETTINGS['LOG_SECURITY_EVENTS']

    # Session cookie settings
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_HTTPONLY = True
    # Default to non-secure so cookies can work over plain HTTP in environments
    # without TLS termination; production should set SESSION_COOKIE_SECURE=true
    SESSION_COOKIE_SECURE = False
    # Default SameSite to Lax for broad compatibility; per-request override
    # will be applied in the login route when required for cross-site XHR.
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_DOMAIN = os.getenv("SESSION_COOKIE_DOMAIN", None)

    # CORS settings — when cookies/credentials are used, do NOT use a wildcard
    CORS_SUPPORTS_CREDENTIALS = True
    # Comma-separated list of allowed origins; default includes localhost for dev
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,https://example.com").split(",")


class DevelopmentConfig(Config):
    DEBUG = True

    # Development-specific performance overrides
    MAX_MEMORY_MB = 512
    LOG_PERFORMANCE = False
    ENABLE_PROMETHEUS = False
    ALERT_EMAIL_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False

    # Production-specific performance overrides
    MAX_MEMORY_MB = 2048
    LOG_PERFORMANCE = True
    ENABLE_PROMETHEUS = True
    ALERT_EMAIL_ENABLED = True
    # Enforce secure cookies for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_SAMESITE = "None"
    # Allow CORS origin to be configured via env (frontend origin)
    CORS_ALLOWED_ORIGINS = os.getenv("FRONTEND_ORIGIN", "").split(",") if os.getenv("FRONTEND_ORIGIN") else []
