#!/usr/bin/env python3
"""
Simple script to test user creation API manually.
"""
import os
import tempfile

import pytest

os.environ["AI_BOT_TEST_MODE"] = "true"

from app import create_app
from app.extensions import db
from app.models import User, UserPortfolio

pytestmark = pytest.mark.skip(
    reason="Legacy manual script; superseded by automated tests under tests/ directory."
)


def test_user_creation():
    # Create a temporary database for testing
    db_fd, db_path = tempfile.mkstemp()

    try:
        app = create_app()
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
        app.config["SECRET_KEY"] = "test-secret-key"

        with app.app_context():
            db.create_all()

            # Check if admin exists, if not create one
            admin_user = User.query.filter_by(username="admin").first()
            if not admin_user:
                admin_user = User(
                    username="admin", email="admin@example.com", is_admin=True
                )
                admin_user.set_password("admin123")
                db.session.add(admin_user)
                db.session.commit()
                print("Created admin user")
            else:
                print("Admin user already exists")

            # Test user creation using Flask test client
            test_data = {
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpass123",
                "is_admin": False,
            }

            with app.test_client() as client:
                # For testing, we'll temporarily disable the admin_required decorator
                # by directly calling the function logic without authentication
                print("Testing user creation API...")

                from app.routes.admin_users import api_create_user
                from flask import request
                import json

                # Create a mock request context
                with app.test_request_context(
                    "/api/users",
                    method="POST",
                    data=json.dumps(test_data),
                    content_type="application/json",
                ):
                    # Mock current_user as admin for testing
                    from flask_login import current_user

                    current_user._get_current_object = lambda: admin_user

                    try:
                        response = api_create_user()
                        print(
                            "API Response status:",
                            response[1]
                            if isinstance(response, tuple)
                            else response.status_code,
                        )
                        data = (
                            response.get_json()
                            if hasattr(response, "get_json")
                            else response[0].get_json()
                        )
                        print("Response data:", data)

                        user = User.query.filter_by(username="testuser").first()
                        if user:
                            print("✅ User created successfully!")
                            portfolio = UserPortfolio.query.filter_by(
                                user_id=user.id
                            ).first()
                            if portfolio:
                                print(
                                    f"✅ Portfolio created with balance: ${portfolio.total_balance}"
                                )
                            else:
                                print("❌ Portfolio not created")
                        else:
                            print("❌ User not created")
                    except Exception as e:
                        print(f"❌ Error during API call: {e}")

    finally:
        os.close(db_fd)
        os.unlink(db_path)


if __name__ == "__main__":
    test_user_creation()
