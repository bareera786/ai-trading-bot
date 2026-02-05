from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import User, UserPortfolio, UserTrade, AuditLog
from app.auth.decorators import admin_required
from datetime import datetime
import uuid
import json

# Mounts at /admin/api via Blueprint registration or explicit prefix here?
# We will define the prefix in the Blueprint creation to be safe.
admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/admin/api")

def log_admin_action(action: str, target_id: uuid.UUID, details: dict = None):
    """Helper to record immutable audit logs for admin actions."""
    try:
        log = AuditLog(
            user_id=current_user.id,
            action=action,
            details=json.dumps(details) if details else None
        )
        # Note: We rely on the caller to commit the transaction to atomicity
        db.session.add(log)
    except Exception as e:
        # Should not block the action but must be logged
        print(f"FAILED TO WRITE AUDIT LOG: {e}")

@admin_api_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def api_list_users():
    """List all users for admin dashboard."""
    users = User.query.order_by(User.created_at.desc()).all()
    users_data = []
    
    for user in users:
        # Avoid crashing if UserPortfolio missing
        portfolio = UserPortfolio.query.filter_by(user_id=user.id).first()
        
        users_data.append({
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "portfolio_value": portfolio.total_balance if portfolio else 0
        })
        
    return jsonify({"users": users_data})

@admin_api_bp.route("/users", methods=["POST"])
@login_required
@admin_required
def api_create_user():
    """Create a new user."""
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    is_admin = data.get("is_admin", False)

    if not username or not password or not email:
        return jsonify({"error": "Username, email, and password required"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409
        
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    user.is_admin = bool(is_admin)
    user.is_active = True
    
    db.session.add(user)
    log_admin_action("create_user", user.id, {"username": username, "email": email, "is_admin": is_admin})
    db.session.commit()
    
    return jsonify({"success": True, "message": "User created", "id": str(user.id)})

@admin_api_bp.route("/users/<uuid:user_id>", methods=["PUT"])
@login_required
@admin_required
def api_update_user(user_id):
    """Update user details."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    # Prevent modifying self role/active status if it's the current user
    if user.id == current_user.id:
        if "is_admin" in data and data["is_admin"] is False:
             return jsonify({"error": "Cannot remove your own admin privileges"}), 400
        if "is_active" in data and data["is_active"] is False:
             return jsonify({"error": "Cannot ban yourself"}), 400

    if "email" in data:
        user.email = data["email"]
    if "is_admin" in data:
        user.is_admin = bool(data["is_admin"])
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "password" in data and data["password"]:
        user.set_password(data["password"])
        
    log_admin_action("update_user", user.id, data)
    db.session.commit()
    return jsonify({"success": True, "message": "User updated"})

@admin_api_bp.route("/users/<uuid:user_id>/status", methods=["PUT"])
@login_required
@admin_required
def api_toggle_user_status(user_id):
    """Toggle specific status (ban/unban)."""
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if user.id == current_user.id:
         return jsonify({"error": "Cannot change your own status"}), 400

    new_status = bool(data.get("is_active")) if "is_active" in data else user.is_active
    
    # CRITICAL: Prevent banning if user has open positions (Orphaned Position Risk)
    if "is_active" in data and not new_status and user.is_active:
        open_trades = UserTrade.query.filter_by(user_id=user.id, status="open").count()
        if open_trades > 0:
            return jsonify({
                "error": "BLOCK_BAN_RISK", 
                "message": f"Cannot ban user with {open_trades} open active trades. Close them first."
            }), 409

    if "is_active" in data:
        user.is_active = new_status
    
    log_admin_action("toggle_status", user.id, {"new_is_active": user.is_active})
    db.session.commit()
    return jsonify({"success": True, "message": "Status updated", "is_active": user.is_active})

@admin_api_bp.route("/users/<uuid:user_id>", methods=["DELETE"])
@login_required
@admin_required
def api_delete_user(user_id):
    """Delete a user."""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({"error": "Cannot delete yourself"}), 400
        
    db.session.delete(user)
    log_admin_action("delete_user", user.id, {"username": user.username})
    db.session.commit()
    return jsonify({"success": True, "message": "User deleted"})

@admin_api_bp.route("/kill-switch", methods=["GET", "POST"])
@login_required
@admin_required
def api_kill_switch():
    """Get or Set Global Kill Switch status."""
    from app.services.protection import ProtectionService
    
    if request.method == "GET":
        is_active = ProtectionService.is_kill_switch_active()
        return jsonify({"active": is_active})
        
    if request.method == "POST":
        data = request.get_json()
        should_activate = bool(data.get("active"))
        
        # Verify it's a real intent (double check/confirmation usually handles UI side)
        ProtectionService.set_kill_switch(should_activate, user_id=current_user.id)
        
        status_str = "ACTIVATED" if should_activate else "DEACTIVATED"
        log_admin_action("kill_switch_toggle", current_user.id, {"status": status_str})
        
        return jsonify({
            "success": True, 
            "message": f"Global Kill Switch {status_str}", 
            "active": should_activate
        })

