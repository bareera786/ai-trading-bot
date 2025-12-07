#!/usr/bin/env python3
"""
Test script for futures trading toggle API
"""
import json
import sys

import pytest
import requests

pytestmark = pytest.mark.skip(reason="Manual futures toggle verification that depends on a running server.")

# Configuration
BASE_URL = "http://localhost:5000"
USERNAME = "admin"
PASSWORD = "admin123"  # Update this with the correct password

def login():
    """Login and get session cookie"""
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }

    response = requests.post(f"{BASE_URL}/login", json=login_data)
    if response.status_code == 200:
        print("✅ Login successful")
        return response.cookies
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def test_futures_toggle(cookies, enable=True):
    """Test futures trading toggle"""
    toggle_data = {"enable": enable}

    response = requests.post(
        f"{BASE_URL}/api/futures/toggle",
        json=toggle_data,
        cookies=cookies
    )

    print(f"🔄 Futures toggle (enable={enable}): {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   Response: {json.dumps(result, indent=2)}")
        return result.get('success', False)
    else:
        print(f"   Error: {response.text}")
        return False

def get_dashboard_status(cookies):
    """Get dashboard status to check futures trading state"""
    response = requests.get(f"{BASE_URL}/api/dashboard/status", cookies=cookies)

    if response.status_code == 200:
        data = response.json()
        system_status = data.get('system_status', {})
        futures_enabled = system_status.get('futures_trading_enabled', False)
        print(f"📊 Dashboard status - futures_trading_enabled: {futures_enabled}")
        return futures_enabled
    else:
        print(f"❌ Failed to get dashboard status: {response.status_code}")
        return None

def main():
    print("🧪 Testing futures trading toggle API...")

    # Login
    cookies = login()
    if not cookies:
        sys.exit(1)

    # Check initial state
    print("\n📊 Initial state:")
    initial_state = get_dashboard_status(cookies)

    # Test enabling futures trading
    print("\n🔄 Testing enable futures trading...")
    success_enable = test_futures_toggle(cookies, enable=True)
    if success_enable:
        print("✅ Futures trading enabled successfully")
    else:
        print("❌ Failed to enable futures trading")

    # Check state after enabling
    print("\n📊 State after enabling:")
    enabled_state = get_dashboard_status(cookies)

    # Test disabling futures trading
    print("\n🔄 Testing disable futures trading...")
    success_disable = test_futures_toggle(cookies, enable=False)
    if success_disable:
        print("✅ Futures trading disabled successfully")
    else:
        print("❌ Failed to disable futures trading")

    # Check state after disabling
    print("\n📊 State after disabling:")
    disabled_state = get_dashboard_status(cookies)

    # Summary
    print("\n📋 Test Summary:")
    print(f"   Initial state: {initial_state}")
    print(f"   After enable: {enabled_state}")
    print(f"   After disable: {disabled_state}")

    if enabled_state == True and disabled_state == False:
        print("✅ SUCCESS: Futures toggle persistence working correctly!")
        return True
    else:
        print("❌ FAILURE: Futures toggle persistence not working")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)