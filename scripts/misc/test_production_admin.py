#!/usr/bin/env python3
"""Test script to verify admin user exists in production database."""

import os

from app import create_app
from app.extensions import db
from app.models import User

# Set production database
os.environ['DATABASE_URL'] = 'sqlite:///trading_bot.db'
os.environ.pop('AI_BOT_TEST_MODE', None)

app = create_app()


def test_production_admin():
    with app.app_context():
        print(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
        print(f"Database file exists: {os.path.exists('trading_bot.db')}")

        # Check all users
        users = User.query.all()
        print(f"Found {len(users)} users in database:")
        for user in users:
            print(f"  - {user.username} ({user.email}) - admin: {user.is_admin}")

        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("❌ Admin user not found")
            return False

        print(f"✅ Admin user found: {admin.username} ({admin.email})")
        print(f"   - is_admin: {admin.is_admin}")
        print(f"   - is_active: {admin.is_active}")

        # Test password verification
        if admin.check_password('admin123'):
            print("✅ Admin password verification successful")
        else:
            print("❌ Admin password verification failed")
            return False

        # Test login
        from flask_login import login_user
        login_user(admin)
        print("✅ Admin login successful")

        return True


if __name__ == "__main__":
    success = test_production_admin()
    if success:
        print("\n🎉 Production admin authentication test passed!")
    else:
        print("\n❌ Production admin authentication test failed!")
        exit(1)