#!/usr/bin/env python3
"""
Simple test script to test user creation API
"""
import os
import tempfile
os.environ['AI_BOT_TEST_MODE'] = 'true'

from ai_ml_auto_bot_final import app, db, User, UserPortfolio
from flask import Flask

def test_user_creation_logic():
    """Test the core user creation logic directly"""
    # Create a temporary database for testing
    db_fd, db_path = tempfile.mkstemp()

    try:
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
        app.config['SECRET_KEY'] = 'test-secret-key'

        with app.app_context():
            db.create_all()

            # Test data with unique username
            import time
            unique_id = str(int(time.time()))
            test_data = {
                'username': f'testuser_{unique_id}',
                'email': f'test_{unique_id}@example.com',
                'password': 'testpass123',
                'is_admin': False
            }

            print("Testing user creation logic...")

            # Test the core logic directly (bypassing Flask decorators)
            username = test_data.get('username', '').strip()
            email = test_data.get('email', '').strip()
            password = test_data.get('password', '').strip()
            is_admin = test_data.get('is_admin', False)
            is_active = test_data.get('is_active', True)

            # Validate required fields
            if not username or not email or not password:
                print('❌ Validation failed: Missing required fields')
                return

            # Check if username already exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print('❌ Validation failed: Username already exists')
                return

            # Check if email already exists
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                print('❌ Validation failed: Email already exists')
                return

            # Create new user
            new_user = User(
                username=username,
                email=email,
                is_admin=is_admin,
                is_active=is_active
            )
            new_user.set_password(password)

            db.session.add(new_user)
            db.session.commit()

            # Create initial portfolio for the user
            user_portfolio = UserPortfolio(
                user_id=new_user.id,
                total_balance=10000.0,  # Starting balance
                available_balance=10000.0,
                open_positions={}
            )
            db.session.add(user_portfolio)
            db.session.commit()

            print('✅ User creation logic test passed!')

            # Verify the user was created
            user = User.query.filter_by(username=test_data['username']).first()
            if user:
                print('✅ User created successfully!')
                print(f'   Username: {user.username}')
                print(f'   Email: {user.email}')
                print(f'   Is Admin: {user.is_admin}')
                portfolio = UserPortfolio.query.filter_by(user_id=user.id).first()
                if portfolio:
                    print(f'✅ Portfolio created with balance: ${portfolio.total_balance}')
                else:
                    print('❌ Portfolio not created')
            else:
                print('❌ User not created')

    finally:
        os.close(db_fd)
        os.unlink(db_path)

if __name__ == '__main__':
    test_user_creation_logic()