#!/usr/bin/env python3
"""Reset admin password."""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from werkzeug.security import generate_password_hash

# Hash the password
hashed = generate_password_hash("admin123")
print(f"Hashed password: {hashed}")

# Now update the database
from app import create_app
from app.models import User

app = create_app()

with app.app_context():
    admin_user = User.query.filter_by(email="admin@example.com").first()
    if admin_user:
        admin_user.set_password("admin123")
        from app.extensions import db
        db.session.commit()
        print("✅ Password reset to 'admin123'")
    else:
        print("❌ Admin user not found")