import unittest
import json
import pytest
from app import create_app
from app.extensions import db
from app.models import User


class UserManagementTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True
        self.client = self.app.test_client()
        with self.app.app_context():
            db.drop_all()
            db.create_all()
            # Create admin user
            admin = User(username="admin", email="admin@example.com", is_admin=True)
            admin.set_password("adminpass")
            db.session.add(admin)
            # Create normal user
            user = User(username="user1", email="user1@example.com", is_admin=False)
            user.set_password("userpass")
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self, username, password):
        return self.client.post(
            "/login",
            data=dict(username=username, password=password),
            follow_redirects=True,
        )

    def logout(self):
        return self.client.get("/logout", follow_redirects=True)

    def test_admin_login_logout(self):
        response = self.login("admin", "adminpass")
        # Should redirect to dashboard (status code 200)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<title>", response.data)  # HTML page
        response = self.logout()
        # Should redirect to login page
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<form", response.data)

    def test_user_login_logout(self):
        response = self.login("user1", "userpass")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<title>", response.data)
        response = self.logout()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<form", response.data)

    def test_admin_add_delete_user(self):
        self.login("admin", "adminpass")
        # Add user
        response = self.client.post(
            "/api/users",
            data=json.dumps(
                {
                    "username": "newuser",
                    "email": "newuser@example.com",
                    "password": "newpass",
                    "is_admin": False,
                    "is_active": True,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["username"], "newuser")
        # Delete user
        response = self.client.delete("/api/users/newuser")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertIn("deleted successfully", data["message"])

    def test_create_user(self, client):
        response = client.post(
            "/api/admin/users",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "password123",
                "role": "viewer",
            },
        )
        assert response.status_code == 201
        assert b"User created successfully" in response.data

    def test_get_users(self, client):
        # Create a user first
        user = User(email="test@example.com", username="testuser", role="viewer")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        response = client.get("/api/admin/users")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]["email"] == "test@example.com"

    def test_promote_user(self, runner):
        # Create a user first
        user = User(email="test@example.com", username="testuser", role="viewer")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()

        result = runner.invoke(args=["users-promote", "test@example.com"])
        assert "promoted to admin" in result.output
        user = User.query.filter_by(email="test@example.com").first()
        assert user is not None
        assert user.role == "admin"


    def test_register_and_login(self):
        """Test user registration via web form and immediate login."""
        # Register a new user
        response = self.client.post(
            "/register",
            data={
                "username": "testuser",
                "email": "testuser@example.com",
                "password": "testpass123",
                "confirm_password": "testpass123",
                "captcha": "7",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        # Should redirect to login with success message
        self.assertIn(b"Registration successful", response.data)

        # Verify email for the test user
        with self.app.app_context():
            user = User.query.filter_by(username="testuser").first()
            if user:
                user.email_verified = True
                db.session.commit()

        # Now login with the same credentials
        response = self.client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("success"))
        self.assertEqual(data["user"]["username"], "testuser")


if __name__ == "__main__":
    unittest.main()
