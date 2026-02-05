"""Application package entry point."""
from __future__ import annotations

from typing import Optional
import os
from datetime import timedelta

from flask import Flask
from .config import Config
from .extensions import init_extensions, limiter, csrf
from .routes import register_blueprints
from .bootstrap import bootstrap_runtime


def _register_cli_commands(app: Flask) -> None:
    """Register Flask CLI commands for user management."""
    from .cli import register_cli_commands
    register_cli_commands(app)


def create_app(config_class: Optional[type[Config]] = None) -> Flask:
    """Application factory used by scripts and WSGI servers."""
    config_cls = config_class or Config

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_cls)

    # Update session and remember cookie settings for proper authentication
    app.config.update(
        PERMANENT_SESSION_LIFETIME=timedelta(seconds=86400),  # 24 hours
        SESSION_REFRESH_EACH_REQUEST=True,
        REMEMBER_COOKIE_DURATION=timedelta(days=30),
        REMEMBER_COOKIE_REFRESH_EACH_REQUEST=True,
        REMEMBER_COOKIE_SAMESITE='None',
        REMEMBER_COOKIE_SECURE=True,
        REMEMBER_COOKIE_HTTPONLY=True
    )

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
        from .core.tenant_isolation import init_tenant_isolation  # type: ignore
        init_tenant_isolation(app)
    except (ImportError, ModuleNotFoundError):
        # Tenant isolation is optional in local/dev setups or when the
        # module is not present. Skip initialization to allow the app
        # to start for debugging and development tasks.
        pass

    register_blueprints(app)

    # Register CLI commands
    _register_cli_commands(app)

    bootstrap_runtime(app)

    # Add a lightweight response header for observability so clients
    # can verify whether data came from the backend (helps debugging
    # proxy / cache issues). Only attach to JSON responses and keep
    # the hook intentionally minimal and non-intrusive.
    @app.after_request
    def after_request(response):
        # 1. CORS Headers (Allow frontend access)
        # Use configured allowed origins or default to wildcard for this setup
        response.headers.add('Access-Control-Allow-Origin', '*') 
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        
        # 2. Cache Control Strategy
        # NO CACHE for HTML Routes (Dashboard, Login, everything user-facing)
        if response.mimetype == 'text/html':
            response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            response.headers.add('Pragma', 'no-cache')
            response.headers.add('Expires', '0')
        
        # 3. Add Observability Header
        if response.mimetype == 'application/json':
             response.headers.setdefault("X-Data-Source", "backend")

        return response

    @app.context_processor
    def inject_reseller_branding():
        """Inject reseller branding into all templates."""
        from flask_login import current_user
        
        branding = {}
        reseller = None
        
        if current_user.is_authenticated and getattr(current_user, "reseller_id", None):
            reseller = getattr(current_user, "reseller", None)
            if reseller and reseller.branding_config:
                branding = reseller.branding_config
                
        return dict(reseller_branding=branding, current_reseller=reseller)

    # Minimal SPA fallback: serve the dashboard entry for deep links that
    # are not API/static/health/metrics. This allows client-side routing to
    # handle paths like /dashboard/trade-history when requested directly.
    # Keep this minimal and conservative so API and static routes remain
    # unchanged.
    from flask import render_template, request, abort
    import time as _time

    @app.route(
        "/<path:requested_path>",

        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )
    def _spa_fallback(requested_path: str):
        path = f"/{requested_path or ''}"

        # Preserve explicit server-handled routes
        if path.startswith("/api/") or path.startswith("/static/"):
            return abort(404)
        if path == "/health" or path.startswith("/health?"):
            return abort(404)
        if path == "/metrics" or path.startswith("/metrics?"):
            return abort(404)
        # Preserve auth routes
        if path in ("/login", "/login/", "/register", "/register/", "/logout", "/logout/"):
            return abort(404)
        
        # Preserve new feature routes (Phase 1-3)
        if path.startswith("/settings/notifications") or path.startswith("/settings/risk-presets"):
            return abort(404)
        if path.startswith("/analytics/"):
            return abort(404)
        if path.startswith("/trading/journal"):
            return abort(404)
        if path == "/backtesting" or path.startswith("/backtesting/"):
            return abort(404)
        
        # Public Marketing Pages
        if path in ("/pricing", "/pricing/", "/plans", "/plans/"):
            return abort(404)

        # For any other path, render the SPA dashboard entry so the client
        # router can take over. Keep the template context minimal to avoid
        # coupling with runtime-only state.
        try:
            return render_template(
                "dashboard.html",
                version_label="Ultimate AI Bot",
                ribs_optimization={},
                current_time=int(_time.time()),
            )
        except Exception:
            # If rendering fails for any unexpected reason, return 404 so
            # the original error path is visible to callers.
            return abort(404)

    # Initialize extensions (use the module-level instances imported above)
    limiter.init_app(app)
    csrf.init_app(app)

    # Exempt API endpoints from CSRF protection (do this after csrf is initialized)
    try:
        # Be robust: instead of assuming attributes on a blueprint/module,
        # look up the actual registered view callables in app.view_functions
        # and exempt the API endpoints we care about. This avoids problems
        # where older deploys or refactors expose only a Blueprint object.
        for endpoint, view_func in list(app.view_functions.items()):
            should_exempt = False
            if endpoint in ("auth_api.api_login", "auth_api.api_logout", "auth_api.api_register"):
                should_exempt = True
            elif endpoint.startswith("brain.") or endpoint.startswith("system_ops."):
                should_exempt = True
            
            if should_exempt:
                try:
                    csrf.exempt(view_func)
                    app.logger.debug(f"CSRF exempted: {endpoint}")
                except Exception:
                    app.logger.debug(f"Failed to CSRF-exempt view: {endpoint}", exc_info=True)
    except Exception:
        app.logger.debug("Failed while scanning view functions for CSRF exemptions", exc_info=True)

    # Temporary global error handler to log full tracebacks for debugging
    # production 500s. Preserve HTTPExceptions (404/405/400/etc) so clients
    # see the correct status code.
    from flask import jsonify
    from werkzeug.exceptions import HTTPException

    def _wants_json_error() -> bool:
        try:
            from flask import request as flask_request

            return bool(
                (flask_request.path or "").startswith("/api/")
                or flask_request.headers.get("X-Requested-With") == "XMLHttpRequest"
                or flask_request.accept_mimetypes.best == "application/json"
            )
        except Exception:
            return False

    @app.errorhandler(Exception)
    def _log_unhandled_exception(exc):
        if isinstance(exc, HTTPException):
            # Log as exception to preserve traceback visibility during rollout,
            # but keep the correct HTTP status code.
            app.logger.exception("HTTP exception during request: %s", exc)

            if _wants_json_error():
                description = getattr(exc, "description", None) or "Request failed"
                code = int(getattr(exc, "code", 500) or 500)
                return jsonify({"success": False, "error": description}), code

            return exc

        # Log full traceback to the application logger for diagnostics
        app.logger.exception("Unhandled exception during request: %s", exc)
        # Return a minimal opaque error to clients
        return jsonify({"success": False, "error": "Internal Server Error"}), 500

    return app
