
import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())

load_dotenv()

from app import create_app
from app.extensions import db
from app.models import User, ExchangeCredential
from app.security.credential_manager import CredentialManager

def verify_encryption():
    app = create_app()
    with app.app_context():
        # Setup test user
        user = User.query.filter_by(username="test_verification_user").first()
        if not user:
            user = User(username="test_verification_user", email="test@verify.com")
            user.set_password("pass")
            db.session.add(user)
            db.session.commit()
            print("Created test user")
        else:
            print("Using existing test user")
            
        test_key = "my_secret_api_key_123"
        test_secret = "my_secret_api_secret_456"
        
        # 1. Simulate saving (using CredentialManager manually as per the route logic)
        cred_manager = CredentialManager()
        enc_key, enc_secret = cred_manager.encrypt_credentials(test_key, test_secret)
        
        # Determine if it's already there to update or create
        cred = ExchangeCredential.query.filter_by(user_id=user.id, exchange_id='binance').first()
        if cred:
            cred.api_key_enc = enc_key
            cred.api_secret_enc = enc_secret
        else:
            cred = ExchangeCredential(
                user_id=user.id,
                exchange_id='binance',
                api_key_enc=enc_key,
                api_secret_enc=enc_secret
            )
            db.session.add(cred)
        db.session.commit()
        
        print("Saved credentials to DB.")
        
        # 2. Verify Storage
        stored_cred = ExchangeCredential.query.filter_by(user_id=user.id, exchange_id='binance').first()
        
        if stored_cred.api_key_enc == test_key.encode('utf-8'):
            print("FAIL: Key stored as PLAINTEXT bytes!")
            return False
        
        if stored_cred.api_key_enc == enc_key:
            print("SUCCESS: Key stored as ENCRYPTED bytes.")
        else:
            print("FAIL: Key mismatch?")
            return False
            
        # 3. Verify Decryption
        dec_key, dec_secret = cred_manager.get_decrypted(stored_cred.api_key_enc, stored_cred.api_secret_enc)
        
        if dec_key == test_key and dec_secret == test_secret:
            print("SUCCESS: Decryption retrieved original keys.")
        else:
            print(f"FAIL: Decryption failed. Got {dec_key}, expected {test_key}")
            return False
            
        # Cleanup
        db.session.delete(stored_cred)
        # db.session.delete(user) # Keep user for other tests if needed? nah delete it
        db.session.delete(user)
        db.session.commit()
        print("Cleanup done.")
        
        return True

if __name__ == "__main__":
    if verify_encryption():
        print("VERIFICATION PASSED")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED")
        sys.exit(1)
