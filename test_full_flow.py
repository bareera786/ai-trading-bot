#!/usr/bin/env python3
"""
Test the full user creation flow with authentication
"""
import sys
import os
sys.path.insert(0, '.')

# Set test mode to avoid full initialization
os.environ['AI_BOT_TEST_MODE'] = 'true'

from ai_ml_auto_bot_final import app, db, User, UserPortfolio
from flask import Flask
import tempfile
import sqlite3

def test_full_user_creation_flow():
    """Test the complete user creation flow with authentication"""

    # Create a temporary database for testing
    db_fd, db_path = tempfile.mkstemp()

    try:
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SECRET_KEY'] = 'test-secret-key'

        with app.app_context():
            # Create tables
            db.create_all()

            # Create admin user for testing
            import random
            admin_username = f'test_admin_{random.randint(1000, 9999)}'
            admin_user = User(
                username=admin_username,
                email=f'{admin_username}@test.com',
                is_admin=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()

            print("=== Testing Authentication ===")

            # Test login
            with app.test_client() as client:
                # Login as admin
                login_response = client.post('/login', json={
                    'username': admin_username,
                    'password': 'admin123'
                })
                print(f"Login response status: {login_response.status_code}")
                print(f"Login response data: {login_response.get_json()}")

                if login_response.status_code == 200:
                    print("✅ Login successful")

                    # Now test user creation with authenticated session
                    print("\n=== Testing User Creation ===")

                    user_creation_response = client.post('/api/users', json={
                        'username': 'newtestuser',
                        'email': 'newtest@example.com',
                        'password': 'testpass123',
                        'is_admin': False
                    })
                    print(f"User creation response status: {user_creation_response.status_code}")
                    print(f"User creation response data: {user_creation_response.get_json()}")

                    if user_creation_response.status_code == 201:
                        print("✅ User creation successful")

                        # Check if user was actually created
                        user = User.query.filter_by(username='newtestuser').first()
                        if user:
                            print("✅ User found in database")
                            print(f"User details: {user.username}, {user.email}, admin: {user.is_admin}")

                            # Check portfolio
                            portfolio = UserPortfolio.query.filter_by(user_id=user.id).first()
                            if portfolio:
                                print(f"✅ Portfolio created with balance: ${portfolio.total_balance}")
                            else:
                                print("❌ Portfolio not created")
                        else:
                            print("❌ User not found in database")
                    else:
                        print("❌ User creation failed")
                        print(f"Error: {user_creation_response.get_json()}")

                else:
                    print("❌ Login failed")
                    print(f"Error: {login_response.get_json()}")

    finally:
        # Clean up
        os.close(db_fd)
        os.unlink(db_path)

if __name__ == '__main__':
    test_full_user_creation_flow()