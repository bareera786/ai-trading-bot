#!/usr/bin/env python3
import requests
import json
import time

def test_user_creation():
    """Test the user creation API with authentication"""
    base_url = "http://localhost:5000"

    # Create a session to maintain cookies
    session = requests.Session()

    # First, login as admin
    login_url = f"{base_url}/login"
    login_data = {
        "username": "admin",
        "password": "admin123"
    }

    try:
        print("Logging in as admin...")
        login_response = session.post(login_url, json=login_data, headers={'Content-Type': 'application/json'})

        print(f"Login Status Code: {login_response.status_code}")
        print(f"Login Response: {login_response.text}")

        if login_response.status_code != 200:
            print("❌ Login failed!")
            return False

        login_result = login_response.json()
        if not login_result.get('success'):
            print("❌ Login not successful!")
            return False

        print("✅ Login successful!")

        # Now test user creation
        url = f"{base_url}/api/users"
        test_data = {
            "username": "testuser123",
            "email": "test@example.com",
            "password": "password123",
            "is_admin": True
        }

        print("\nTesting user creation API...")
        print(f"URL: {url}")
        print(f"Data: {json.dumps(test_data, indent=2)}")

        response = session.post(url, json=test_data, headers={'Content-Type': 'application/json'})

        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 201:
            result = response.json()
            if result.get('success'):
                print("✅ User creation successful!")
                return True
            else:
                print("❌ User creation failed - API returned success=false")
                return False
        else:
            print("❌ User creation failed!")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - server not running")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    # Wait a bit for server to start
    print("Waiting for server to start...")
    time.sleep(5)

    success = test_user_creation()
    exit(0 if success else 1)