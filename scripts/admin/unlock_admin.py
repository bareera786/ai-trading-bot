#!/usr/bin/env python3
"""Unlock admin user account."""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from app import create_app
from app.models import User

def unlock_admin():
    """Unlock the admin user account."""
    app = create_app()

    with app.app_context():
        # Find admin user
        admin_user = User.query.filter_by(email="admin@example.com").first()

        if not admin_user:
            print("❌ Admin user not found!")
            return

        # Reset failed logins
        admin_user.failed_login_count = 0
        admin_user.locked_until = None

        from app.extensions import db
        db.session.commit()

        print("✅ Admin user unlocked successfully!")
        print(f"   Username: {admin_user.username}")
        print(f"   Email: {admin_user.email}")

if __name__ == "__main__":
    unlock_admin()