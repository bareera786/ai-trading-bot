"""Shared Flask extensions initialized via the application factory."""
from __future__ import annotations

import redis
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager

try:
    from flask_mail import Mail
except (
    Exception
):  # pragma: no cover - optional dependency may be missing in some test envs
    # Provide a lightweight fallback so tests and minimal setups don't fail when Flask-Mail
    # isn't installed. The real Mail class will be used in production when available.
    class Mail:
        def init_app(self, app):
            return None


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
    # If session options were provided via app config (e.g., tests may set
    # expire_on_commit=False to avoid DetachedInstanceError when objects are
    # accessed after commit), apply them to the scoped session factory.
    session_opts = app.config.get("SQLALCHEMY_SESSION_OPTIONS")
    if session_opts and isinstance(session_opts, dict):
        try:
            db.session.configure(**session_opts)
        except Exception:
            # Best-effort; don't fail initialization if configuration not
            # compatible with the installed Flask-SQLAlchemy/SQLAlchemy
            # version.
            app.logger.debug("Failed to apply session options: %s", session_opts)
    # Some versions of Flask-SQLAlchemy may not honor session options via
    # config; in test environments explicitly replace the scoped session
    # factory so sessions do not expire on commit (avoids DetachedInstance
    # errors when test helpers access model attributes after commit).
    try:
        import os
        from sqlalchemy.orm import scoped_session, sessionmaker

        if app.config.get("TESTING") or os.getenv("PYTEST_CURRENT_TEST"):
            with app.app_context():
                # Create a session factory bound to the engine with
                # expire_on_commit disabled so instances remain usable
                # after commit in tests.
                sess_factory = sessionmaker(bind=db.engine, expire_on_commit=False)
                db.session = scoped_session(sess_factory)
    except Exception:
        app.logger.debug("Failed to configure test session factory", exc_info=True)

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
