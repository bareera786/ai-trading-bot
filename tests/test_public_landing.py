from __future__ import annotations

import pytest
from flask import Flask
from pathlib import Path

from app.config import Config
from app.extensions import init_extensions
from app.routes.auth import auth_bp
from app.routes.marketing import marketing_bp
from app.routes.subscriptions import subscription_bp
from app.routes.leads import leads_bp
from app.assets import register_asset_helpers

BASE_DIR = Path(__file__).resolve().parents[1]


class PublicLandingTestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///"
    SHOW_PUBLIC_LANDING = True


@pytest.fixture()
def client():
    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "app" / "templates"),
        static_folder=str(BASE_DIR / "app" / "static"),
    )
    app.config.from_object(PublicLandingTestConfig)

    init_extensions(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(subscription_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(marketing_bp)
    register_asset_helpers(app)

    @app.route("/dashboard")
    def dashboard():  # pragma: no cover - stub for redirect target
        return "dashboard"

    with app.test_client() as test_client:
        yield test_client


def test_marketing_page_loads(client):
    response = client.get("/marketing")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    lower_html = html.lower()
    assert "ai trading pro" in lower_html
    assert "start free trial" in lower_html


def test_root_redirects_to_marketing(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 301)
    assert "/marketing" in response.headers["Location"]


def test_marketing_includes_analytics_snippet_when_enabled(client):
    app = client.application
    app.config["ENABLE_MARKETING_ANALYTICS"] = True
    app.config["MARKETING_ANALYTICS_SRC"] = "https://analytics.example/js/script.js"
    app.config["MARKETING_ANALYTICS_DOMAIN"] = "ai-bot.local"

    response = client.get("/marketing")
    html = response.get_data(as_text=True)

    assert "analytics.example/js/script.js" in html
    assert 'data-domain="ai-bot.local"' in html
