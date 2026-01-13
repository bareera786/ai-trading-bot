"""Admin user management API blueprint."""
from __future__ import annotations

import time

from flask import Blueprint, jsonify, request, session
from flask_login import current_user

from app.auth.decorators import admin_required
from app.extensions import db
from app.models import (
    SubscriptionPlan,
    User,
    UserPortfolio,
    UserSubscription,
    UserTrade,
)
from app.subscriptions import (
    assign_subscription_to_user,
    serialize_subscription,
    coerce_bool,
)

admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/api")


@admin_users_bp.route("/users", methods=["GET"])
@admin_required
def api_get_users():
    """Return all users with portfolio and subscription summaries."""
    try:
        users = User.query.all()
        users_data = []
        for user in users:
            portfolio = UserPortfolio.query.filter_by(user_id=user.id).first()
            trade_count = UserTrade.query.filter_by(user_id=user.id).count()
            users_data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "portfolio_value": (portfolio.total_balance if portfolio else 0),
                    "trade_count": trade_count,
                    "created_at": user.created_at.isoformat()
                    if user.created_at
                    else None,
                    "last_login": user.last_login.isoformat()
                    if user.last_login
                    else None,
                    "subscription": serialize_subscription(user.active_subscription),
                }
            )

        return jsonify(
            {
                "success": True,
                "users": users_data,
                "total_users": len(users_data),
                "timestamp": time.time(),
            }
        )
    except Exception as exc:
        print(f"Error in /api/users GET: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_users_bp.route("/users", methods=["POST"])
@admin_required
def api_create_user():
    """Create a new user and assign a default portfolio/trial subscription."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        is_admin = coerce_bool(data.get("is_admin"), default=False)
        is_active = coerce_bool(data.get("is_active"), default=True)

        if not username or not email or not password:
            return jsonify({"error": "Username, email, and password are required"}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists"}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 400

        new_user = User(
            username=username, email=email, is_admin=is_admin, is_active=is_active
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        # Initialize portfolio
        portfolio = UserPortfolio(
            user_id=new_user.id,
            total_balance=10000.0,
            available_balance=10000.0,
            open_positions={},
        )
        db.session.add(portfolio)
        db.session.commit()

        # Assign default trial subscription if available
        trial_plan = SubscriptionPlan.query.filter_by(
            plan_type="trial", is_active=True
        ).first()
        if trial_plan:
            try:
                assign_subscription_to_user(
                    new_user,
                    trial_plan,
                    auto_renew=False,
                    cancel_existing=True,
                    notes="Auto-issued trial on account creation",
                )
            except Exception as sub_exc:
                print(f"⚠️ Failed to assign trial subscription: {sub_exc}")
                db.session.rollback()

        subscription_info = serialize_subscription(new_user.active_subscription)
        session.modified = True

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"User {username} created successfully",
                    "user": {
                        "id": new_user.id,
                        "username": new_user.username,
                        "email": new_user.email,
                        "is_admin": new_user.is_admin,
                        "is_active": new_user.is_active,
                        "portfolio_value": portfolio.total_balance,
                        "created_at": new_user.created_at.isoformat()
                        if new_user.created_at
                        else None,
                        "subscription": subscription_info,
                    },
                }
            ),
            201,
        )
    except Exception as exc:
        db.session.rollback()
        print(f"Error in /api/users POST: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_users_bp.route("/users/<username>", methods=["DELETE"])
@admin_required
def api_delete_user(username):
    """Delete non-self accounts including portfolio and trades."""
    try:
        if username == current_user.username:
            return jsonify({"error": "Cannot delete your own account"}), 400

        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        UserPortfolio.query.filter_by(user_id=user.id).delete()
        UserTrade.query.filter_by(user_id=user.id).delete()
        UserSubscription.query.filter_by(user_id=user.id).delete()

        db.session.delete(user)
        db.session.commit()
        session.modified = True

        return jsonify(
            {"success": True, "message": f"User {username} deleted successfully"}
        )
    except Exception as exc:
        db.session.rollback()
        print(f"Error in /api/users/{username} DELETE: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_users_bp.route("/users/<username>", methods=["PUT"])
@admin_required
def api_update_user(username):
    """Update account metadata or credentials."""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        user.email = data.get("email", user.email)
        is_admin_value = data.get("is_admin", user.is_admin)
        user.role = "admin" if is_admin_value else "viewer"
        user.is_active = data.get("is_active", user.is_active)
        if data.get("password"):
            user.set_password(data["password"])

        db.session.commit()
        return jsonify(
            {"success": True, "message": f"User {username} updated successfully"}
        )
    except Exception as exc:
        db.session.rollback()
        print(f"Error in /api/users/{username} PUT: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_users_bp.route("/users/<username>", methods=["GET"])
@admin_required
def api_get_user_details(username):
    """Return detailed user info for admin view."""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        portfolio = UserPortfolio.query.filter_by(user_id=user.id).first()
        trade_count = UserTrade.query.filter_by(user_id=user.id).count()
        return jsonify(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "portfolio_value": portfolio.total_balance if portfolio else 0,
                "trade_count": trade_count,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "subscription": serialize_subscription(user.active_subscription),
            }
        )
    except Exception as exc:
        print(f"Error in /api/users/{username} GET: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_users_bp.route("/users/<username>/activity", methods=["GET"])
@admin_required
def api_get_user_activity(username):
    """Get user activity log."""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Get recent trades as activity
        recent_trades = UserTrade.query.filter_by(user_id=user.id).order_by(
            UserTrade.timestamp.desc()
        ).limit(10).all()

        activity = []
        for trade in recent_trades:
            activity.append({
                "type": "trade",
                "timestamp": trade.timestamp.isoformat() if trade.timestamp else None,
                "description": f"Trade: {trade.symbol} {trade.side} {trade.quantity} @ {trade.price}",
                "details": {
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "pnl": trade.pnl
                }
            })

        # Add login activity if available
        if user.last_login:
            activity.append({
                "type": "login",
                "timestamp": user.last_login.isoformat(),
                "description": "User logged in",
                "details": {}
            })

        # Sort by timestamp descending
        activity.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return jsonify({
            "success": True,
            "username": username,
            "activity": activity[:20]  # Limit to 20 most recent
        })

    except Exception as exc:
        print(f"Error in /api/users/{username}/activity GET: {exc}")
        return jsonify({"error": str(exc)}), 500


@admin_users_bp.route("/users/<username>/permissions", methods=["PUT"])
@admin_required
def api_update_user_permissions(username):
    """Update user permissions and roles."""
    try:
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Prevent self-demotion for security
        if username == current_user.username and not coerce_bool(data.get("is_admin"), user.is_admin):
            return jsonify({"error": "Cannot remove admin privileges from yourself"}), 400

        is_admin_value = coerce_bool(data.get("is_admin"), user.is_admin)
        user.role = "admin" if is_admin_value else "viewer"
        user.is_active = coerce_bool(data.get("is_active"), user.is_active)

        # Add additional permission fields if they exist in the model
        if hasattr(user, 'can_trade'):
            user.can_trade = coerce_bool(data.get("can_trade"), getattr(user, 'can_trade', True))
        if hasattr(user, 'can_backtest'):
            user.can_backtest = coerce_bool(data.get("can_backtest"), getattr(user, 'can_backtest', True))

        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Permissions updated for user {username}",
            "user": {
                "username": user.username,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "can_trade": getattr(user, 'can_trade', True),
                "can_backtest": getattr(user, 'can_backtest', True)
            }
        })

    except Exception as exc:
        db.session.rollback()
        print(f"Error in /api/users/{username}/permissions PUT: {exc}")
        return jsonify({"error": str(exc)}), 500
