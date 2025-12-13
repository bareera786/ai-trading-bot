"""Shared Flask extensions initialized via the application factory."""
from __future__ import annotations

import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

from .config import Config
from .assets import register_asset_helpers

# Instantiate extensions (no app bound yet)
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO()
mail = Mail()

# Configure Redis storage for rate limiting
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")


def init_extensions(app):
    """Bind extensions to the provided Flask application."""
    # SQLAlchemy
    db.init_app(app)

    # Flask-Migrate
    migrate.init_app(app, db, directory=app.config.get("MIGRATE_DIRECTORY"))

    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Socket.IO (reuse config defaults)
    cors = app.config.get(
        "SOCKETIO_CORS_ALLOWED_ORIGINS", Config.SOCKETIO_CORS_ALLOWED_ORIGINS
    )
    async_mode = app.config.get("SOCKETIO_ASYNC_MODE", Config.SOCKETIO_ASYNC_MODE)
    socketio.init_app(app, cors_allowed_origins=cors, async_mode=async_mode)

    # Flask-Limiter
    limiter.init_app(app)

    # Flask-Mail
    mail.init_app(app)

    # Ensure asset helpers are always registered, even for ad-hoc Flask apps in tests
    register_asset_helpers(app)
