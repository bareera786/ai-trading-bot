"""Runtime/bootstrap helpers for the modularized AI bot."""
from __future__ import annotations

import glob
import json
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
_TEST_MODE = None  # Deprecated placeholder — evaluate test-mode dynamically in runtime


def _validate_startup_configuration(app) -> None:
    """Validate critical configuration settings on startup."""
    issues = []

    # Check if we're in test mode - if so, skip Binance API key requirements
    test_mode = os.getenv("AI_BOT_TEST_MODE", "").lower() in ("1", "true", "yes")

    if not test_mode:
        # Check required environment variables (only when not in test mode)
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
    else:
        app.logger.info("✅ Test mode enabled - skipping Binance API key validation")

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

    dist_dir = os.path.join(static_dir, "dist")
    manifest_path = app.config.get("ASSET_MANIFEST_PATH") or os.path.join(
        dist_dir, "manifest.json"
    )

    if not os.path.exists(manifest_path):
        app.logger.warning(
            "UI asset manifest not found at %s. Run 'npm run build:assets' to build UI assets.",
            manifest_path,
        )
        return

    try:
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle) or {}
    except Exception as exc:
        app.logger.warning("Failed to load UI asset manifest %s: %s", manifest_path, exc)
        return

    css_assets: list[str] = []
    js_assets: list[str] = []
    for logical_name, rel_path in manifest.items():
        if not isinstance(rel_path, str):
            continue
        if logical_name.endswith(".css") or rel_path.endswith(".css"):
            css_assets.append(rel_path)
        if logical_name.endswith(".js") or rel_path.endswith(".js"):
            js_assets.append(rel_path)

    if not css_assets:
        app.logger.warning(
            "No hashed CSS assets found in manifest. Run 'npm run build:assets' to build UI assets."
        )
    if not js_assets:
        app.logger.warning(
            "No hashed JS assets found in manifest. Run 'npm run build:assets' to build UI assets."
        )

    missing_files: list[str] = []
    for rel_path in sorted(set(css_assets + js_assets)):
        abs_path = os.path.join(static_dir, rel_path)
        if not os.path.exists(abs_path):
            missing_files.append(rel_path)

    if missing_files:
        app.logger.warning(
            "UI asset manifest references missing files: %s. Re-run 'npm run build:assets'.",
            ", ".join(missing_files[:10])
            + ("..." if len(missing_files) > 10 else ""),
        )

    # Optional: source maps can be disabled in production builds.
    map_files = glob.glob(os.path.join(dist_dir, "**", "*.map"), recursive=True)
    if not map_files:
        app.logger.info("No source maps found in %s.", dist_dir)


