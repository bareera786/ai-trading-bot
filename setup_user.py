import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())

load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User

def setup_admin():
    app = create_app()
    with app.app_context():
        # Check if admin exists
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            print("Creating admin user...")
            admin = User(username="admin", email="admin@example.com")
            admin.set_password("admin123")
            admin.is_admin = True
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin / admin123")
        else:
            print("Admin user exists. Resetting password...")
            admin.set_password("admin123")
            admin.is_admin = True
            db.session.commit()
            print("Admin user updated: admin / admin123")

if __name__ == "__main__":
    setup_admin()
