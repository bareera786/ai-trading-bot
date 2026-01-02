"""Application package entry point."""
from __future__ import annotations

from typing import Optional
import os

from flask import Flask
from .config import Config
from .extensions import init_extensions
from .routes import register_blueprints
from .bootstrap import bootstrap_runtime


def create_app(config_class: Optional[type[Config]] = None) -> Flask:
    """Application factory used by scripts and WSGI servers."""
    config_cls = config_class or Config

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_cls)

    # If tests signal to skip runtime behavior via environment variable,
    # ensure SQLAlchemy uses an in-memory database by default so any early
    # engine creation (happens lazily) does not point at the developer's
    # persistent DB file which can cause conflicts during tests.
    if os.getenv("AI_BOT_TEST_MODE", "").lower() in ("1", "true", "yes"):
        # Force an in-memory DB so any lazy engine creation during app
        # initialization uses a transient, isolated DB and cannot collide
        # with the developer's persistent instance DB.
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        # In tests we prefer sessions to keep their state after commit so
        # test helpers can access model attributes without hitting a closed
        # session (avoids sqlalchemy.orm.exc.DetachedInstanceError).
        app.config["SQLALCHEMY_SESSION_OPTIONS"] = {"expire_on_commit": False}

    # Detect running under pytest and ensure the background runtime is
    # skipped so expensive workers (RIBS, schedulers) do not start during
    # unit tests. We set the SKIP_RUNTIME_BOOTSTRAP flag which
    # bootstrap_runtime honors; additionally enable TESTING so Flask and
    # extensions run in test mode.
    if "PYTEST_CURRENT_TEST" in os.environ:
        app.config["SKIP_RUNTIME_BOOTSTRAP"] = True
        app.config["TESTING"] = True

    init_extensions(app)

    # Initialize tenant isolation for multi-user support (optional)
    try:
        from .core.tenant_isolation import init_tenant_isolation
        init_tenant_isolation(app)
    except Exception:
        # Tenant isolation is optional in local/dev setups or when the
        # module is not present. Skip initialization to allow the app
        # to start for debugging and development tasks.
        pass

    register_blueprints(app)

    bootstrap_runtime(app)

    return app
