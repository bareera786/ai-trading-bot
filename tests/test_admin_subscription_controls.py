from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from flask import Flask

from app.extensions import db, init_extensions
from app.models import SubscriptionPlan, User
from app.routes.admin_user_api import admin_user_api_bp


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "admin_subscriptions.db"

    app = Flask(__name__)
    app.config.from_object(TestConfig)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

    init_extensions(app)
    app.register_blueprint(admin_user_api_bp)

    with app.app_context():
        db.create_all()

        admin = User()
        admin.username = "admin"
        admin.email = "admin@test"
        admin.is_admin = True
        admin.set_password("pass")
        user = User()
        user.username = "user"
        user.email = "user@test"
        user.is_admin = False
        user.set_password("pass")

        plan = SubscriptionPlan(
            name="Pro Monthly",
            code="pro-monthly",
            plan_type="monthly",
            price_usd=Decimal("149"),
            currency="USD",
            duration_days=30,
            trial_days=0,
            description="",
            is_active=True,
            is_featured=False,
        )

        db.session.add_all([admin, user, plan])
        db.session.commit()

        yield app.test_client()

        db.session.remove()
        db.drop_all()


def _login_as(client, user_id: int):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)
        sess["_fresh"] = True


def test_admin_can_grant_and_extend_subscription(client):
    with client.application.app_context():
        admin = User.query.filter_by(username="admin").first()
        user = User.query.filter_by(username="user").first()
        assert admin and user

    _login_as(client, admin.id)

    grant = client.post(
        f"/api/users/{user.id}/subscription/grant",
        json={"plan_code": "pro-monthly", "days": 10, "notes": "free access"},
    )
    assert grant.status_code == 200
    payload = grant.get_json()
    assert payload["success"] is True

    # admin_user_api should expose subscription_expiry via current_period_end
    user_json = client.get(f"/api/users/{user.id}").get_json()
    assert user_json["subscription_expiry"]

    extend = client.post(
        f"/api/users/{user.id}/subscription/extend",
        json={"days": 5, "notes": "extend cycle"},
    )
    assert extend.status_code == 200

    with client.application.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed is not None
        assert refreshed.active_subscription
        end = refreshed.active_subscription.current_period_end
        assert end is not None
        assert end > datetime.utcnow() + timedelta(days=10)


def test_non_admin_cannot_grant_or_extend(client):
    with client.application.app_context():
        user = User.query.filter_by(username="user").first()
        assert user

    _login_as(client, user.id)

    resp = client.post(f"/api/users/{user.id}/subscription/grant", json={})
    assert resp.status_code == 403

    resp = client.post(f"/api/users/{user.id}/subscription/extend", json={"days": 1})
    assert resp.status_code == 403


def test_admin_can_update_subscription_expiry_via_edit_user(client):
    with client.application.app_context():
        admin = User.query.filter_by(username="admin").first()
        user = User.query.filter_by(username="user").first()
        assert admin and user

    _login_as(client, admin.id)

    # Create a subscription first
    grant = client.post(
        f"/api/users/{user.id}/subscription/grant",
        json={"plan_code": "pro-monthly", "days": 3},
    )
    assert grant.status_code == 200

    new_end = (datetime.utcnow() + timedelta(days=99)).replace(microsecond=0)
    put = client.put(
        f"/api/users/{user.id}",
        json={"subscription_expiry": new_end.isoformat()},
    )
    assert put.status_code == 200

    with client.application.app_context():
        refreshed = db.session.get(User, user.id)
        assert refreshed is not None
        assert refreshed.active_subscription
        assert refreshed.active_subscription.current_period_end.replace(microsecond=0) == new_end
