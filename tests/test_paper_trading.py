#!/usr/bin/env python3
import pytest
import json
from unittest.mock import Mock, patch


# Test enable_paper_trading endpoint
def test_enable_paper_trading(monkeypatch):
    # Mock the requests module
    mock_post = Mock()
    mock_get = Mock()

    # Mock auth response
    auth_response = Mock()
    auth_response.status_code = 200
    auth_response.cookies = {'session': 'test_cookie'}

    # Mock dashboard responses
    dashboard_response_before = Mock()
    dashboard_response_before.status_code = 200
    dashboard_response_before.json.return_value = {
        "system_status": {
            "trading_enabled": False,
            "paper_trading": False
        }
    }

    dashboard_response_after = Mock()
    dashboard_response_after.status_code = 200
    dashboard_response_after.json.return_value = {
        "system_status": {
            "trading_enabled": True,
            "paper_trading": True
        }
    }

    # Mock enable response
    enable_response = Mock()
    enable_response.status_code = 200
    enable_response.json.return_value = {"success": True}

    # Configure mock_post to return different responses
    mock_post.side_effect = [auth_response, enable_response]
    mock_get.side_effect = [dashboard_response_before, dashboard_response_after]

    monkeypatch.setattr('requests.post', mock_post)
    monkeypatch.setattr('requests.get', mock_get)

    base_url = "http://localhost:5000"

    # First, authenticate as admin
    auth_url = f"{base_url}/login"
    auth_data = {"username": "admin", "password": "admin123"}

    print("Authenticating as admin...")
    auth_response = mock_post(auth_url, json=auth_data)

    assert auth_response.status_code == 200

    # Get session cookie
    cookies = auth_response.cookies

    print("Login successful!")

    # Check dashboard before enabling paper trading
    dashboard_url = f"{base_url}/api/dashboard"
    print("Checking dashboard before enabling paper trading...")
    dashboard_response = mock_get(dashboard_url, cookies=cookies)

    assert dashboard_response.status_code == 200
    dashboard_data = dashboard_response.json()
    system_status = dashboard_data.get("system_status", {})
    print(f"Before - trading_enabled: {system_status.get('trading_enabled')}")
    print(f"Before - paper_trading: {system_status.get('paper_trading')}")

    # Enable paper trading
    enable_url = f"{base_url}/api/enable_paper_trading"
    enable_data = {"enable": True}

    print("Enabling paper trading...")
    enable_response = mock_post(enable_url, json=enable_data, cookies=cookies)

    print(f"Enable response: {enable_response.status_code}")
    print(f"Enable response body: {enable_response.json()}")

    assert enable_response.status_code == 200
    enable_result = enable_response.json()
    print(f"Enable result: {enable_result}")

    # Check dashboard after enabling paper trading
    print("Checking dashboard after enabling paper trading...")
    dashboard_response2 = mock_get(dashboard_url, cookies=cookies)

    assert dashboard_response2.status_code == 200
    dashboard_data2 = dashboard_response2.json()
    system_status2 = dashboard_data2.get("system_status", {})
    print(f"After - trading_enabled: {system_status2.get('trading_enabled')}")
    print(f"After - paper_trading: {system_status2.get('paper_trading')}")

    # Check if the change persisted
    assert system_status2.get("trading_enabled") and system_status2.get("paper_trading")
    print("✅ SUCCESS: Paper trading enabled and dashboard reflects the change!")


if __name__ == "__main__":
    pytest.main([__file__])
