from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import AuditLog, User
from app.extensions import db

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')

@audit_bp.route('/logs', methods=['GET'])
@jwt_required()
def get_audit_logs():
    # Ensure only admins can access this endpoint
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    if not current_user or current_user.role != 'ADMIN':
        return jsonify({'error': 'Access denied'}), 403

    # Fetch audit logs
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    log_list = [
        {
            'id': log.id,
            'user_id': log.user_id,
            'action': log.action,
            'timestamp': log.timestamp,
            'details': log.details
        } for log in logs
    ]
    return jsonify(log_list), 200