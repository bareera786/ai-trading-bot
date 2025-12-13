"""Application configuration objects for the Ultimate AI Trading Bot."""
from __future__ import annotations

import os
from pathlib import Path


class Config:
    """Base configuration shared across environments."""

    # Core secrets and security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///trading_bot.db")
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
    SOCKETIO_CORS_ALLOWED_ORIGINS = os.getenv("SOCKETIO_CORS", "*")
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
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.getenv("WTF_CSRF_SECRET_KEY", SECRET_KEY)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
