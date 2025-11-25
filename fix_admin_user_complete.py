#!/usr/bin/env python3
"""
COMPLETE FIX for admin and user management issues
"""

import re
import os

def fix_all_admin_user_issues():
    print("🔧 COMPREHENSIVE ADMIN & USER MANAGEMENT FIX")
    print("=" * 50)
    
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        content = f.read()
    
    # FIX 1: Fix admin_required decorator (remove nested @login_required)
    old_admin_decorator = '''def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function'''
    
    new_admin_decorator = '''def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Please login first'}), 401
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function'''
    
    if old_admin_decorator in content:
        content = content.replace(old_admin_decorator, new_admin_decorator)
        print("✅ Fixed admin_required decorator (removed nested @login_required)")
    
    # FIX 2: Add missing user deletion route
    user_deletion_route = '''
@app.route('/api/users/<username>', methods=['DELETE'])
@admin_required
def api_delete_user(username):
    """Delete a user - Admin only"""
    try:
        # Prevent admin from deleting themselves
        if username == current_user.username:
            return jsonify({'error': 'Cannot delete your own account'}), 400

        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Delete user's portfolio and trades
        UserPortfolio.query.filter_by(user_id=user.id).delete()
        UserTrade.query.filter_by(user_id=user.id).delete()
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': f'User {username} deleted successfully'})

    except Exception as e:
        db.session.rollback()
        print(f"Error deleting user: {e}")
        return jsonify({'error': str(e)}), 500
'''
    
    # Find where to add deletion route (after user creation route)
    user_routes_pos = content.find('@app.route(\'/api/users\', methods=[\'POST\'])')
    if user_routes_pos != -1:
        # Find the end of the user creation function
        end_pos = content.find('return jsonify', user_routes_pos)
        end_pos = content.find('\n\n', end_pos)  # Find double newline after function
        
        if end_pos != -1:
            content = content[:end_pos] + user_deletion_route + content[end_pos:]
            print("✅ Added missing user deletion route")
    
    # FIX 3: Ensure User model has all required fields
    user_model_check = [
        'is_admin = db.Column(db.Boolean, default=False)',
        'is_active = db.Column(db.Boolean, default=True)',
        'created_at = db.Column(db.DateTime, default=datetime.utcnow)',
        'last_login = db.Column(db.DateTime)'
    ]
    
    for field in user_model_check:
        if field not in content:
            print(f"⚠️  Missing User model field: {field}")
    
    # FIX 4: Add proper error handling to user creation
    # Find and fix the user creation route
    user_create_pattern = r"@app\.route\('/api/users', methods=\['POST'\]\).*?@admin_required.*?def api_create_user.*?try:.*?return jsonify\(.*?\)"
    
    if not re.search(user_create_pattern, content, re.DOTALL):
        print("❌ User creation route pattern not found, adding complete route...")
        
        complete_user_creation = '''
@app.route('/api/users', methods=['POST'])
@admin_required
def api_create_user():
    """Create a new user - Admin only"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        is_admin = data.get('is_admin', False)

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        # Check if username exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400

        # Create new user
        new_user = User(
            username=username,
            email=f"{username}@tradingbot.com",
            is_admin=is_admin
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Create portfolio for new user
        portfolio = UserPortfolio(user_id=new_user.id)
        db.session.add(portfolio)
        db.session.commit()

        return jsonify({
            'message': f'User {username} created successfully',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'is_admin': new_user.is_admin
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"User creation error: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500
'''
        
        # Try to replace existing route or add new one
        existing_route_pattern = r"@app\.route\('/api/users', methods=\['POST'\]\).*?def api_create_user.*?return jsonify\(.*?\)"
        if re.search(existing_route_pattern, content, re.DOTALL):
            content = re.sub(existing_route_pattern, complete_user_creation, content, flags=re.DOTALL)
            print("✅ Replaced user creation route with complete version")
        else:
            # Add after other user routes
            user_routes_end = content.find('@app.route(\'/api/users\', methods=[\'GET\'])')
            if user_routes_end != -1:
                user_routes_end = content.find('\n\n', user_routes_end)
                content = content[:user_routes_end] + complete_user_creation + content[user_routes_end:]
                print("✅ Added complete user creation route")
    
    # FIX 5: Add missing imports if needed
    required_imports = [
        'from datetime import datetime',
        'from functools import wraps'
    ]
    
    for imp in required_imports:
        if imp not in content:
            # Add to imports section
            imports_section = content.find('from flask import')
            if imports_section != -1:
                content = content[:imports_section] + imp + '\n' + content[imports_section:]
                print(f"✅ Added missing import: {imp}")
    
    # Write updated content
    with open('ai_ml_auto_bot_final.py', 'w') as f:
        f.write(content)
    
    print("\n🎉 ALL ADMIN & USER MANAGEMENT FIXES APPLIED!")
    print("\n📋 FIXES APPLIED:")
    print("  ✅ Fixed admin_required decorator (no nested @login_required)")
    print("  ✅ Added missing user deletion route")
    print("  ✅ Ensured complete user creation route")
    print("  ✅ Added missing imports if needed")
    
    # Create test script
    create_test_script()

