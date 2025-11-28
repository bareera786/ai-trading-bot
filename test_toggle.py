#!/usr/bin/env python3
import requests
import json

# First, authenticate as admin
auth_url = "http://localhost:5000/auth/login"
auth_data = {
    "username": "admin",
    "password": "admin123"
}

print("Authenticating as admin...")
auth_response = requests.post(auth_url, json=auth_data)
print(f"Auth status: {auth_response.status_code}")

if auth_response.status_code == 200:
    auth_json = auth_response.json()
    token = auth_json.get('access_token')
    print(f"Got token: {token[:20]}...")

    # Now toggle trading
    toggle_url = "http://localhost:5000/api/toggle_trading"
    headers = {"Authorization": f"Bearer {token}"}

    print("Toggling trading...")
    toggle_response = requests.post(toggle_url, headers=headers)
    print(f"Toggle status: {toggle_response.status_code}")
    print(f"Toggle response: {toggle_response.text}")

    # Toggle again
    print("Toggling trading again...")
    toggle_response2 = requests.post(toggle_url, headers=headers)
    print(f"Toggle status: {toggle_response2.status_code}")
    print(f"Toggle response: {toggle_response2.text}")

else:
    print(f"Auth failed: {auth_response.text}")