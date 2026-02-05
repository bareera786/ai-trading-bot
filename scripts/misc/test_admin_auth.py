#!/usr/bin/env python3
"""Test authentication with admin user."""

import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite:///test_auth.db'
os.environ['SKIP_RUNTIME_BOOTSTRAP'] = '1'
os.environ['AI_BOT_TEST_MODE'] = '1'

from app import create_app
from app.extensions import db
from app.models import User

def test_admin_auth():
    app = create_app()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_auth.db'

    print(f"Database URL: {app.config.get('SQLALCHEMY_DATABASE_URI')}")
    print(f"Database file exists: {os.path.exists('test_auth.db')}")

    with app.app_context():
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

if __name__ == '__main__':
    success = test_admin_auth()
    if success:
        print("\n🎉 Admin authentication test passed!")
    else:
        print("\n❌ Admin authentication test failed!")
        sys.exit(1)