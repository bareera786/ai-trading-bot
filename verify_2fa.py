
import os
import sys
import pyotp
from dotenv import load_dotenv

sys.path.append(os.getcwd())
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User


def verify_2fa_flow():
    os.environ["AI_BOT_TEST_MODE"] = "true"
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        # Setup test user
        username = "2fa_test_user"
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            
        user = User(username=username, email="2fa_test@example.com")
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        
        user_id = user.id

    client = app.test_client()

    # 1. Login WITHOUT 2FA
    print("Testing Login WITHOUT 2FA...")
    resp = client.post('/auth/login', data={'username': username, 'password': 'password123'}, follow_redirects=True)
    if b'Dashboard' in resp.data or b'Sign Out' in resp.data:
        print("SUCCESS: Logged in normally.")
    else:
        print("FAIL: Login failed or unexpected redirect.")
        print(resp.data)
        return False
        
    client.get('/auth/logout')

    # 2. Enable 2FA manually in DB
    with app.app_context():
        user = User.query.get(user_id)
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.is_2fa_enabled = True
        db.session.commit()
        print(f"Enabled 2FA for user. Secret: {secret}")
        
    # 3. Login WITH 2FA
    print("Testing Login WITH 2FA...")
    resp = client.post('/auth/login', data={'username': username, 'password': 'password123'}, follow_redirects=True)
    
    # Should be redirected to /auth/2fa/verify
    if b'Two-Factor Authentication' in resp.data and b'Enter the code' in resp.data:
        print("SUCCESS: Redirected to 2FA verification page.")
    else:
        print("FAIL: Did not redirect to 2FA page.")
        if b'Dashboard' in resp.data:
            print("FAIL: Bypassed 2FA!")
        print(resp.data[:500])
        return False
        
    # 4. Verify with Code
    totp = pyotp.TOTP(secret)
    code = totp.now()
    print(f"Submitting code: {code}")
    
    resp = client.post('/auth/2fa/verify', data={'code': code}, follow_redirects=True)
    
    if b'Login successful' in resp.data or b'Dashboard' in resp.data:
        print("SUCCESS: 2FA Verification passed.")
    else:
        print("FAIL: 2FA Verification failed.")
        print(resp.data)
        return False

    # Cleanup
    with app.app_context():
        user = User.query.get(user_id)
        db.session.delete(user)
        db.session.commit()

    return True

if __name__ == "__main__":
    try:
        if verify_2fa_flow():
            print("VERIFICATION PASSED")
            sys.exit(0)
        else:
            print("VERIFICATION FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
