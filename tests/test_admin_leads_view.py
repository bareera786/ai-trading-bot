from __future__ import annotations

import pytest
from flask import Flask
from pathlib import Path

from app.config import Config
from app.extensions import db, init_extensions
from app.models import Lead, User
from app.routes.admin_views import admin_views_bp
from app.routes.leads import leads_bp
from app.routes.dashboard import dashboard_bp


BASE_DIR = Path(__file__).resolve().parents[1]


class AdminViewTestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///"


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "admin-leads.db"
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "app" / "templates"),
        static_folder=str(BASE_DIR / "app" / "static"),
    )
    app.config.from_object(AdminViewTestConfig)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    init_extensions(app)
    app.register_blueprint(admin_views_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(dashboard_bp)

    with app.app_context():
        db.create_all()

    yield app.test_client()

    with app.app_context():
        db.drop_all()


def login_admin(app: Flask, client) -> int:
    with app.app_context():
        admin = User(username="admin", email="admin@example.com", is_admin=True)
        admin.set_password("secret123")
        db.session.add(admin)
        db.session.add(
            Lead(name="Alice", email="alice@example.com", status="contacted")
        )
        db.session.commit()
        admin_id = admin.id

    with client.session_transaction() as session:
        session["_user_id"] = str(admin_id)
        session["_fresh"] = True

    return admin_id


def test_admin_leads_requires_auth(client):
    response = client.get("/admin/leads")
    assert response.status_code == 401


def test_admin_leads_renders_table(client):
    app = client.application
    login_admin(app, client)

    response = client.get("/admin/leads")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Lead Inbox" in html
    assert "alice@example.com" in html
    assert "Download CSV" in html
