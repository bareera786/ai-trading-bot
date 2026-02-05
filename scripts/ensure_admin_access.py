import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

def ensure_admin():
    with app.app_context():
        print("🔍 Checking user roles for Admin Access...")
        users = User.query.all()
        if not users:
            print("⚠️ No users found in database.")
            return

        admin_exists = any(u.is_admin for u in users)
        
        if admin_exists:
            print(f"✅ Found {sum(1 for u in users if u.is_admin)} admin(s).")
            for u in users:
                if u.is_admin:
                    print(f"   - Admin: {u.username} ({u.email})")
        else:
            print("⚠️ No admins found! Promoting the first user to Admin...")
            # Heuristic: Promote 'admin' if exists, otherwise first user
            target = next((u for u in users if u.username == 'admin'), users[0])
            
            target.is_admin = True
            target.is_active = True
            db.session.commit()
            print(f"🚀 PROMOTED {target.username} ({target.email}) to ADMIN.")

if __name__ == "__main__":
    try:
        ensure_admin()
    except Exception as e:
        print(f"❌ Error ensuring admin: {e}")
        sys.exit(1)
