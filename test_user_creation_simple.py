#!/usr/bin/env python3
"""
Simple test script to test user creation API without running full server
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

def test_user_creation():
    """Test user creation API directly"""

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
            admin_user = User(
                username='test_admin',
                email='admin@test.com',
                is_admin=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()

            # Test user creation data
            test_data = {
                'username': 'testuser',
                'email': 'test@example.com',
                'password': 'testpass123',
                'is_admin': False
            }

            print("Testing user creation API...")
            print(f"Test data: {test_data}")

            # Simulate the API call
            from flask import request
            from ai_ml_auto_bot_final import api_create_user

            # Mock request
            with app.test_request_context('/api/users', method='POST',
                                        json=test_data,
                                        headers={'Content-Type': 'application/json'}):
                # Mock login
                from flask_login import login_user
                login_user(admin_user)

                try:
                    response = api_create_user()
                    print(f"API Response: {response}")
                    print(f"Response data: {response.get_json() if hasattr(response, 'get_json') else 'No JSON data'}")

                    # Check if user was created
                    user = User.query.filter_by(username='testuser').first()
                    if user:
                        print("✅ User created successfully!")
                        print(f"User details: {user.username}, {user.email}, admin: {user.is_admin}")

                        # Check portfolio
                        portfolio = UserPortfolio.query.filter_by(user_id=user.id).first()
                        if portfolio:
                            print(f"✅ Portfolio created with balance: ${portfolio.total_balance}")
                        else:
                            print("❌ Portfolio not created")
                    else:
                        print("❌ User not created")

                except Exception as e:
                    print(f"❌ Error during user creation: {e}")
                    import traceback
                    traceback.print_exc()

    finally:
        # Clean up
        os.close(db_fd)
        os.unlink(db_path)

if __name__ == '__main__':
    test_user_creation()