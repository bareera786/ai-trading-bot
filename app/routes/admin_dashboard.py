from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.tasks.manager import get_self_improvement_worker
from app.extensions import limiter

admin_dashboard_bp = Blueprint("admin_dashboard", __name__, url_prefix="/admin")


@admin_dashboard_bp.route("/users", methods=["GET"], endpoint="user_management")
@login_required
@limiter.exempt
def user_management():
    if not getattr(current_user, "is_admin", False):
        return "Forbidden", 403
    return render_template("admin/user_management.html")


# Self-Improvement API Endpoints
@admin_dashboard_bp.route("/api/self-improvement/status", methods=["GET"])
@login_required
@limiter.exempt
def get_self_improvement_status():
    """Get current self-improvement system status."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

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
@limiter.exempt
def trigger_self_improvement_cycle():
    """Manually trigger a self-improvement cycle."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

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
@limiter.exempt
def trigger_auto_fix():
    """Trigger a specific auto-fix action."""
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

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
@limiter.exempt
def ribs_admin_page():
    """Admin UI for tuning RIBS deploy thresholds."""
    if not getattr(current_user, "is_admin", False):
        return "Forbidden", 403
    return render_template("admin/ribs_config.html")


@admin_dashboard_bp.route("/api/ribs/config", methods=["GET", "PUT"])
@login_required
@limiter.exempt
def admin_ribs_config():
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403

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
