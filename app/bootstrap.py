"""Runtime/bootstrap helpers for the modularized AI bot."""
from __future__ import annotations

import glob
import os
from threading import Lock
from typing import Any, Optional

from app.extensions import db
from app.migrations import migrate_database
from app.runtime.builder import RuntimeBuilderError, assemble_runtime_context
from app.runtime.system import initialize_runtime_from_context

BootstrapContext = dict[str, Any]

_bootstrap_lock = Lock()
_runtime_started = False
_TEST_MODE = os.getenv("AI_BOT_TEST_MODE", "").lower() in ("1", "true", "yes")


def _check_ui_assets(app) -> None:
    """Check for missing hashed UI assets and warn if build is needed."""
    static_dir = os.path.join(app.root_path, "static")
    if not os.path.exists(static_dir):
        app.logger.warning("Static directory not found: %s", static_dir)
        return

    # Check for hashed CSS files (common pattern: app-*.css)
    css_files = glob.glob(os.path.join(static_dir, "**", "app-*.css"), recursive=True)
    if not css_files:
        app.logger.warning(
            "No hashed CSS assets found. Run 'npm run build' or 'yarn build' to build UI assets."
        )

    # Check for hashed JS files (common pattern: app-*.js)
    js_files = glob.glob(os.path.join(static_dir, "**", "app-*.js"), recursive=True)
    if not js_files:
        app.logger.warning(
            "No hashed JS assets found. Run 'npm run build' or 'yarn build' to build UI assets."
        )

    # Check for source maps (optional but good indicator of built assets)
    map_files = glob.glob(os.path.join(static_dir, "**", "*.map"), recursive=True)
    if not map_files:
        app.logger.info(
            "No source maps found. Consider enabling source maps in development."
        )


def bootstrap_runtime(app) -> Optional[BootstrapContext]:
    """Ensure the legacy AI bot runtime is wired into the provided Flask app."""

    with app.app_context():
        from app import (
            models,
        )  # noqa: F401  # Ensure models are registered before create_all

        db.create_all()
        try:
            migrate_database()
        except Exception as exc:  # pragma: no cover - migration is best-effort
            app.logger.warning("Database migration skipped: %s", exc)

    if (
        app.config.get("TESTING")
        or app.config.get("SKIP_RUNTIME_BOOTSTRAP")
        or _TEST_MODE
    ):
        return None

    try:
        runtime = assemble_runtime_context(flask_app=app, force=True)
    except RuntimeBuilderError as exc:
        app.logger.error("Unable to assemble AI runtime context: %s", exc)
        return None

    context = runtime.as_dict() if runtime else None
    background_runtime = (
        getattr(runtime, "background_runtime", None) if runtime else None
    )

    scheduler = None
    if background_runtime is not None:
        scheduler = getattr(background_runtime, "live_portfolio_scheduler", None)
        if scheduler is not None:
            try:
                scheduler.app = app
            except Exception:
                app.logger.debug(
                    "Failed to attach Flask app to scheduler", exc_info=True
                )
    if scheduler is None and context:
        scheduler = context.get("live_portfolio_scheduler")
        if scheduler is not None:
            try:
                scheduler.app = app
            except Exception:
                app.logger.debug(
                    "Failed to attach Flask app to scheduler", exc_info=True
                )

    background_task_manager = None
    if background_runtime is not None:
        background_task_manager = getattr(
            background_runtime, "background_task_manager", None
        )
    if background_task_manager is None and context:
        background_task_manager = context.get("background_task_manager")

    global _runtime_started
    with _bootstrap_lock:
        if not _runtime_started:
            if context:
                initialize_runtime_from_context(context)
            else:
                app.logger.warning(
                    "AI runtime context unavailable; skipping initialization"
                )
            if background_task_manager is not None:
                try:
                    background_task_manager.start_live_portfolio_updates()
                except Exception as exc:  # pragma: no cover
                    app.logger.warning(
                        "Live portfolio scheduler failed to start: %s", exc
                    )
            _runtime_started = True

    # Check for UI asset build status
    _check_ui_assets(app)

    return context
