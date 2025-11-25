#!/usr/bin/env python3
"""
Test script for user creation API with authentication
"""

import requests
import json
import sys

# Flask app URL (adjust if running on different port)
BASE_URL = "http://localhost:5000"

def login_admin():
    """Login as admin user and return session"""
    login_url = f"{BASE_URL}/login"
    login_data = {
        "username": "admin",
        "password": "admin123"
    }

    print("🔐 Logging in as admin...")
    response = requests.post(login_url, json=login_data)

    if response.status_code == 200:
        data = response.json()
        if data.get('success'):
            print("✅ Admin login successful")
            # Get session cookie
            session_cookie = response.cookies.get('session')
            if session_cookie:
                return session_cookie
            else:
                print("❌ No session cookie received")
                return None
        else:
            print(f"❌ Login failed: {data.get('error', 'Unknown error')}")
            return None
    else:
        print(f"❌ Login request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        return None

def test_user_creation(session_cookie):
    """Test user creation with admin authentication"""
    user_creation_url = f"{BASE_URL}/api/users"

    # Test data for new user
    test_user_data = {
        "username": "testuser123",
        "email": "testuser123@example.com",
        "password": "testpass123",
        "is_admin": False,
        "is_active": True
    }

    print("👤 Creating test user...")
    print(f"Data: {json.dumps(test_user_data, indent=2)}")

    # Set up cookies for authentication
    cookies = {'session': session_cookie}

    response = requests.post(user_creation_url, json=test_user_data, cookies=cookies)

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

    if response.status_code == 201:
        data = response.json()
        if data.get('success'):
            print("✅ User creation successful!")
            print(f"Created user: {data.get('user', {})}")
            return True
        else:
            print(f"❌ User creation failed: {data.get('error', 'Unknown error')}")
            return False
    else:
        print(f"❌ User creation request failed with status {response.status_code}")
        try:
            error_data = response.json()
            print(f"Error details: {error_data}")
        except:
            print(f"Raw response: {response.text}")
        return False

def main():
    print("🧪 Testing User Creation API with Authentication")
    print("=" * 50)

    # Step 1: Login as admin
    session_cookie = login_admin()
    if not session_cookie:
        print("❌ Cannot proceed without admin authentication")
        sys.exit(1)

    print()

    # Step 2: Test user creation
    success = test_user_creation(session_cookie)

    print()
    print("=" * 50)
    if success:
        print("🎉 All tests passed!")
    else:
        print("❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()