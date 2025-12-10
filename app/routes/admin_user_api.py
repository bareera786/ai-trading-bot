from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import User
from app.extensions import db

admin_user_api_bp = Blueprint("admin_user_api", __name__, url_prefix="/api/users")

@admin_user_api_bp.route("", methods=["GET"])
@login_required
def list_users():
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    search = request.args.get("search", "")
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.id == search if search.isdigit() else False)
        )
    users = query.order_by(User.id.desc()).all()
    return jsonify({
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "balance": getattr(u, "balance", None),
                "subscription_expiry": getattr(u.active_subscription, "expiry", None),
                "is_active": u.is_active,
            } for u in users
        ]
    })

@admin_user_api_bp.route("/<int:user_id>", methods=["GET"])
@login_required
def get_user(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "balance": getattr(user, "balance", None),
        "subscription_expiry": getattr(user.active_subscription, "expiry", None),
        "is_active": user.is_active,
    })

@admin_user_api_bp.route("/<int:user_id>/toggle", methods=["POST"])
@login_required
def toggle_user(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    user.is_active = data.get("is_active", not user.is_active)
    db.session.commit()
    return jsonify({"success": True, "is_active": user.is_active})

@admin_user_api_bp.route("/<int:user_id>", methods=["PUT"])
@login_required
def edit_user(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    user.username = data.get("username", user.username)
    user.email = data.get("email", user.email)
    if "balance" in data:
        user.balance = data["balance"]
    # Subscription expiry update (if applicable)
    if "subscription_expiry" in data and hasattr(user, "active_subscription") and user.active_subscription:
        user.active_subscription.expiry = data["subscription_expiry"]
    db.session.commit()
    return jsonify({"success": True})
