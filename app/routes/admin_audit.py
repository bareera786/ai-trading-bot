
from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
from sqlalchemy import desc
from app.models import AuditLog, User, requires_role
from app.extensions import db

admin_audit_bp = Blueprint('admin_audit', __name__, url_prefix='/admin/audit')

@admin_audit_bp.route('/')
@login_required
@requires_role('admin')
def index():
    """Admin Audit Log Dashboard."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # filters
    action_filter = request.args.get('action')
    user_filter = request.args.get('user_id')
    
    query = AuditLog.query

    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    
    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)

    # Eager load user relationship
    pagination = query.order_by(desc(AuditLog.timestamp)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    logs = pagination.items
    
    return render_template(
        'admin/audit_log.html',
        logs=logs,
        pagination=pagination,
        action_filter=action_filter,
        user_filter=user_filter
    )
