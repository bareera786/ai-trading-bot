from __future__ import annotations

from decimal import Decimal

import pytest
from flask import Flask

from app.config import Config
from app.extensions import db, init_extensions
from app.models import SubscriptionPlan
from app.routes.subscriptions import (
    _invalidate_public_plan_cache,
    api_public_subscription_plans,  # noqa: F401  # ensure route is registered during import
    subscription_bp,
)


class TestConfig(Config):
    TESTING = True
    SECRET_KEY = 'test-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SHOW_PUBLIC_LANDING = True


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / 'subscriptions.db'

    app = Flask(__name__)
    app.config.from_object(TestConfig)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

    init_extensions(app)
    app.register_blueprint(subscription_bp)

    with app.app_context():
        db.create_all()
        _invalidate_public_plan_cache()

        yield app.test_client()

        db.session.remove()
        db.drop_all()
        _invalidate_public_plan_cache()


def seed_plans():
    intro_trial = SubscriptionPlan(
        name='Pilot',
        code='pilot',
        plan_type='trial',
        price_usd=Decimal('0'),
        currency='USD',
        duration_days=14,
        trial_days=0,
        description='Complimentary trial',
        is_active=True,
        is_featured=False,
    )
    featured_monthly = SubscriptionPlan(
        name='Elite Automation',
        code='elite-automation',
        plan_type='monthly',
        price_usd=Decimal('249'),
        currency='USD',
        duration_days=30,
        trial_days=14,
        description='Most adopted plan',
        is_active=True,
        is_featured=True,
    )
    backup_yearly = SubscriptionPlan(
        name='Elite Yearly',
        code='elite-yearly',
        plan_type='yearly',
        price_usd=Decimal('2490'),
        currency='USD',
        duration_days=365,
        trial_days=30,
        description='Two months free',
        is_active=True,
        is_featured=False,
    )
    db.session.add_all([intro_trial, featured_monthly, backup_yearly])
    db.session.commit()


def test_public_subscription_endpoint_returns_featured_plan(client):
    with client.application.app_context():
        seed_plans()
        _invalidate_public_plan_cache()

    response = client.get('/api/subscriptions/plans')
    assert response.status_code == 200
    payload = response.get_json()

    assert payload['featured_plan']['name'] == 'Elite Automation'
    assert len(payload['plans']) == 3
    assert payload['plans'][0]['name'] == 'Pilot'
    assert payload['plans'][1]['price_usd'] == 249.0


def test_public_subscription_endpoint_caches_until_invalidated(client):
    with client.application.app_context():
        seed_plans()
        _invalidate_public_plan_cache()

    first_response = client.get('/api/subscriptions/plans').get_json()
    assert first_response['featured_plan']['price_usd'] == 249.0

    with client.application.app_context():
        plan = SubscriptionPlan.query.filter_by(code='elite-automation').first()
        plan.price_usd = Decimal('199')
        db.session.commit()
        # cache still holds old payload

    cached_response = client.get('/api/subscriptions/plans').get_json()
    assert cached_response['featured_plan']['price_usd'] == 249.0

    with client.application.app_context():
        _invalidate_public_plan_cache()

    refreshed_response = client.get('/api/subscriptions/plans').get_json()
    assert refreshed_response['featured_plan']['price_usd'] == 199.0