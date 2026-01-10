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

    # Allow operational scripts (e.g., create_admin.py) to skip the heavy
    # runtime bootstrap without forcing an in-memory database.
    if os.getenv("SKIP_RUNTIME_BOOTSTRAP", "").lower() in ("1", "true", "yes"):
        app.config["SKIP_RUNTIME_BOOTSTRAP"] = True

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

    # Add a lightweight response header for observability so clients
    # can verify whether data came from the backend (helps debugging
    # proxy / cache issues). Only attach to JSON responses and keep
    # the hook intentionally minimal and non-intrusive.
    @app.after_request
    def add_x_data_source_header(response):
        try:
            # Ensure the asset manifest is never cached by browsers/proxies.
            # This prevents stale bundle URLs after deploy.
            if (getattr(response, "direct_passthrough", False) is False):
                try:
                    from flask import request as flask_request

                    if (flask_request.path or "").endswith("/static/dist/manifest.json"):
                        response.headers["Cache-Control"] = (
                            "no-store, no-cache, must-revalidate, max-age=0"
                        )
                        response.headers["Pragma"] = "no-cache"
                        response.headers["Expires"] = "0"
                except Exception:
                    pass

            ctype = response.headers.get("Content-Type", "")
            if ctype and "application/json" in ctype.lower():
                # set default header; allow existing header to remain if present
                response.headers.setdefault("X-Data-Source", "backend")
        except Exception:
            # guard against any unexpected errors in the hook
            pass
        return response

    return app
