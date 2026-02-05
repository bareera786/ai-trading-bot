import os
import sys

# Add current dir to path
sys.path.append(os.getcwd())

from app import create_app
from flask import render_template
from flask_login import LoginManager, UserMixin, login_user

# Mock User
class MockUser(UserMixin):
    id = 1
    username = "test"
    role = "user"
    is_admin = False

def verify_sidebar():
    print("Initializing App...")
    # Set required env vars to avoid crashes
    os.environ['BINANCE_API_KEY'] = 'mock'
    os.environ['BINANCE_API_SECRET'] = 'mock'
    os.environ['ENCRYPTION_KEY'] = 'gAAAAABkZm...' 
    
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost' # Needed for url_for

    # Setup Login Manager (minimal)
    login_manager = LoginManager()
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return MockUser()

    with app.test_request_context('/'):
        # Log in mock user
        login_user(MockUser())
        
        print("Rendering base.html...")
        try:
            html = render_template('base.html', active_page='dashboard')
            
            checks = {
                "Marketplace": "Marketplace" in html,
                "Grid Bot": "Grid Bot" in html,
                "Connect Exchanges": "Connect Exchanges" in html
            }
            
            print("\n--- RESULTS ---")
            all_passed = True
            for feature, passed in checks.items():
                status = "✅ FOUND" if passed else "❌ MISSING"
                print(f"{feature}: {status}")
                if not passed: all_passed = False
                
            if all_passed:
                print("\nSUCCESS: All links are present in the rendered HTML.")
            else:
                print("\nFAILURE: Some links are missing.")
                
        except Exception as e:
            print(f"Render Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verify_sidebar()
