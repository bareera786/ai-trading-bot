"""Shared Flask extensions initialized via the application factory."""
from __future__ import annotations

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

from .config import Config
from .assets import register_asset_helpers

# Instantiate extensions (no app bound yet)
db = SQLAlchemy()
login_manager = LoginManager()
socketio = SocketIO()


def init_extensions(app):
    """Bind extensions to the provided Flask application."""
    # SQLAlchemy
    db.init_app(app)

    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Socket.IO (reuse config defaults)
    cors = app.config.get('SOCKETIO_CORS_ALLOWED_ORIGINS', Config.SOCKETIO_CORS_ALLOWED_ORIGINS)
    async_mode = app.config.get('SOCKETIO_ASYNC_MODE', Config.SOCKETIO_ASYNC_MODE)
    socketio.init_app(app, cors_allowed_origins=cors, async_mode=async_mode)

    # Ensure asset helpers are always registered, even for ad-hoc Flask apps in tests
    register_asset_helpers(app)
