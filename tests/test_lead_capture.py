from __future__ import annotations

import pytest
from flask import Flask

from app.config import Config
from app.extensions import db, init_extensions
from app.models import Lead, User
from app.routes import leads as leads_module
from app.routes.leads import leads_bp


class LeadTestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    LEAD_RATE_LIMIT_SECONDS = 60


@pytest.fixture(autouse=True)
def reset_rate_limit_tracker():
    leads_module._rate_limit_tracker.clear()
    yield
    leads_module._rate_limit_tracker.clear()


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / 'leads.db'
    app = Flask(__name__)
    app.config.from_object(LeadTestConfig)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    init_extensions(app)
    app.register_blueprint(leads_bp)

    with app.app_context():
        db.create_all()

    yield app.test_client()

    with app.app_context():
        db.drop_all()


def login_admin(app: Flask, client) -> int:
    with app.app_context():
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('secret123')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as session:
        session['_user_id'] = str(admin_id)
        session['_fresh'] = True

    return admin_id


def test_lead_capture_success(client):
    response = client.post('/api/leads', json={
        'name': 'Jane Doe',
        'email': 'jane@example.com',
        'company': 'AI Fund',
        'message': 'Need futures automation',
    })

    assert response.status_code == 201
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['lead']['email'] == 'jane@example.com'

    with client.application.app_context():
        lead = Lead.query.filter_by(email='jane@example.com').first()
        assert lead is not None
        assert lead.company == 'AI Fund'


def test_lead_capture_rate_limit(client):
    for _ in range(2):
        response = client.post('/api/leads', json={'name': 'A', 'email': 'a@example.com'})
    assert response.status_code == 429
    payload = response.get_json()
    assert 'retry_after_seconds' in payload


def test_admin_list_requires_auth(client):
    response = client.get('/api/leads/admin')
    assert response.status_code == 401


def test_admin_list_returns_leads(client):
    app = client.application
    with app.app_context():
        db.session.add(Lead(name='L1', email='l1@example.com'))
        db.session.add(Lead(name='L2', email='l2@example.com', status='contacted'))
        db.session.commit()

    login_admin(app, client)

    response = client.get('/api/leads/admin')
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['count'] == 2
    assert {lead['email'] for lead in payload['leads']} == {'l1@example.com', 'l2@example.com'}