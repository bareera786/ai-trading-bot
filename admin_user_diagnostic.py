#!/usr/bin/env python3
"""
Comprehensive diagnostic for admin and user management issues
"""

import os
import re
import requests

def comprehensive_admin_diagnostic():
    print("🔍 COMPREHENSIVE ADMIN & USER MANAGEMENT DIAGNOSTIC")
    print("=" * 60)
    
    # Check main application file
    if not os.path.exists('ai_ml_auto_bot_final.py'):
        print("❌ Main application file not found")
        return
    
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        content = f.read()
    
    print("\n📋 ADMIN & USER MANAGEMENT CHECK:")
    
    # 1. Check User Model
    print("\n👤 USER MODEL:")
    user_model_checks = {
        'User Class': 'class User(' in content,
        'is_admin Field': 'is_admin' in content and 'db.Column' in content,
        'is_active Field': 'is_active' in content and 'db.Column' in content,
        'Password Hashing': 'set_password' in content and 'check_password' in content,
        'Flask-Login Mixin': 'UserMixin' in content
    }
    
    for check, exists in user_model_checks.items():
        status = "✅" if exists else "❌"
        print(f"  {status} {check}")
    
    # 2. Check Admin Decorator
    print("\n🔐 ADMIN AUTHENTICATION:")
    admin_auth_checks = {
        'Admin Required Decorator': 'def admin_required' in content,
        'Login Required Decorator': '@login_required' in content,
        'Current User Import': 'current_user' in content,
        'Admin Check Logic': 'current_user.is_admin' in content
    }
    
    for check, exists in admin_auth_checks.items():
        status = "✅" if exists else "❌"
        print(f"  {status} {check}")
    
    # 3. Check User Management Routes
    print("\n🛣️  USER MANAGEMENT ROUTES:")
    user_routes = [
        ('/api/users', 'GET', 'List users'),
        ('/api/users', 'POST', 'Create user'),
        ('/api/users/', 'DELETE', 'Delete user'),
        ('/login', 'POST', 'User login'),
        ('/logout', 'GET', 'User logout')
    ]
    
    for route, method, description in user_routes:
        if f"@app.route('{route}'" in content or f'@app.route("{route}"' in content:
            # Check if it has the right method
            methods_pattern = f"methods=\[.*{method}.*\]"
            if re.search(methods_pattern, content):
                print(f"  ✅ {method} {route} - {description}")
            else:
                print(f"  ⚠️  {route} - {description} (wrong method)")
        else:
            print(f"  ❌ {route} - {description} (missing)")
    
    # 4. Check Database Initialization
    print("\n🗄️  DATABASE & INITIALIZATION:")
    db_checks = {
        'SQLAlchemy Setup': 'SQLAlchemy(' in content,
        'DB Create All': 'db.create_all()' in content,
        'Admin User Creation': 'admin' in content and 'set_password' in content,
        'Default Admin Check': 'User.query.filter_by' in content
    }
    
    for check, exists in db_checks.items():
        status = "✅" if exists else "❌"
        print(f"  {status} {check}")
    
    # 5. Test Live Endpoints (if app is running)
    print("\n🌐 LIVE ENDPOINT TESTING:")
    try:
        base_url = "http://localhost:5000"
        
        # Test health endpoint
        health_resp = requests.get(f"{base_url}/health", timeout=5)
        print(f"  ✅ Health endpoint: {health_resp.status_code}")
        
        # Test login
        login_data = {"username": "admin", "password": "admin123"}
        login_resp = requests.post(f"{base_url}/login", json=login_data, timeout=5)
        print(f"  ✅ Login endpoint: {login_resp.status_code}")
        
        if login_resp.status_code == 200:
            session_cookies = login_resp.cookies
            
            # Test user list (admin function)
            users_resp = requests.get(f"{base_url}/api/users", cookies=session_cookies, timeout=5)
            print(f"  ✅ User list endpoint: {users_resp.status_code}")
            
            # Test user creation
            test_user = {"username": f"testuser_{os.getpid()}", "password": "test123", "is_admin": False}
            create_resp = requests.post(f"{base_url}/api/users", json=test_user, cookies=session_cookies, timeout=5)
            print(f"  ✅ User creation endpoint: {create_resp.status_code}")
            
        else:
            print(f"  ❌ Login failed: {login_resp.text}")
            
    except Exception as e:
        print(f"  ⚠️  Live testing skipped: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSTIC COMPLETE")

def extract_problematic_code():
    """Extract and display problematic code sections"""
    print("\n🔍 ANALYZING PROBLEMATIC CODE SECTIONS:")
    print("=" * 40)
    
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        content = f.read()
    
    # Extract admin_required decorator
    admin_decorator_match = re.search(r'def admin_required.*?return decorated_function', content, re.DOTALL)
    if admin_decorator_match:
        print("\n🔐 ADMIN REQUIRED DECORATOR:")
        print(admin_decorator_match.group(0))
    else:
        print("❌ Admin required decorator not found")
    
    # Extract user creation route
    user_create_match = re.search(r"@app\.route.*?/api/users.*?methods=\[.*?POST.*?\].*?def api_create_user.*?return.*?\)", content, re.DOTALL)
    if user_create_match:
        print("\n👤 USER CREATION ROUTE:")
        print(user_create_match.group(0)[:500] + "..." if len(user_create_match.group(0)) > 500 else user_create_match.group(0))
    else:
        print("❌ User creation route not found")

if __name__ == '__main__':
    comprehensive_admin_diagnostic()
    extract_problematic_code()
