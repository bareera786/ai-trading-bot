#!/usr/bin/env python3
"""
Manual fix based on the exact structure found
"""

def manual_fix():
    print("🔧 MANUAL FIX BASED ON DEBUG OUTPUT")
    print("=" * 50)
    
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        lines = f.readlines()
    
    # Find the line numbers for the problematic area
    deletion_route_line = None
    for i, line in enumerate(lines):
        if "@app.route('/api/users/<username>', methods=['DELETE'])" in line:
            deletion_route_line = i
            break
    
    if deletion_route_line is None:
        print("❌ Could not find the deletion route")
        return
    
    print(f"✅ Found deletion route at line: {deletion_route_line + 1}")
    
    # Check if this route is inside another function
    # Look backwards to find the containing function
    current_indent = None
    in_function = False
    function_start = None
    
    for i in range(deletion_route_line, 0, -1):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith('def '):
            function_start = i
            print(f"✅ Found containing function: {stripped} at line {i+1}")
            break
    
    if function_start is None:
        print("❌ Could not find containing function")
        return
    
    # Check what function contains the deletion route
    function_name_line = lines[function_start]
    print(f"🔍 Deletion route is inside: {function_name_line.strip()}")
    
    # Extract the function that contains the deletion route
    function_content = []
    i = function_start
    while i < len(lines) and (i == function_start or lines[i].strip() or lines[i].startswith('    ')):
        function_content.append(lines[i])
        i += 1
    
    print(f"🔍 Function content length: {len(function_content)} lines")
    
    # Find the deletion route within this function
    deletion_start = None
    for i, line in enumerate(function_content):
        if "@app.route('/api/users/<username>', methods=['DELETE'])" in line:
            deletion_start = i
            break
    
    if deletion_start is None:
        print("❌ Could not find deletion route in function content")
        return
    
    # Extract the deletion route from the function
    deletion_lines = []
    i = deletion_start
    while i < len(function_content):
        line = function_content[i]
        deletion_lines.append(line)
        
        # Check if we've reached the end of the deletion function
        if i > deletion_start and line.strip() and not line.startswith('    ') and not line.startswith('@'):
            # Found a line that's not indented and not a decorator - likely the next function
            break
        i += 1
    
    print(f"🔍 Extracted deletion route: {len(deletion_lines)} lines")
    
    # Remove the deletion route from the containing function
    new_function_content = function_content[:deletion_start] + function_content[deletion_start + len(deletion_lines):]
    
    # Rebuild the file
    new_lines = lines[:function_start] + new_function_content + ['\n'] + deletion_lines + lines[function_start + len(function_content):]
    
    # Write the fixed file
    with open('ai_ml_auto_bot_final.py', 'w') as f:
        f.writelines(new_lines)
    
    print("✅ Moved deletion route outside of containing function")
    
    # Verify the fix
    verify_fix()

def verify_fix():
    print("\n📋 VERIFYING FIX...")
    
    import subprocess
    result = subprocess.run(['python3', '-m', 'py_compile', 'ai_ml_auto_bot_final.py'], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("🎉 Syntax is valid!")
        print("🚀 You can now start your app:")
        print("python3 ai_ml_auto_bot_final.py")
    else:
        print("❌ Syntax errors remain:")
        print(result.stderr)

if __name__ == '__main__':
    manual_fix()
