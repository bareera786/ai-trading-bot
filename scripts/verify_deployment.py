#!/usr/bin/env python3
import requests
import sys
import os
from urllib.parse import urljoin

# Configuration
BASE_URL = os.environ.get("BOT_URL", "http://localhost:5000")
print(f"🔍 Verifying Deployment at: {BASE_URL}")

def check_endpoint(path, expected_code=200):
    url = urljoin(BASE_URL, path)
    try:
        response = requests.get(url, timeout=5)
        status = response.status_code
        if status == expected_code:
            print(f"✅ {path}: OK ({status})")
            return True
        else:
            print(f"❌ {path}: FAILED (Expected {expected_code}, got {status})")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ {path}: CONNECTION REFUSED")
        return False
    except Exception as e:
        print(f"❌ {path}: MEMORY ERROR ({e})")
        return False

def check_static_asset(path):
    url = urljoin(BASE_URL, path)
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ Asset {path}: FOUND")
            return True
        elif response.status_code == 403:
            print(f"❌ Asset {path}: 403 FORBIDDEN (Permission Issue?)")
            return False
        elif response.status_code == 404:
            print(f"❌ Asset {path}: 404 NOT FOUND")
            return False
        else:
            print(f"❌ Asset {path}: FAILED ({response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Asset {path}: ERROR {e}")
        return False

# 1. Health Checks
print("\n--- System Health ---")
app_health = check_endpoint("/api/health") # The robust app check
nginx_health = check_endpoint("/health")   # The Nginx simple check

# 2. Static Assets (Simulate the browser loading files)
print("\n--- Static Assets ---")
css_ok = check_static_asset("/static/css/dashboard.css")
js_ok = check_static_asset("/static/js/dashboard.js")
favicon_ok = check_static_asset("/static/favicon.ico")

# 3. Critical API Endpoints (Admin)
print("\n--- Critical APIs ---")
# API endpoints might return 401/403 if unauthorized, which actually means they are WORKING (reachable)
check_endpoint("/api/users", expected_code=401) # Should require login
check_endpoint("/auth/login", expected_code=200)

print("\n--- Summary ---")
if app_health and css_ok and js_ok:
    print("🚀 Deployment Verification: PASSED")
    sys.exit(0)
else:
    print("⚠️ Deployment Verification: FAILED (See above for details)")
    sys.exit(1)
