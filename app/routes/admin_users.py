from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User
from app.utils.decorators import admin_required
from app.services.binance import BinanceCredentialService, BinanceCredentialStore

admin_users_bp = Blueprint("admin_users", __name__, url_prefix="/admin/users")

@admin_users_bp.route("/", methods=["GET"])
@login_required
@admin_required
def list_users():
    """List all registered users with pagination."""
    page = request.args.get("page", 1, type=int)
    per_page = 20
    query = request.args.get("q", "")

    base_query = User.query
    if query:
        base_query = base_query.filter(User.username.ilike(f"%{query}%") | User.email.ilike(f"%{query}%"))

    users_pagination = base_query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)

    return render_template("admin/users.html", users=users_pagination, search_query=query)

@admin_users_bp.route("/<uuid:user_id>/toggle-status", methods=["POST"])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active/banned status."""
    user = User.query.get_or_404(user_id)
    
    # Prevent banning yourself
    if user.id == current_user.id:
        flash("You cannot ban yourself.", "danger")
        return redirect(url_for("admin_users.list_users"))

    user.is_active = not user.is_active
    db.session.commit()
    
    status = "activated" if user.is_active else "banned"
    flash(f"User {user.username} has been {status}.", "success")
    return redirect(url_for("admin_users.list_users"))

@admin_users_bp.route("/<uuid:user_id>/promote", methods=["POST"])
@login_required
@admin_required
def promote_user(user_id):
    """Toggle user admin status."""
    user = User.query.get_or_404(user_id)
    
    # Prevent demoting yourself
    if user.id == current_user.id:
        flash("You cannot remove your own admin privileges.", "danger")
        return redirect(url_for("admin_users.list_users"))

    user.is_admin = not user.is_admin
    db.session.commit()
    
    role = "Admin" if user.is_admin else "Trader"
    flash(f"User {user.username} is now a {role}.", "success")
    return redirect(url_for("admin_users.list_users"))

@admin_users_bp.route("/<uuid:user_id>/details", methods=["GET"])
@login_required
@admin_required
def user_details(user_id):
    """Get detailed JSON info for a user (for modal)."""
    user = User.query.get_or_404(user_id)
    
    # Get recent activity or stats if available
    # For now, just return basic info + trade count
    trade_count = 0 # Placeholder until we query UserTrade count
    
    return jsonify({
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "Never",
        "trade_count": trade_count
    })
