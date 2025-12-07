"""Server-rendered admin views for operational dashboards."""
from __future__ import annotations

from flask import Blueprint, render_template

from app.auth.decorators import admin_required
from app.models import Lead

admin_views_bp = Blueprint('admin_views', __name__)


@admin_views_bp.route('/admin/leads')
@admin_required
def admin_leads_page():
    leads = Lead.query.order_by(Lead.created_at.desc()).limit(100).all()
    return render_template('admin/leads.html', leads=leads)
