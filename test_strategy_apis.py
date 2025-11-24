#!/usr/bin/env python3
"""
Quick test for strategy API endpoints
"""
import requests
import json
import time
import threading
import os
import sys

def start_test_server():
    """Start the Flask app in test mode in a separate thread"""
    # Set test mode
    os.environ['AI_BOT_TEST_MODE'] = 'true'

    # Import and start the app
    sys.path.insert(0, '.')
    from ai_ml_auto_bot_final import app

    # Start the app in a thread
    def run_app():
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)

    server_thread = threading.Thread(target=run_app, daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(3)
    return server_thread

def test_strategy_apis():
    """Test the newly added strategy API endpoints"""
    base_url = "http://localhost:5000"

    print("🧪 Testing Strategy API Endpoints")
    print("=" * 50)

    # Test endpoints that don't require authentication
    endpoints = [
        '/api/qfm/status',
        '/api/qfm/signals',
        '/api/crt/status',
        '/api/ml/status',
        '/api/trading/status'
    ]

    results = {}

    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                results[endpoint] = "✅ PASS"
                print(f"  ✅ {endpoint}: {response.status_code}")
                # Print a bit of the response to verify it's working
                try:
                    data = response.json()
                    print(f"    Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                except:
                    print(f"    Response: {response.text[:100]}...")
            else:
                results[endpoint] = f"❌ FAIL ({response.status_code})"
                print(f"  ❌ {endpoint}: {response.status_code}")
        except Exception as e:
            results[endpoint] = f"❌ ERROR: {str(e)}"
            print(f"  ❌ {endpoint}: ERROR - {str(e)}")

    print("\n📊 Test Results:")
    print("=" * 50)
    for endpoint, result in results.items():
        print(f"{endpoint}: {result}")

    success_count = sum(1 for r in results.values() if "PASS" in r)
    total_count = len(results)

    print(f"\n🎯 Summary: {success_count}/{total_count} endpoints working")

    if success_count == total_count:
        print("🎉 All strategy API endpoints are working!")
        return True
    else:
        print("⚠️ Some endpoints need attention")
        return False

if __name__ == "__main__":
    print("🚀 Starting test server...")
    server_thread = start_test_server()

    try:
        success = test_strategy_apis()
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
        success = False
    finally:
        print("🛑 Shutting down test server...")

    exit(0 if success else 1)