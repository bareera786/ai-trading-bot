"""API endpoints for managing Resellers."""
from flask import Blueprint, jsonify, request
from app.auth.decorators import admin_required
from app.services.reseller_service import ResellerService
from app.models import Reseller, User

reseller_bp = Blueprint("reseller", __name__, url_prefix="/api/reseller")

@reseller_bp.route("", methods=["POST"])
@admin_required
def create_reseller():
    """Create a new reseller."""
    data = request.get_json() or {}
    name = data.get("name")
    owner_id = data.get("owner_id")
    limits_config = data.get("limits_config")
    
    if not name or not owner_id:
        return jsonify({"error": "name and owner_id are required"}), 400
        
    try:
        reseller = ResellerService.create_reseller(name, owner_id, limits_config)
        return jsonify({
            "success": True, 
            "reseller": {
                "id": reseller.id,
                "name": reseller.name
            }
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@reseller_bp.route("/<reseller_id>/users", methods=["POST"])
@admin_required
def assign_user(reseller_id):
    """Assign a user to a reseller."""
    data = request.get_json() or {}
    user_id = data.get("user_id")
    
    if not user_id:
        return jsonify({"error": "user_id is required"}), 400
        
    try:
        ResellerService.assign_user_to_reseller(user_id, reseller_id)
        return jsonify({"success": True, "message": "User assigned to reseller"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@reseller_bp.route("/<reseller_id>/users", methods=["GET"])
@admin_required
def list_users(reseller_id):
    """List users belonging to a reseller."""
    users = User.query.filter_by(reseller_id=reseller_id).all()
    user_list = [
        {"id": u.id, "username": u.username, "email": u.email, "role": u.reseller_role}
        for u in users
    ]
    return jsonify({"users": user_list})

@reseller_bp.route("/<reseller_id>/branding", methods=["PUT"])
@admin_required
def update_branding(reseller_id):
    """Update branding configuration for a reseller."""
    data = request.get_json() or {}
    reseller = Reseller.query.get(reseller_id)
    
    if not reseller:
        return jsonify({"error": "Reseller not found"}), 404
        
    # Merge existing with new
    current_config = reseller.branding_config or {}
    current_config.update(data)
    reseller.branding_config = current_config
    
    from app.extensions import db
    db.session.commit()
    
    return jsonify({"success": True, "branding": reseller.branding_config})
