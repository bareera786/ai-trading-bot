
import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from app.extensions import db
from app.models import User

def reset_password():
    app = create_app()
    with app.app_context():
        # Find admin user
        admin = User.query.filter_by(email="admin@local").first()
        if not admin:
            # Create if missing
            print("Admin user not found. Creating new admin...")
            admin = User()
            admin.email = "admin@local"
            admin.username = "admin"
            admin.is_admin = True
            admin.is_active = True
            db.session.add(admin)
        
        # Force password reset
        print("Resetting admin password to 'admin123'...")
        admin.set_password("admin123")
        db.session.commit()
        print("✅ Password reset successful.")

if __name__ == "__main__":
    reset_password()
