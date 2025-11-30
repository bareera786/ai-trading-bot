#!/usr/bin/env python3
"""
Simple Dashboard Endpoint Test
Tests key endpoints manually
"""

import requests
import json

def test_endpoint(base_url, endpoint, method="GET", data=None, auth=True):
    """Test a single endpoint"""
    url = f"{base_url}{endpoint}"

    # Create session for cookies
    session = requests.Session()

    if auth:
        # Login first
        login_data = {"username": "admin", "password": "admin123"}
        login_response = session.post(f"{base_url}/login", json=login_data)
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            return False

    try:
        if method == "GET":
            response = session.get(url, timeout=10)
        elif method == "POST":
            response = session.post(url, json=data, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False

        if response.status_code == 200:
            print(f"✅ {endpoint} - {response.status_code}")
            return True
        else:
            print(f"❌ {endpoint} - {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ {endpoint} - Error: {e}")
        return False

def main():
    base_url = "http://localhost:5000"

    print("🧪 Testing key dashboard endpoints...")

    # Test public endpoints first
    print("\n📡 Public endpoints:")
    test_endpoint(base_url, "/health", auth=False)
    test_endpoint(base_url, "/api/realtime/market_data", auth=False)

    # Test auth endpoints
    print("\n🔐 Auth endpoints:")
    test_endpoint(base_url, "/api/current_user")
    test_endpoint(base_url, "/api/symbols")

    # Test core dashboard features
    print("\n📊 Dashboard features:")
    test_endpoint(base_url, "/api/dashboard")
    test_endpoint(base_url, "/api/status")
    test_endpoint(base_url, "/api/portfolio")

    # Test trading
    print("\n💰 Trading:")
    test_endpoint(base_url, "/api/spot/toggle", "POST", {"enabled": False})
    test_endpoint(base_url, "/api/futures/toggle", "POST", {"enabled": False})

    # Test analytics
    print("\n📈 Analytics:")
    test_endpoint(base_url, "/api/performance")
    test_endpoint(base_url, "/api/ml_telemetry")
    test_endpoint(base_url, "/api/qfm")

    # Test strategies
    print("\n🎯 Strategies:")
    test_endpoint(base_url, "/api/strategies")

    # Test backtesting
    print("\n🔬 Backtesting:")
    test_endpoint(base_url, "/api/backtests")

    # Test trade history
    print("\n📋 Trade History:")
    test_endpoint(base_url, "/api/trades")

    print("\n✅ Testing complete!")

if __name__ == "__main__":
    main()