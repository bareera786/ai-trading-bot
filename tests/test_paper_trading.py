#!/usr/bin/env python3
import requests
import json

# Test enable_paper_trading endpoint
def test_enable_paper_trading():
    base_url = "http://localhost:5000"

    # First, authenticate as admin
    auth_url = f"{base_url}/login"
    auth_data = {
        "username": "admin",
        "password": "admin123"
    }

    print("Authenticating as admin...")
    auth_response = requests.post(auth_url, json=auth_data)

    if auth_response.status_code != 200:
        print(f"Auth failed: {auth_response.status_code} - {auth_response.text}")
        return

    # Get session cookie
    cookies = auth_response.cookies

    print("Login successful!")

    # Check dashboard before enabling paper trading
    dashboard_url = f"{base_url}/api/dashboard"
    print("Checking dashboard before enabling paper trading...")
    dashboard_response = requests.get(dashboard_url, cookies=cookies)

    if dashboard_response.status_code == 200:
        dashboard_data = dashboard_response.json()
        system_status = dashboard_data.get('system_status', {})
        print(f"Before - trading_enabled: {system_status.get('trading_enabled')}")
        print(f"Before - paper_trading: {system_status.get('paper_trading')}")
    else:
        print(f"Dashboard check failed: {dashboard_response.status_code}")

    # Enable paper trading
    enable_url = f"{base_url}/api/enable_paper_trading"
    enable_data = {"enable": True}

    print("Enabling paper trading...")
    enable_response = requests.post(enable_url, json=enable_data, cookies=cookies)

    print(f"Enable response: {enable_response.status_code}")
    print(f"Enable response body: {enable_response.text}")

    if enable_response.status_code == 200:
        enable_result = enable_response.json()
        print(f"Enable result: {enable_result}")

        # Check dashboard after enabling paper trading
        print("Checking dashboard after enabling paper trading...")
        dashboard_response2 = requests.get(dashboard_url, cookies=cookies)

        if dashboard_response2.status_code == 200:
            dashboard_data2 = dashboard_response2.json()
            system_status2 = dashboard_data2.get('system_status', {})
            print(f"After - trading_enabled: {system_status2.get('trading_enabled')}")
            print(f"After - paper_trading: {system_status2.get('paper_trading')}")

            # Check if the change persisted
            if system_status2.get('trading_enabled') and system_status2.get('paper_trading'):
                print("✅ SUCCESS: Paper trading enabled and dashboard reflects the change!")
            else:
                print("❌ FAILURE: Dashboard does not reflect the paper trading enablement")
        else:
            print(f"Dashboard check after failed: {dashboard_response2.status_code}")
    else:
        print(f"Enable paper trading failed: {enable_response.status_code}")

if __name__ == "__main__":
    test_enable_paper_trading()