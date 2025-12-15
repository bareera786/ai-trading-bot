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
