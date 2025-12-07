"""Lead capture and administration routes."""
from __future__ import annotations

import csv
import io
import re
import time
from typing import Any, Dict

import requests
from flask import Blueprint, current_app, jsonify, request, send_file

from app.auth.decorators import admin_required
from app.extensions import db
from app.models import Lead

leads_bp = Blueprint('leads', __name__, url_prefix='/api/leads')

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_rate_limit_tracker: Dict[str, float] = {}


def _rate_key() -> str:
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    return (ip or 'unknown').split(',')[0].strip() or 'unknown'


def _is_rate_limited(ttl: int) -> tuple[bool, float]:
    key = _rate_key()
    now = time.time()
    last = _rate_limit_tracker.get(key, 0.0)
    remaining = max(0.0, ttl - (now - last))
    return remaining > 0.0, remaining


def _mark_submission() -> None:
    key = _rate_key()
    _rate_limit_tracker[key] = time.time()


def _notify_ops(lead: Lead) -> None:
    webhook = current_app.config.get('LEAD_NOTIFICATION_WEBHOOK')
    payload = {
        'text': f"New lead captured: {lead.name} ({lead.email})",
        'details': lead.to_dict(),
    }
    if not webhook:
        current_app.logger.info("Lead captured: %s", payload['text'])
        return

    try:
        response = requests.post(webhook, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - notification best effort
        current_app.logger.warning('Failed to notify webhook for lead %s: %s', lead.email, exc)


@leads_bp.route('', methods=['POST'])
def capture_lead():
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    company = (data.get('company') or '').strip()
    message = (data.get('message') or data.get('notes') or '').strip()
    source = (data.get('source') or 'marketing_form').strip()

    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400
    if not _EMAIL_RE.match(email):
        return jsonify({'error': 'Email address is invalid'}), 400

    ttl = int(current_app.config.get('LEAD_RATE_LIMIT_SECONDS', 90))
    limited, remaining = _is_rate_limited(ttl)
    if limited:
        return jsonify({'error': 'Please wait before submitting again', 'retry_after_seconds': int(remaining)}), 429

    lead = Lead(
        name=name,
        email=email,
        company=company or None,
        message=message or None,
        status='new',
        source=source or 'marketing_form',
        details={k: v for k, v in data.items() if k not in {'name', 'email', 'company', 'message', 'notes', 'source'}},
    )

    try:
        db.session.add(lead)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        current_app.logger.error('Failed to persist lead: %s', exc)
        return jsonify({'error': 'Unable to save your request. Please try again later.'}), 500

    _mark_submission()
    _notify_ops(lead)

    return jsonify({'success': True, 'lead': lead.to_dict()}), 201


@leads_bp.route('/admin', methods=['GET'])
@admin_required
def list_leads():
    status_filter = (request.args.get('status') or '').strip().lower() or None
    export = (request.args.get('export') or '').strip().lower()

    query = Lead.query.order_by(Lead.created_at.desc())
    if status_filter:
        query = query.filter(Lead.status == status_filter)

    leads = query.all()

    if export == 'csv':
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['id', 'name', 'email', 'company', 'status', 'source', 'message', 'created_at'])
        for lead in leads:
            writer.writerow([
                lead.id,
                lead.name,
                lead.email,
                lead.company or '',
                lead.status,
                lead.source or '',
                (lead.message or '').replace('\n', ' ').strip(),
                lead.created_at.isoformat() if lead.created_at else '',
            ])
        buffer.seek(0)
        return send_file(
            io.BytesIO(buffer.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='leads.csv',
        )

    return jsonify({'count': len(leads), 'leads': [lead.to_dict() for lead in leads]})
