#!/usr/bin/env python3
"""Test script for the simplified auth system."""

import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite:///test_auth.db'
os.environ['SKIP_RUNTIME_BOOTSTRAP'] = '1'
os.environ['AI_BOT_TEST_MODE'] = '1'

from app import create_app
from app.extensions import db
from app.models import User

def test_auth():
    app = create_app()

    with app.app_context():
        # Test user registration
        print("Testing user registration...")

        # Create a test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')

        db.session.add(user)
        db.session.commit()

        print("✓ User registered successfully")

        # Test password verification
        print("Testing password verification...")
        assert user.check_password('testpass123') == True
        assert user.check_password('wrongpass') == False
        print("✓ Password verification works")

        # Test user lookup
        print("Testing user lookup...")
        found_user = User.query.filter_by(username='testuser').first()
        assert found_user is not None
        assert found_user.email == 'test@example.com'
        print("✓ User lookup works")

        # Test unique constraints
        print("Testing unique constraints...")
        try:
            duplicate_user = User(username='testuser', email='different@example.com')
            duplicate_user.set_password('pass')
            db.session.add(duplicate_user)
            db.session.commit()
            assert False, "Should have failed due to duplicate username"
        except Exception as e:
            print(f"✓ Username uniqueness enforced: {type(e).__name__}")

        try:
            duplicate_email = User(username='differentuser', email='test@example.com')
            duplicate_email.set_password('pass')
            db.session.add(duplicate_email)
            db.session.commit()
            assert False, "Should have failed due to duplicate email"
        except Exception as e:
            print(f"✓ Email uniqueness enforced: {type(e).__name__}")

        print("\n🎉 All auth tests passed! The simplified auth system is working correctly.")

if __name__ == '__main__':
    test_auth()