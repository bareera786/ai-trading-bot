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


def _validate_startup_configuration(app) -> None:
    """Validate critical configuration settings on startup."""
    issues = []

    # Check required environment variables
    required_env_vars = [
        "BINANCE_API_KEY",
    ]

    for var in required_env_vars:
        if not os.getenv(var):
            issues.append(f"Missing required environment variable: {var}")

    # Accept either BINANCE_API_SECRET or legacy BINANCE_SECRET_KEY for the secret env var
    if not (os.getenv("BINANCE_API_SECRET") or os.getenv("BINANCE_SECRET_KEY")):
        issues.append(
            "Missing required environment variable: BINANCE_API_SECRET (or legacy BINANCE_SECRET_KEY)"
        )

    # Check database configuration
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        issues.append("Database URI not configured")

    # Check trading mode configuration
    use_testnet = os.getenv("USE_TESTNET", "1").lower() in ("1", "true", "yes")
    enable_futures = os.getenv("ENABLE_FUTURES_TRADING", "0").lower() in (
        "1",
        "true",
        "yes",
    )
    enable_auto_trading = os.getenv("ENABLE_AUTO_TRADING", "0").lower() in (
        "1",
        "true",
        "yes",
    )

    if enable_auto_trading and not use_testnet:
        issues.append(
            "WARNING: Auto trading enabled in LIVE mode - ensure you understand the risks"
        )

    if enable_futures and not use_testnet:
        issues.append(
            "WARNING: Futures trading enabled in LIVE mode - ensure you understand the risks"
        )

    # Check for conflicting configurations
    if enable_auto_trading and enable_futures and not use_testnet:
        issues.append(
            "CRITICAL: Both auto trading and futures trading enabled in LIVE mode - this is HIGH RISK"
        )

    # Log validation results
    if issues:
        app.logger.warning("Configuration validation found %d issue(s):", len(issues))
        for issue in issues:
            if issue.startswith("CRITICAL"):
                app.logger.error("🚨 %s", issue)
            elif issue.startswith("WARNING"):
                app.logger.warning("⚠️ %s", issue)
            else:
                app.logger.warning("ℹ️ %s", issue)
    else:
        app.logger.info("✅ Configuration validation passed")


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

    # Validate startup configuration
    _validate_startup_configuration(app)

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

            # Initialize self-improvement worker with RIBS optimization
            if context:
                try:
                    from app.tasks.self_improvement import SelfImprovementWorker

                    ultimate_trader = context.get("ultimate_trader")
                    optimized_trader = context.get("optimized_trader")
                    ultimate_ml_system = context.get("ultimate_ml_system")
                    optimized_ml_system = context.get("optimized_ml_system")
                    trading_config = context.get("trading_config", {})

                    if all(
                        [
                            ultimate_trader,
                            optimized_trader,
                            ultimate_ml_system,
                            optimized_ml_system,
                        ]
                    ):
                        self_improvement_worker = SelfImprovementWorker(
                            ultimate_trader=ultimate_trader,
                            optimized_trader=optimized_trader,
                            ultimate_ml_system=ultimate_ml_system,
                            optimized_ml_system=optimized_ml_system,
                            dashboard_data=context.get("dashboard_data", {}),
                            trading_config=trading_config,
                            logger=app.logger,
                        )

                        # Store reference in context for access from routes
                        context["self_improvement_worker"] = self_improvement_worker

                        # Start RIBS optimization if enabled
                        if self_improvement_worker.ribs_enabled:
                            import threading

                            ribs_thread = threading.Thread(
                                target=self_improvement_worker.continuous_ribs_optimization,
                                daemon=True,
                                name="RIBS-Optimization",
                            )
                            ribs_thread.start()
                            app.logger.info(
                                "🧬 RIBS Quality Diversity Optimization started"
                            )

                        app.logger.info("🤖 Self-improvement worker initialized")
                    else:
                        app.logger.warning(
                            "⚠️ Missing components for self-improvement worker"
                        )

                except Exception as exc:
                    app.logger.warning(
                        "Self-improvement worker failed to start: %s", exc
                    )

            _runtime_started = True

    # Check for UI asset build status
    _check_ui_assets(app)

    return context
