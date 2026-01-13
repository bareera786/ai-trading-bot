from flask import Blueprint, request, jsonify, abort, render_template, g
from flask_login import current_user
from app.models import User, db, requires_role, AuditLog

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Admin Dashboard
@admin_bp.route("/")
def admin_dashboard():
    return render_template("admin_dashboard.html")

# Create a new user
@admin_bp.route("/users", methods=["POST"])
@requires_role("admin")
def create_user():
    data = request.get_json()
    if not data:
        abort(400, "Invalid request payload")

    user = User(
        username=data["username"],
        email=data["email"],
        role=data.get("role", "viewer"),
    )
    user.set_password(data["password"])

    db.session.add(user)
    db.session.commit()

    log_audit_event(
        actor_user_id=current_user.id,
        target_user_id=user.id,
        action="create_user",
        metadata={"username": user.username, "email": user.email},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )

    return jsonify({"message": "User created successfully", "user_id": user.id}), 201

# Get all users
@admin_bp.route("/users", methods=["GET"])
@requires_role("admin")
def get_users():
    users = User.query.all()
    return jsonify([{
        "id": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active
    } for user in users])

# Get a specific user
@admin_bp.route("/users/<uuid:user_id>", methods=["GET"])
@requires_role("admin")
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active,
    })

# Update a user
@admin_bp.route("/users/<uuid:user_id>", methods=["PATCH"])
@requires_role("admin")
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if "username" in data:
        user.username = data["username"]
    if "email" in data:
        user.email = data["email"]
    if "role" in data:
        user.role = data["role"]

    db.session.commit()
    log_audit_event(
        actor_user_id=current_user.id,
        target_user_id=user.id,
        action="update_user",
        metadata={"username": user.username, "email": user.email},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    return jsonify({"message": "User updated successfully"})

# Delete a user
@admin_bp.route("/users/<uuid:user_id>", methods=["DELETE"])
@requires_role("admin")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    log_audit_event(
        actor_user_id=current_user.id,
        target_user_id=user.id,
        action="delete_user",
        metadata={"username": user.username, "email": user.email},
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    return jsonify({"message": "User deleted successfully"})

# Function to log audit events
def log_audit_event(actor_user_id, target_user_id, action, metadata=None, ip_address=None, user_agent=None):
    import json
    details = {
        "target_user_id": target_user_id,
        "metadata": metadata,
        "ip_address": ip_address,
        "user_agent": user_agent
    }
    audit_log = AuditLog(
        user_id=actor_user_id,  # type: ignore
        action=action,  # type: ignore
        details=json.dumps(details)  # type: ignore
    )
    db.session.add(audit_log)
    db.session.commit()

# Placeholder for fetching users from the database
@admin_bp.route('/users', methods=['GET'])
def placeholder_get_users():
    users = [
        {"id": 1, "username": "admin", "role": "admin"},
        {"id": 2, "username": "user1", "role": "user"}
    ]
    return jsonify(users)

# Placeholder for adding a user
@admin_bp.route('/users', methods=['POST'])
def placeholder_add_user():
    data = request.json
    return jsonify({"message": "User added", "data": data}), 201

# Placeholder for editing a user
@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
def placeholder_edit_user(user_id):
    data = request.json
    return jsonify({"message": "User updated", "user_id": user_id, "data": data})

# Placeholder for deleting a user
@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
def placeholder_delete_user(user_id):
    return jsonify({"message": "User deleted", "user_id": user_id})