def bootstrap_runtime(app) -> Optional[BootstrapContext]:
    """Ensure the legacy AI bot runtime is wired into the provided Flask app."""
    # Note: don't short-circuit before running DB migrations; we need basic
    # schema creation to succeed even when tests set AI_BOT_TEST_MODE. The
    # actual decision to skip starting background runtime will be taken
    # later (after migrations) so tests can still create tables.

    # Validate startup configuration
    _validate_startup_configuration(app)

    skip_db_bootstrap = os.getenv("SKIP_DB_BOOTSTRAP", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if skip_db_bootstrap:
        app.logger.info("bootstrap_runtime: SKIP_DB_BOOTSTRAP enabled; skipping db.create_all/migrate_database")
    else:
        with app.app_context():
            from app import (
                models,
            )  # noqa: F401  # Ensure models are registered before create_all

            # Wrapper to handle "type already exists" errors typical with Postgres Enums in create_all
            # Wrapper to handle "type already exists" errors typical with Postgres Enums in create_all
            from sqlalchemy.exc import ProgrammingError
            app.logger.info("🔧 Bootstrap patch active: Attempting safe db.create_all()")
            try:
                db.create_all()
                app.logger.info("✅ db.create_all() completed")
            except Exception as e:
                # Ignore "type ... already exists" errors
                if "already exists" in str(e):
                    app.logger.warning(f"⚠️ db.create_all() warning (ignored): {e}")
                else:
                    app.logger.error(f"❌ db.create_all() failed with {type(e)}: {e}")
                    # For now, let's swallow it if it looks like a DB error, to keep the bot alive
                    if "DuplicateObject" not in str(e):
                         raise
            
            # --- SELF-HEALING PATCH: Fix Schema Drift for TrainingJob ---
            # Explicitly check/add columns that migrations might miss if revisions are out of sync
            try:
                from sqlalchemy import text
                with db.engine.connect() as conn:
                    # Fix training_job ID sequence (Auto-Increment)
                    try:
                        # Postgres-specific fix for missing SERIAL/SEQUENCE
                        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS training_job_id_seq"))
                        conn.execute(text("ALTER TABLE training_job ALTER COLUMN id SET DEFAULT nextval('training_job_id_seq')"))
                        conn.execute(text("ALTER SEQUENCE training_job_id_seq OWNED BY training_job.id"))
                        # Sync sequence with max ID
                        conn.execute(text("SELECT setval('training_job_id_seq', COALESCE((SELECT MAX(id)+1 FROM training_job), 1), false)"))
                        conn.commit()
                        app.logger.info("✅ Applied ID sequence fix for TrainingJob")
                    except Exception as e:
                        # Ignore if it's not Postgres or already correct
                        app.logger.warning(f"⚠️ ID sequence patch check (safe to ignore if not Postgres): {e}")

                    # Fix training_job columns
                    try:
                        conn.execute(text("ALTER TABLE training_job ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"))
                        conn.execute(text("ALTER TABLE training_job ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP"))
                        conn.execute(text("ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS symbol VARCHAR(20)"))
                        conn.execute(text("ALTER TABLE ml_model ADD COLUMN IF NOT EXISTS file_path VARCHAR(255)"))
                        conn.commit()
                        app.logger.info("✅ Applied self-healing schema patch for TrainingJob/MLModel")
                    except Exception as e:
                        app.logger.warning(f"⚠️ Schema patch check failed (might be already correct): {e}")
            except Exception as e:
                app.logger.error(f"❌ Failed to apply schema patch: {e}")
            # ------------------------------------------------------------

            try:
                migrate_database()
            except Exception as exc:  # pragma: no cover - migration is best-effort
                app.logger.warning("Database migration skipped: %s", exc)

            # Create bootstrap users if requested
            _create_bootstrap_users_if_requested(app)

    # Evaluate test mode dynamically so changes to AI_BOT_TEST_MODE during tests
    # (set at runtime) are respected. Previously this used a module-level
    # _TEST_MODE computed at import time which caused bootstrap to run even
    # after tests set the env var inside a test function.
    test_mode = os.getenv("AI_BOT_TEST_MODE", "").lower() in ("1", "true", "yes")
    app.logger.info(
        "bootstrap_runtime: AI_BOT_TEST_MODE=%s, app.TESTING=%s",
        os.getenv("AI_BOT_TEST_MODE"),
        app.config.get("TESTING"),
    )

    if (
        app.config.get("TESTING")
        or app.config.get("SKIP_RUNTIME_BOOTSTRAP")
        or test_mode
    ):
        return None

    try:
        runtime = assemble_runtime_context(flask_app=app, force=True)
    except RuntimeBuilderError as exc:
        app.logger.error("Unable to assemble AI runtime context: %s", exc)
        # CRITICAL DEBUG: Re-raise to see why it fails
        raise

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
            # Determine Role
            bot_role = os.getenv("AI_BOT_ROLE", "api")

            if background_task_manager is not None:
                # Start Portfolio Updates (Safe for API and Worker)
                try:
                    background_task_manager.start_live_portfolio_updates()
                except Exception as exc:  # pragma: no cover
                    app.logger.warning(
                        "Live portfolio scheduler failed to start: %s", exc
                    )

            # Initialize self-improvement worker with RIBS optimization
            if context:
                try:
                    from app.ml.self_improvement.worker import SelfImprovementWorker

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

                        # Start RIBS optimization ONLY if NOT API
                        if bot_role != "api":
                            self_improvement_worker.start()  # Starts main loop for control file & metrics

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

                            app.logger.info("🤖 Self-improvement worker initialized (Worker Role)")
                        else:
                            app.logger.info("ℹ️ API Role: Skipping RIBS Optimization thread")

                    else:
                        missing = [k for k, v in {
                            "ultimate_trader": ultimate_trader,
                            "optimized_trader": optimized_trader,
                            "ultimate_ml_system": ultimate_ml_system,
                            "optimized_ml_system": optimized_ml_system
                        }.items() if not v]
                        app.logger.warning(
                            f"⚠️ Missing components for self-improvement worker: {missing}"
                        )

                except Exception as exc:
                    app.logger.warning(
                        "Self-improvement worker failed to start: %s", exc
                    )

            _runtime_started = True

            # --- Inject Persistence Context into Global Trader ---
            # --- Persistence Context Injection Removed in Phase 10 ---
            # Global trader is now stateless/generic. Real trading requires
            # explicit per-user instantiation via MarketDataService.
            if context and context.get("ultimate_trader"):
                # Mark as system-context (no user)
                 ut = context["ultimate_trader"]
                 if hasattr(ut, "real_trader"):
                     ut.real_trader.user_id = "system_global"
            # -----------------------------------------------------

    # Register AI bot context for dashboard routes (best-effort, idempotent)
    try:
        if not getattr(app, "_ai_bot_context_registered", False):
            # Import here to avoid circular import at module load time
            from app.core.bot import register_ai_bot_context

            register_ai_bot_context(app, force=True)
            setattr(app, "_ai_bot_context_registered", True)
            app.logger.info("✅ AI bot context registered for Flask app")
    except Exception as exc:
        app.logger.warning("Failed to register AI bot context: %s", exc)

    # Integrate enhanced dashboard monitoring (guard against duplicate handler registration)
    try:
        if not getattr(app, "_dashboard_monitoring_integrated", False):
            from config.resource_manager import ResourceManager
            from integrations.dashboard_integration import (
                integrate_with_existing_dashboard,
            )

            resource_manager = ResourceManager()
            integrate_with_existing_dashboard(app, resource_manager)
            setattr(app, "_dashboard_monitoring_integrated", True)
            app.logger.info("✅ Enhanced dashboard monitoring integrated")
    except Exception as exc:
        app.logger.warning("Failed to integrate enhanced dashboard monitoring: %s", exc)

    # Check for UI asset build status
    _check_ui_assets(app)


def _create_bootstrap_users_if_requested(app) -> None:
    """Create bootstrap users if environment variables are set."""
    # Skip if running CLI commands
    if app.config.get("SKIP_RUNTIME_BOOTSTRAP"):
        return

    # Only create bootstrap users in development/test environments
    env = os.getenv("FLASK_ENV", "production").lower()
    if env not in ("development", "testing"):
        # In production, require explicit opt-in
        if not os.getenv("CREATE_BOOTSTRAP_USERS", "").lower() in ("1", "true", "yes"):
            return

    # Check if bootstrap users should be created
    create_bootstrap = os.getenv("CREATE_BOOTSTRAP_USERS", "").lower() in ("1", "true", "yes")

    # Alternative: check for specific user credentials
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not (create_bootstrap or (admin_email and admin_password)):
        return

    app.logger.info("🔧 Checking for bootstrap users...")

    from .models import User

    # Create admin user if specified
    if admin_email and admin_password:
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            admin_user = User(
                username=admin_email.split("@")[0],
                email=admin_email,
                is_admin=True,
                is_active=True,
                email_verified=True,
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            app.logger.info(f"✅ Bootstrap admin user created: {admin_email}")
        else:
            app.logger.info(f"ℹ️  Admin user already exists: {admin_email}")

    # Create default bootstrap users if requested
    if create_bootstrap:
        # Admin user
        admin_user = User.query.filter_by(email="admin@local").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@local",
                is_admin=True,
                is_active=True,
                email_verified=True,
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            app.logger.info("✅ Bootstrap admin user created: admin@local / admin123")

        # Test user
        test_user = User.query.filter_by(email="test@local").first()
        if not test_user:
            test_user = User(
                username="test",
                email="test@local",
                is_admin=False,
                is_active=True,
                email_verified=True,
            )
            test_user.set_password("test123")
            db.session.add(test_user)
            app.logger.info("✅ Bootstrap test user created: test@local / test123")

    db.session.commit()
    app.logger.info("🎉 Bootstrap users setup complete!")
