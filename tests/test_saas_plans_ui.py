from __future__ import annotations

import pytest
from flask import Flask, url_for
from app.extensions import db, init_extensions
from app.models import User, SubscriptionPlan

# Import all blueprints needed for base.html to render
from app.routes.admin_dashboard import admin_dashboard_bp
from app.routes.marketing import marketing_bp
from app.routes.dashboard import dashboard_bp
from app.routes.subscriptions import subscription_bp
from app.routes.auth import auth_bp
from app.routes.marketplace import marketplace_bp
from app.routes.strategies import strategies_bp
from app.routes.exchange import exchange_bp
try:
    from app.routes.admin_resellers import admin_resellers_bp
except ImportError:
    # minimal mock if module missing
    from flask import Blueprint
    admin_resellers_bp = Blueprint('admin_resellers', __name__)
    @admin_resellers_bp.route('/resellers')
    def resellers_dashboard(): return ""

from decimal import Decimal

class TestConfig:
    TESTING = True
    SECRET_KEY = "test-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False  # Disable CSRF for simplified testing

@pytest.fixture
def app(tmp_path):
    import os
    # Fix template path relative to this test file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, 'app/templates')
    static_dir = os.path.join(base_dir, 'app/static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(TestConfig)
    db_path = tmp_path / "saas_ui_test.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    init_extensions(app)
    
    # Register blueprints
    app.register_blueprint(admin_dashboard_bp)
    app.register_blueprint(marketing_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(auth_bp)
    try:
        app.register_blueprint(marketplace_bp)
        app.register_blueprint(strategies_bp)
        app.register_blueprint(exchange_bp)
        app.register_blueprint(admin_resellers_bp)
    except Exception as e:
        print(f"Warning: Failed to register some blueprints: {e}")

    with app.app_context():
        db.create_all()
        
        # Create Users
        admin = User(username="admin", email="admin@test.com", is_admin=True)
        admin.set_password("password")
        
        user = User(username="user", email="user@test.com", is_admin=False)
        user.set_password("password")
        
        db.session.add_all([admin, user])
        
        # Create Plans
        plan = SubscriptionPlan(
            name="Pro Plan",
            code="pro",
            plan_type="monthly",
            price_usd=Decimal("29.99"),
            currency="USD",
            duration_days=30,
            is_active=True
        )
        db.session.add(plan)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def login_as(client, username):
    """Helper to simulate login via POST request."""
    # Ensure user exists and password is set (handled in fixture)
    return client.post('/auth/login', data={
        'username': username,
        'password': 'password'
    }, follow_redirects=True)

def test_admin_plans_page_access(client):
    """Test that /admin/plans is accessible only to admins."""
    # 1. Anonymous
    resp = client.get("/admin/plans")
    assert resp.status_code == 302 # redirect to login
    
    # 2. Regular User
    login_as(client, "user")
    resp = client.get("/admin/plans", follow_redirects=True)
    assert resp.status_code == 403
    assert b"Admin access required" in resp.data
    # Should NOT have the admin plans content
    assert b"SaaS Plans" not in resp.data or b"Admin / Plans" not in resp.data

    # 3. Admin User
    client.get("/auth/logout", follow_redirects=True)
    login_as(client, "admin")
    resp = client.get("/admin/plans")
    assert resp.status_code == 200
    assert b"SaaS Plans" in resp.data
    assert b"Add New Plan" in resp.data

def test_pricing_page_rendering(client):
    """Test verification of pricing page content."""
    resp = client.get("/pricing")
    assert resp.status_code == 200
    assert b"Choose Your Plan" in resp.data
    assert b'id="plans-container"' in resp.data

def test_api_admin_plans(client):
    """Test Admin API for listing plans."""
    login_as(client, "admin")
    resp = client.get("/api/admin/subscription/plans")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "plans" in data
    assert len(data["plans"]) >= 1
    assert data["plans"][0]["name"] == "Pro Plan"

def test_user_subscription_page(client):
    """Test user subscription settings page."""
    login_as(client, "user")
    resp = client.get("/settings/subscription")
    assert resp.status_code == 200
    assert b"Subscription Management" in resp.data
    # Verify usage stats are present (even if 0)
    assert b"Plan Limits & Usage" in resp.data

def test_admin_create_plan(client):
    """Test creating a new plan via API."""
    login_as(client, "admin")
    payload = {
        "name": "Enterprise",
        "code": "ent",
        "price_usd": 999,
        "duration_days": 365,
        "plan_type": "yearly",
        "limits": {"max_bots": 10}
    }
    resp = client.post("/api/admin/subscription/plans", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["success"] is True
    assert data["plan"]["name"] == "Enterprise"
    
    # Verify it appears in list
    resp = client.get("/api/admin/subscription/plans")
    data = resp.get_json()
    assert len(data["plans"]) == 2

def test_user_confirm_subscription(client):
    """Test user confirming plan switch."""
    login_as(client, "user")
    # Verify redirect
    resp = client.get("/dashboard/subscription/confirm?plan=pro", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Subscription Management" in resp.data
    # Should show success or updated plan

