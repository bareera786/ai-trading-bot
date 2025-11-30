#!/usr/bin/env python3
import requests
import json
import time

# Test script to check paper trading enablement
BASE_URL = "http://151.243.171.80:5000"

def login():
    """Login and get session"""
    session = requests.Session()

    # Login
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }

    response = session.post(f"{BASE_URL}/login", data=login_data)
    print(f"Login response: {response.status_code}")

    if response.status_code != 200:
        print("Login failed!")
        return None

    return session

def test_paper_trading():
    """Test paper trading enablement"""
    session = login()
    if not session:
        return

    print("\n=== Testing Paper Trading Enablement ===")

    # Check initial dashboard status
    print("1. Checking initial dashboard status...")
    response = session.get(f"{BASE_URL}/api/dashboard")
    if response.status_code == 200:
        data = response.json()
        initial_trading_enabled = data.get('system_status', {}).get('trading_enabled', False)
        print(f"   Initial trading_enabled: {initial_trading_enabled}")
    else:
        print(f"   Failed to get dashboard: {response.status_code}")
        return

    # Enable paper trading
    print("2. Enabling paper trading...")
    response = session.post(f"{BASE_URL}/api/enable_paper_trading")
    if response.status_code == 200:
        data = response.json()
        print(f"   Enable response: {data}")
    else:
        print(f"   Failed to enable paper trading: {response.status_code}")
        print(f"   Response: {response.text}")
        return

    # Wait a moment
    time.sleep(2)

    # Check dashboard status after enablement
    print("3. Checking dashboard status after enablement...")
    response = session.get(f"{BASE_URL}/api/dashboard")
    if response.status_code == 200:
        data = response.json()
        final_trading_enabled = data.get('system_status', {}).get('trading_enabled', False)
        print(f"   Final trading_enabled: {final_trading_enabled}")

        if final_trading_enabled:
            print("✅ SUCCESS: Paper trading is now enabled!")
        else:
            print("❌ FAILURE: Paper trading is still disabled!")
            print(f"   Full system_status: {data.get('system_status', {})}")
    else:
        print(f"   Failed to get dashboard: {response.status_code}")

if __name__ == "__main__":
    test_paper_trading()