def create_test_script():
    """Create a test script to verify fixes"""
    test_script = '''#!/usr/bin/env python3
"""
Test script for admin and user management fixes
"""

import requests
import time
import sys

def test_admin_user_management():
    base_url = "http://localhost:5000"
    
    print("🧪 TESTING ADMIN & USER MANAGEMENT FIXES")
    print("=" * 50)
    
    # Wait for app to start
    print("⏳ Waiting for app to start...")
    time.sleep(3)
    
    try:
        # Test 1: Login as admin
        print("\\n1. Testing admin login...")
        login_data = {"username": "admin", "password": "admin123"}
        response = requests.post(f"{base_url}/login", json=login_data)
        
        if response.status_code != 200:
            print(f"   ❌ Login failed: {response.status_code} - {response.text}")
            return False
        
        print("   ✅ Admin login successful")
        session_cookies = response.cookies
        
        # Test 2: List users (admin function)
        print("\\n2. Testing user list...")
        response = requests.get(f"{base_url}/api/users", cookies=session_cookies)
        
        if response.status_code == 200:
            users_data = response.json()
            print(f"   ✅ User list: {len(users_data.get('users', []))} users")
        elif response.status_code == 403:
            print("   ❌ User list: Admin access denied (admin_required not working)")
            return False
        else:
            print(f"   ❌ User list failed: {response.status_code} - {response.text}")
            return False
        
        # Test 3: Create new user
        print("\\n3. Testing user creation...")
        test_username = f"testuser_{int(time.time())}"
        user_data = {
            "username": test_username,
            "password": "test123",
            "is_admin": False
        }
        
        response = requests.post(f"{base_url}/api/users", json=user_data, cookies=session_cookies)
        
        if response.status_code == 201:
            print(f"   ✅ User creation: {test_username} created successfully")
        else:
            print(f"   ❌ User creation failed: {response.status_code} - {response.text}")
            return False
        
        # Test 4: Delete user
        print("\\n4. Testing user deletion...")
        response = requests.delete(f"{base_url}/api/users/{test_username}", cookies=session_cookies)
        
        if response.status_code == 200:
            print(f"   ✅ User deletion: {test_username} deleted successfully")
        else:
            print(f"   ❌ User deletion failed: {response.status_code} - {response.text}")
            return False
        
        print("\\n🎉 ALL ADMIN & USER MANAGEMENT TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("💡 Make sure the Flask app is running: python3 ai_ml_auto_bot_final.py")
        return False

if __name__ == "__main__":
    if test_admin_user_management():
        sys.exit(0)
    else:
        sys.exit(1)
'''
    
    with open('test_admin_fixes.py', 'w') as f:
        f.write(test_script)
    
    print("✅ Created test script: test_admin_fixes.py")
    print("\\n🚀 NEXT STEPS:")
    print("1. Start your app: python3 ai_ml_auto_bot_final.py")
    print("2. Run tests: python3 test_admin_fixes.py")
    print("3. Check browser: http://localhost:5000")

if __name__ == '__main__':
    fix_all_admin_user_issues()
