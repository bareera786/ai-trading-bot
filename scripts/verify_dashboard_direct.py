import sys
import os
from flask_login import login_user

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import User
from app.routes.admin_resellers import resellers_dashboard, list_all_resellers

app = create_app()

def verify_direct():
    with app.app_context():
        # Mock Admin User
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            print("❌ No admin found.")
            return

        print(f"DEBUG: Using Admin: {admin.email}")
        
        # Test 1: Dashboard View
        with app.test_request_context('/admin/resellers'):
            login_user(admin)
            try:
                # Direct call to view function
                response = resellers_dashboard()
                print("✅ resellers_dashboard() executed successfully (template rendered)")
            except Exception as e:
                print(f"❌ resellers_dashboard() failed: {e}")

        # Test 2: API
        with app.test_request_context('/admin/api/resellers-list'):
            login_user(admin)
            try:
                response = list_all_resellers()
                # If it returns a Response object (jsonify), we check it
                if response.status_code == 200:
                    print(f"✅ list_all_resellers() returned 200 OK")
                    print(f"   Data: {response.get_data(as_text=True)[:50]}...")
                else:
                    print(f"❌ list_all_resellers() returned {response.status_code}")
            except Exception as e:
                print(f"❌ list_all_resellers() failed: {e}")

if __name__ == "__main__":
    verify_direct()
