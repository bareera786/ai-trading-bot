
import sys
import os
sys.path.append(os.getcwd())

from app import create_app
from app.models import User

def verify_login():
    app = create_app()
    with app.app_context():
        username = "admin"
        password = "admin123"
        
        print(f"🔍 Testing login for username: '{username}'")
        
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print("❌ User not found!")
            return
            
        print(f"✅ User found. ID: {user.id}, Role: {getattr(user, 'role', 'N/A')}, Active: {user.is_active}")
        
        if user.check_password(password):
            print("✅ Password valid! Login should work.")
        else:
            print("❌ Password invalid! Hash mismatch.")
            # Debug hash
            print(f"   Stored hash: {user.password_hash}")

if __name__ == "__main__":
    verify_login()
