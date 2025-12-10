import os
import tempfile

import pytest
from unittest.mock import patch

os.environ["AI_BOT_TEST_MODE"] = "true"

from app import create_app
from app.extensions import db
from app.models import User


@pytest.fixture
def app():
    """Create and configure a test app instance."""
    db_fd, db_path = tempfile.mkstemp()
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SECRET_KEY"] = "test-secret-key"

    with app.app_context():
        db.create_all()

        # Create admin user if not exists
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(
                username="admin", email="admin@example.com", is_admin=True
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            db.session.commit()

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_toggle_trading(client):
    """Test toggling trading on and off."""
    with client.application.app_context():
        # First, authenticate
        auth_response = client.post(
            "/login", json={"username": "admin", "password": "admin123"}
        )
        assert auth_response.status_code == 200

        # Mock the context for the toggle
        mock_ctx = {
            "ultimate_trader": type('MockTrader', (), {'trading_enabled': False})(),
            "optimized_trader": None,
            "dashboard_data": {}
        }
        with patch('app.routes.system_ops._ctx', return_value=mock_ctx):
            # Toggle trading on
            toggle_response = client.post("/api/toggle_trading")
            assert toggle_response.status_code == 200
            toggle_json = toggle_response.get_json()
            assert "message" in toggle_json

            # Toggle trading off
            toggle_response2 = client.post("/api/toggle_trading")
            assert toggle_response2.status_code == 200
            toggle_json2 = toggle_response2.get_json()
            assert "message" in toggle_json2
