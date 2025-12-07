"""Runtime/bootstrap helpers for the modularized AI bot."""
from __future__ import annotations

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
_TEST_MODE = os.getenv('AI_BOT_TEST_MODE', '').lower() in ('1', 'true', 'yes')


def bootstrap_runtime(app) -> Optional[BootstrapContext]:
    """Ensure the legacy AI bot runtime is wired into the provided Flask app."""

    with app.app_context():
        from app import models  # noqa: F401  # Ensure models are registered before create_all
        db.create_all()
        try:
            migrate_database()
        except Exception as exc:  # pragma: no cover - migration is best-effort
            app.logger.warning("Database migration skipped: %s", exc)

    if app.config.get('TESTING') or app.config.get('SKIP_RUNTIME_BOOTSTRAP') or _TEST_MODE:
        return None

    try:
        runtime = assemble_runtime_context(flask_app=app, force=True)
    except RuntimeBuilderError as exc:
        app.logger.error("Unable to assemble AI runtime context: %s", exc)
        return None

    context = runtime.as_dict() if runtime else None
    background_runtime = getattr(runtime, 'background_runtime', None) if runtime else None

    scheduler = None
    if background_runtime is not None:
        scheduler = getattr(background_runtime, 'live_portfolio_scheduler', None)
        if scheduler is not None:
            try:
                scheduler.app = app
            except Exception:
                app.logger.debug("Failed to attach Flask app to scheduler", exc_info=True)
    if scheduler is None and context:
        scheduler = context.get('live_portfolio_scheduler')
        if scheduler is not None:
            try:
                scheduler.app = app
            except Exception:
                app.logger.debug("Failed to attach Flask app to scheduler", exc_info=True)

    background_task_manager = None
    if background_runtime is not None:
        background_task_manager = getattr(background_runtime, 'background_task_manager', None)
    if background_task_manager is None and context:
        background_task_manager = context.get('background_task_manager')

    global _runtime_started
    with _bootstrap_lock:
        if not _runtime_started:
            if context:
                initialize_runtime_from_context(context)
            else:
                app.logger.warning("AI runtime context unavailable; skipping initialization")
            if background_task_manager is not None:
                try:
                    background_task_manager.start_live_portfolio_updates()
                except Exception as exc:  # pragma: no cover
                    app.logger.warning("Live portfolio scheduler failed to start: %s", exc)
            _runtime_started = True

    return context
