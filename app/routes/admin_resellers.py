"""Admin routes for Reseller management."""
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.auth.decorators import admin_required
from app.models import Reseller, User
from app.extensions import db, limiter
from sqlalchemy.exc import IntegrityError
import uuid

admin_resellers_bp = Blueprint("admin_resellers", __name__, url_prefix="/admin")

@admin_resellers_bp.route("/resellers", methods=["GET"])
@login_required
@admin_required
def resellers_dashboard():
    """Render the Reseller Management UI."""
    return render_template("admin/resellers.html")

@admin_resellers_bp.route("/api/resellers-list", methods=["GET"])
@login_required
@admin_required
@limiter.exempt  # Admin internal API
def list_all_resellers():
    """API to list all resellers with user counts."""
    resellers = Reseller.query.all()
    
    result = []
    for r in resellers:
        # Calculate current user count efficiently
        count = User.query.filter_by(reseller_id=r.id).count()
        
        result.append({
            "id": r.id,
            "name": r.name,
            "owner_id": str(r.owner_id),
            "user_count": count,
            "limits": r.limits_config,
            "branding": r.branding_config
        })
        
    return jsonify({"resellers": result})

@admin_resellers_bp.route("/api/resellers", methods=["POST"])
@login_required
@admin_required
def create_reseller():
    """Create a new reseller account."""
    data = request.get_json()
    
    name = data.get("name")
    owner_id_str = data.get("owner_id")
    limits = data.get("limits_config", {})
    
    if not name or not owner_id_str:
        return jsonify({"error": "Name and Owner ID are required"}), 400
        
    try:
        # Validate Owner Exists
        try:
            owner_uuid = uuid.UUID(owner_id_str)
        except ValueError:
            return jsonify({"error": "Invalid UUID format for Owner ID"}), 400
            
        owner = db.session.get(User, owner_uuid)
        if not owner:
            return jsonify({"error": "User with specified ID not found"}), 404
            
        # Create Reseller
        new_reseller = Reseller(
            name=name,
            owner_id=owner_uuid,
            limits_config=limits,
            branding_config={}
        )
        
        db.session.add(new_reseller)
        db.session.commit()
        
        return jsonify({"success": True, "reseller_id": str(new_reseller.id), "message": "Reseller created successfully"})
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Reseller with this name already exists"}), 409
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin_resellers_bp.route("/api/resellers/<reseller_id>/branding", methods=["PUT"])
@login_required
@admin_required
def update_reseller_branding(reseller_id):
    """Update branding configuration for a reseller."""
    data = request.get_json()
    
    try:
        r_uuid = uuid.UUID(reseller_id)
        reseller = db.session.get(Reseller, r_uuid)
        
        if not reseller:
            return jsonify({"error": "Reseller not found"}), 404
            
        # Update branding config (merge or overwrite)
        current_branding = reseller.branding_config or {}
        
        # Whitelist allowed keys for safety
        allowed_keys = ["logo_url", "primary_color", "company_name", "support_email"]
        for k in allowed_keys:
            if k in data:
                current_branding[k] = data[k]
                
        # Trigger SQLAlchemy update detection
        reseller.branding_config = dict(current_branding)
        
        db.session.commit()
        
        return jsonify({"success": True, "branding": reseller.branding_config})
        
    except ValueError:
        return jsonify({"error": "Invalid Reseller ID format"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
