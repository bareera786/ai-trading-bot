#!/usr/bin/env python3
"""
Test script for admin and user management fixes
"""

import requests
import time
import sys

def test_admin_user_management():
    base_url = "http://localhost:5000"
    
    print("🧪 TESTING ADMIN & USER MANAGEMENT FIXES")
    print("=" * 50)
    
    # Wait for app to start
    print("⏳ Waiting for app to start...")
    time.sleep(3)
    
    try:
        # Test 1: Login as admin
        print("\n1. Testing admin login...")
        login_data = {"username": "admin", "password": "admin123"}
        response = requests.post(f"{base_url}/login", json=login_data)
        
        if response.status_code != 200:
            print(f"   ❌ Login failed: {response.status_code} - {response.text}")
            return False
        
        print("   ✅ Admin login successful")
        session_cookies = response.cookies
        
        # Test 2: List users (admin function)
        print("\n2. Testing user list...")
        response = requests.get(f"{base_url}/api/users", cookies=session_cookies)
        
        if response.status_code == 200:
            users_data = response.json()
            print(f"   ✅ User list: {len(users_data.get('users', []))} users")
        elif response.status_code == 403:
            print("   ❌ User list: Admin access denied (admin_required not working)")
            return False
        else:
            print(f"   ❌ User list failed: {response.status_code} - {response.text}")
            return False
        
        # Test 3: Create new user
        print("\n3. Testing user creation...")
        test_username = f"testuser_{int(time.time())}"
        user_data = {
            "username": test_username,
            "password": "test123",
            "is_admin": False
        }
        
        response = requests.post(f"{base_url}/api/users", json=user_data, cookies=session_cookies)
        
        if response.status_code == 201:
            print(f"   ✅ User creation: {test_username} created successfully")
        else:
            print(f"   ❌ User creation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 4: Delete user
        print("\n4. Testing user deletion...")
        response = requests.delete(f"{base_url}/api/users/{test_username}", cookies=session_cookies)
        
        if response.status_code == 200:
            print(f"   ✅ User deletion: {test_username} deleted successfully")
        else:
            print(f"   ❌ User deletion failed: {response.status_code} - {response.text}")
            return False
        
        print("\n🎉 ALL ADMIN & USER MANAGEMENT TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("💡 Make sure the Flask app is running: python3 ai_ml_auto_bot_final.py")
        return False

if __name__ == "__main__":
    if test_admin_user_management():
        sys.exit(0)
    else:
        sys.exit(1)
