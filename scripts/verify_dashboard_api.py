import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

def verify_dashboard():
    with app.test_client() as client:
        with app.app_context():
            # Mock Admin User
            admin = User.query.filter_by(is_admin=True).first()
            if not admin:
                print("❌ No admin found to test dashboard access.")
                return

            print(f"DEBUG: Using Admin: {admin.email}")
            
            # Login mock via session transaction
            with client.session_transaction() as sess:
                sess['_user_id'] = admin.id
                sess['_fresh'] = True

            # 1. Test Reseller Dashboard Page
            resp = client.get('/admin/resellers')
            if resp.status_code == 200:
                print("✅ /admin/resellers loaded successfully (200 OK)")
            elif resp.status_code == 302:
                print(f"❌ /admin/resellers redirected to {resp.headers['Location']}")
            else:
                print(f"❌ /admin/resellers failed: {resp.status_code}")

            # 2. Test Reseller List API
            resp = client.get('/admin/api/resellers-list')
            if resp.status_code == 200:
                data = resp.get_json()
                if "resellers" in data:
                    print(f"✅ /admin/api/resellers-list returned {len(data['resellers'])} resellers.")
                else:
                    print("❌ API response missing 'resellers' key")
            elif resp.status_code == 302:
                print(f"❌ /admin/api/resellers-list redirected to {resp.headers['Location']}")
            else:
                print(f"❌ /admin/api/resellers-list failed: {resp.status_code}")

if __name__ == "__main__":
    verify_dashboard()
