#!/usr/bin/env python3
"""
Fix misplaced user deletion route that's inside user creation function
"""

def fix_misplaced_routes():
    print("🔧 Fixing misplaced route definition...")
    
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        content = f.read()
    
    # Find the problematic section where user deletion is inside user creation
    # We need to extract the user deletion route and move it outside
    user_creation_start = content.find('def api_create_user():')
    if user_creation_start == -1:
        print("❌ Could not find api_create_user function")
        return
    
    # Find the end of the user creation function
    user_creation_end = user_creation_start
    indent_level = 0
    lines = content[user_creation_start:].split('\n')
    
    for i, line in enumerate(lines):
        if i == 0:
            # First line is the function definition
            continue
        
        stripped = line.strip()
        if not stripped:
            continue
            
        if stripped.startswith('def ') and i > 0:
            # Found next function, this is the end
            break
            
        if stripped.startswith('@app.route'):
            # Found a route decorator inside the function - this is wrong!
            break
    
    # The end of user creation function is at this point
    user_creation_end_absolute = user_creation_start + sum(len(line) + 1 for line in lines[:i])
    
    # Extract the user creation function content
    user_creation_content = content[user_creation_start:user_creation_end_absolute]
    
    # Now find the user deletion route inside the user creation function
    deletion_start = user_creation_content.find("@app.route('/api/users/<username>', methods=['DELETE'])")
    if deletion_start == -1:
        print("❌ Could not find user deletion route inside user creation function")
        return
    
    # Extract the user deletion route from inside user creation
    deletion_content = user_creation_content[deletion_start:]
    
    # Find the end of the deletion function
    deletion_lines = deletion_content.split('\n')
    deletion_end = 0
    for i, line in enumerate(deletion_lines):
        if i > 0 and line.strip() and not line.startswith('    ') and not line.startswith('@'):
            # Found the next non-indented line that's not a decorator
            deletion_end = sum(len(deletion_lines[j]) + 1 for j in range(i))
            break
    
    if deletion_end == 0:
        deletion_end = len(deletion_content)
    
    deletion_route = deletion_content[:deletion_end]
    
    # Remove the deletion route from user creation function
    fixed_user_creation = user_creation_content[:deletion_start] + user_creation_content[deletion_start + deletion_end:]
    
    # Rebuild the content
    before_user_creation = content[:user_creation_start]
    after_user_creation = content[user_creation_start + len(user_creation_content):]
    
    # Insert deletion route after user creation function
    new_content = before_user_creation + fixed_user_creation + '\n\n' + deletion_route + after_user_creation
    
    # Write fixed content
    with open('ai_ml_auto_bot_final.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Fixed misplaced user deletion route")
    print("✅ User deletion route is now properly placed outside user creation function")
    
    # Verify the fix
    verify_fix()

def verify_fix():
    print("\n📋 VERIFYING FIX...")
    
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        content = f.read()
    
    # Check if user creation and deletion are now separate
    user_creation_pos = content.find('def api_create_user():')
    user_deletion_pos = content.find("def api_delete_user(username):")
    
    if user_creation_pos == -1 or user_deletion_pos == -1:
        print("❌ Could not find one of the functions")
        return
    
    if user_deletion_pos > user_creation_pos:
        # Check if there's proper separation
        between_content = content[user_creation_pos:user_deletion_pos]
        if 'def api_create_user():' in between_content and 'def api_delete_user(username):' in between_content:
            print("✅ Functions are now properly separated")
        else:
            print("⚠️  Functions might still be nested")
    else:
        print("❌ Deletion function is still before creation function")
    
    # Test syntax
    import subprocess
    result = subprocess.run(['python3', '-m', 'py_compile', 'ai_ml_auto_bot_final.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("🎉 Syntax is valid! You can now start your app.")
        print("\n🚀 Start your app with:")
        print("python3 ai_ml_auto_bot_final.py")
    else:
        print("❌ Syntax errors remain:")
        print(result.stderr)

if __name__ == '__main__':
    fix_misplaced_routes()
