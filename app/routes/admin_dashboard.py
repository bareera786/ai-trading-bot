from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.tasks.manager import get_self_improvement_worker
from app.extensions import limiter
from app.auth.decorators import admin_required

admin_dashboard_bp = Blueprint("admin_dashboard", __name__, url_prefix="/admin")


@admin_dashboard_bp.route("/users", methods=["GET"], endpoint="user_management")
@login_required
@admin_required
@limiter.exempt
def user_management():
    return render_template("admin/user_management.html")


# Self-Improvement API Endpoints
@admin_dashboard_bp.route("/api/self-improvement/status", methods=["GET"])
@login_required
@admin_required
@limiter.exempt
def get_self_improvement_status():
    """Get current self-improvement system status."""

    try:
        worker = get_self_improvement_worker()
        if not worker:
            return jsonify({"error": "Self-improvement worker not available"}), 503

        # Get dashboard data which contains self-improvement telemetry
        dashboard_data = worker.dashboard_data

        return jsonify(dashboard_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/api/self-improvement/trigger-cycle", methods=["POST"])
@login_required
@admin_required
@limiter.exempt
def trigger_self_improvement_cycle():
    """Manually trigger a self-improvement cycle."""

    try:
        worker = get_self_improvement_worker()
        if not worker:
            return jsonify({"error": "Self-improvement worker not available"}), 503

        # Trigger immediate cycle
        worker.request_cycle("manual")

        return jsonify({"message": "Self-improvement cycle triggered successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/api/self-improvement/auto-fix", methods=["POST"])
@login_required
@admin_required
@limiter.exempt
def trigger_auto_fix():
    """Trigger a specific auto-fix action."""

    try:
        data = request.get_json()
        action = data.get("action")

        if not action:
            return jsonify({"error": "Action parameter required"}), 400

        worker = get_self_improvement_worker()
        if not worker:
            return jsonify({"error": "Self-improvement worker not available"}), 503

        # Check if the action is available
        if action not in worker.auto_fix_handlers:
            return jsonify({"error": f"Unknown auto-fix action: {action}"}), 400

        # Trigger the specific auto-fix (respecting cooldown/hysteresis)
        result = worker.execute_auto_fix_action(action)
        if not result.get("success"):
            return jsonify({"error": result.get("message", "Auto-fix rejected")}), 400

        return jsonify({"message": result.get("message")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/ribs", methods=["GET"])
@login_required
@admin_required
@limiter.exempt
def ribs_admin_page():
    """Admin UI for tuning RIBS deploy thresholds."""
    return render_template("admin/ribs_config.html")


@admin_dashboard_bp.route("/api/ribs/config", methods=["GET", "PUT"])
@login_required
@admin_required
@limiter.exempt
def admin_ribs_config():
    try:
        from app.services.ribs_admin import load_overrides, save_overrides

        overrides = load_overrides() or {}

        if request.method == "GET":
            # Return overrides and merged effective values
            base = {}
            # Read base defaults from TRADING_CONFIG if available
            try:
                from ai_ml_auto_bot_final import TRADING_CONFIG as BASE_TRADING_CONFIG

                base = {
                    "ribs_deploy_min_return": float(
                        BASE_TRADING_CONFIG.get("ribs_deploy_min_return", 0.0)
                    ),
                    "ribs_deploy_min_sharpe": float(
                        BASE_TRADING_CONFIG.get("ribs_deploy_min_sharpe", 0.0)
                    ),
                    "ribs_deploy_max_drawdown": float(
                        BASE_TRADING_CONFIG.get("ribs_deploy_max_drawdown", 100.0)
                    ),
                    "ribs_deploy_min_win_rate": float(
                        BASE_TRADING_CONFIG.get("ribs_deploy_min_win_rate", 0.0)
                    ),
                    "ribs_deploy_backtest_hours": int(
                        BASE_TRADING_CONFIG.get("ribs_deploy_backtest_hours", 168)
                    ),
                }
            except Exception:
                base = {}

            effective = dict(base)
            effective.update(overrides)

            return jsonify({"overrides": overrides, "effective": effective})

        # PUT -> update overrides
        data = request.get_json() or {}
        allowed = {
            "ribs_deploy_min_return": float,
            "ribs_deploy_min_sharpe": float,
            "ribs_deploy_max_drawdown": float,
            "ribs_deploy_min_win_rate": float,
            "ribs_deploy_backtest_hours": int,
        }

        new_overrides = dict(overrides)
        for k, v in data.items():
            if k not in allowed:
                continue
            try:
                new_overrides[k] = allowed[k](v)
            except Exception:
                return jsonify({"error": f"Invalid type for {k}"}), 400

        if not save_overrides(new_overrides):
            return jsonify({"error": "Failed to save overrides"}), 500

        # If possible, notify running self-improvement worker to pick up new values
        try:
            from app.tasks.manager import get_self_improvement_worker

            worker = get_self_improvement_worker()
            if worker:
                # Worker reads overrides at deploy time, but we can nudge dashboard data
                worker.dashboard_data.setdefault("self_improvement", {})[
                    "ribs_deploy_overrides"
                ] = new_overrides
        except Exception:
            pass

        return jsonify({"success": True, "overrides": new_overrides})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Model Management Routes
@admin_dashboard_bp.route("/models", methods=["GET"], endpoint="model_management")
@login_required
@limiter.exempt
def model_management():
    """Model management dashboard."""
    if not getattr(current_user, "is_admin", False):
        return "Forbidden", 403
    return render_template("admin/model_management.html")


@admin_dashboard_bp.route("/api/models/status", methods=["GET"])
@login_required
@limiter.exempt
def get_model_status():
    """Get comprehensive model status across all profiles."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

    try:
        from app.ml import ModelRegistry

        # Initialize registry with default path
        registry = ModelRegistry("./models/registry")

        # Get all profiles and their status
        profiles = {}
        registry_data = registry._load_registry()

        for profile_name, profile_data in registry_data.items():
            active_info = registry.get_model_info(profile_name)
            versions = registry.list_versions(profile_name)

            profiles[profile_name] = {
                "active_version": active_info.get("active") if active_info else None,
                "performance": active_info.get("performance") if active_info else None,
                "timestamp": active_info.get("timestamp") if active_info else None,
                "total_versions": len(versions),
                "versions": versions[-5:]  # Last 5 versions
            }

        # Get filesystem model status (existing models not in registry)
        import os
        filesystem_models = {}

        model_dirs = ["./ultimate_models", "./optimized_models", "./futures_models"]
        for model_dir in model_dirs:
            if os.path.exists(model_dir):
                profile_name = os.path.basename(model_dir)
                filesystem_models[profile_name] = []

                for root, dirs, files in os.walk(model_dir):
                    for file in files:
                        if file.endswith('.pkl'):
                            filesystem_models[profile_name].append({
                                "filename": file,
                                "path": os.path.join(root, file),
                                "size": os.path.getsize(os.path.join(root, file))
                            })

        return jsonify({
            "registry_models": profiles,
            "filesystem_models": filesystem_models,
            "registry_path": "./models/registry"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/api/models/rollback", methods=["POST"])
@login_required
@limiter.exempt
def rollback_model():
    """Rollback a model to previous or specific version."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

    try:
        data = request.get_json()
        profile = data.get("profile")
        target_version = data.get("target_version")

        if not profile:
            return jsonify({"error": "Profile is required"}), 400

        from app.ml import ModelRegistry
        registry = ModelRegistry("./models/registry")

        success = registry.rollback_model(profile, target_version)

        if success:
            # Get updated info
            info = registry.get_model_info(profile)
            return jsonify({
                "success": True,
                "message": f"Successfully rolled back {profile}",
                "new_active_version": info.get("active") if info else None
            })
        else:
            return jsonify({"error": "Rollback failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/api/models/cleanup", methods=["POST"])
@login_required
@limiter.exempt
def cleanup_models():
    """Clean up old model versions."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

    try:
        data = request.get_json()
        profile = data.get("profile", "all")
        keep_count = data.get("keep_count", 5)

        from app.ml import ModelRegistry
        registry = ModelRegistry("./models/registry")

        if profile == "all":
            # Cleanup all profiles
            registry_data = registry._load_registry()
            cleaned_profiles = []

            for profile_name in registry_data.keys():
                registry.cleanup_old_versions(profile_name, keep_count)
                cleaned_profiles.append(profile_name)
        else:
            # Cleanup specific profile
            registry.cleanup_old_versions(profile, keep_count)
            cleaned_profiles = [profile]

        return jsonify({
            "success": True,
            "message": f"Cleaned up old versions for: {', '.join(cleaned_profiles)}",
            "keep_count": keep_count
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_dashboard_bp.route("/api/models/register", methods=["POST"])
@login_required
@limiter.exempt
def register_model():
    """Manually register a model file."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

    try:
        data = request.get_json()
        model_path = data.get("model_path")
        profile = data.get("profile")
        metadata = data.get("metadata", {})

        if not model_path or not profile:
            return jsonify({"error": "Model path and profile are required"}), 400

        if not os.path.exists(model_path):
            return jsonify({"error": "Model file does not exist"}), 404

        # Load the model
        import pickle
        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        # Register with registry
        from app.ml import ModelRegistry
        registry = ModelRegistry("./models/registry")

        metadata["profile"] = profile
        metadata["manually_registered"] = True
        metadata["source_path"] = model_path

        version = registry.register_model(model, metadata)

        return jsonify({
            "success": True,
            "message": f"Model registered as version {version}",
            "version": version
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
