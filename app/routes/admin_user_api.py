from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models import User
from app.extensions import db, limiter

admin_user_api_bp = Blueprint("admin_user_api", __name__, url_prefix="/api/users")


@admin_user_api_bp.route("", methods=["GET"])
@login_required
@limiter.exempt
def list_users():
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    search = request.args.get("search", "")
    query = User.query
    if search:
        query = query.filter(
            (User.username.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
            | (User.id == search if search.isdigit() else False)
        )
    users = query.order_by(User.id.desc()).all()
    return jsonify(
        {
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "email": u.email,
                    "balance": getattr(u, "balance", 0.0),  # Default to 0 if not set
                    "portfolio_value": getattr(
                        u, "portfolio_value", 0.0
                    ),  # Add if available
                    "trade_count": len(u.trades) if u.trades else 0,
                    "subscription_expiry": getattr(
                        u.active_subscription, "expiry", None
                    ),
                    "subscription_history": [
                        {
                            "plan": s.plan.code if s.plan else "unknown",
                            "start": s.created_at.isoformat() if s.created_at else None,
                            "end": s.expiry.isoformat() if s.expiry else None,
                            "is_active": s.is_active,
                        }
                        for s in u.subscriptions
                    ]
                    if u.subscriptions
                    else [],
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                }
                for u in users
            ]
        }
    )


@admin_user_api_bp.route("/<int:user_id>", methods=["GET"])
@login_required
@limiter.exempt
def get_user(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    return jsonify(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "balance": getattr(user, "balance", 0.0),
            "portfolio_value": getattr(user, "portfolio_value", 0.0),
            "trade_count": len(user.trades) if user.trades else 0,
            "subscription_expiry": getattr(user.active_subscription, "expiry", None),
            "subscription_history": [
                {
                    "plan": s.plan.code if s.plan else "unknown",
                    "start": s.created_at.isoformat() if s.created_at else None,
                    "end": s.expiry.isoformat() if s.expiry else None,
                    "is_active": s.is_active,
                }
                for s in user.subscriptions
            ]
            if user.subscriptions
            else [],
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }
    )


@admin_user_api_bp.route("/<int:user_id>/toggle", methods=["POST"])
@login_required
@limiter.exempt
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
@limiter.exempt
def edit_user(user_id):
    if not getattr(current_user, "is_admin", False):
        return jsonify({"error": "Forbidden"}), 403
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    user.username = data.get("username", user.username)
    user.email = data.get("email", user.email)
    if "balance" in data:
        user.balance = float(data["balance"]) if data["balance"] else 0.0
    if "portfolio_value" in data:
        user.portfolio_value = (
            float(data["portfolio_value"]) if data["portfolio_value"] else 0.0
        )
    # Subscription expiry update (if applicable)
    if (
        "subscription_expiry" in data
        and hasattr(user, "active_subscription")
        and user.active_subscription
    ):
        user.active_subscription.expiry = data["subscription_expiry"]
    db.session.commit()
    return jsonify({"success": True})
