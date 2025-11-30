#!/usr/bin/env python3
"""
Test script to verify dashboard endpoints work correctly
"""

import requests
import time
import subprocess
import signal
import os
import sys

def test_endpoints():
    """Test the login and symbols endpoints"""
    base_url = "http://localhost:5000"

    print("🧪 Testing Dashboard Endpoints...")

    # Test login
    print("\n1. Testing login endpoint...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }

    try:
        response = requests.post(f"{base_url}/login", json=login_data, timeout=10)
        print(f"Login response status: {response.status_code}")
        print(f"Login response: {response.text[:200]}...")

        if response.status_code == 200:
            print("✅ Login successful!")

            # Extract session cookie if available
            session_cookie = None
            if 'session' in response.cookies:
                session_cookie = response.cookies['session']
                print(f"Session cookie obtained: {session_cookie[:20]}...")

            # Test symbols endpoint
            print("\n2. Testing symbols endpoint...")
            headers = {}
            if session_cookie:
                headers['Cookie'] = f'session={session_cookie}'

            response = requests.get(f"{base_url}/api/symbols", headers=headers, timeout=10)
            print(f"Symbols response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Symbols endpoint working! Returned {len(data) if isinstance(data, list) else 'data'} items")
                if isinstance(data, list) and len(data) > 0:
                    print(f"Sample symbol: {data[0]}")
            else:
                print(f"❌ Symbols endpoint failed: {response.text[:200]}")

        else:
            print(f"❌ Login failed: {response.text[:200]}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def start_server():
    """Start the Flask server"""
    print("🚀 Starting Flask server...")
    env = os.environ.copy()
    env['PYTHONPATH'] = '/Users/tahir/Desktop/ai-bot'
    env['FLASK_APP'] = '/Users/tahir/Desktop/ai-bot/ai_ml_auto_bot_final.py'
    env['FLASK_ENV'] = 'development'

    process = subprocess.Popen([
        '/Users/tahir/Desktop/ai-bot/.venv/bin/flask',
        'run',
        '--host=0.0.0.0',
        '--port=5000'
    ], cwd='/Users/tahir/Desktop/ai-bot', env=env)

    return process

def main():
    # Start server
    server_process = start_server()

    try:
        # Wait for server to start - give it more time
        print("⏳ Waiting for server to initialize...")
        time.sleep(25)  # Give more time for full initialization

        # Test endpoints multiple times in case server is still starting
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                print(f"\n🔄 Attempt {attempt + 1}/{max_attempts} to test endpoints...")
                test_endpoints()
                break  # Success, exit loop
            except Exception as e:
                if attempt == max_attempts - 1:
                    print(f"❌ All attempts failed. Last error: {e}")
                else:
                    print(f"⚠️ Attempt {attempt + 1} failed, retrying...")
                    time.sleep(5)

    except KeyboardInterrupt:
        print("\n🛑 Test interrupted")
    finally:
        # Clean up server
        print("🛑 Stopping server...")
        if server_process.poll() is None:
            server_process.terminate()
            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()

        print("✅ Test completed")

if __name__ == "__main__":
    main()