#!/usr/bin/env python3
"""
Fix indentation errors in ai_ml_auto_bot_final.py
"""

def fix_indentation_errors():
    print("🔧 Fixing indentation errors...")
    
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        lines = f.readlines()
    
    # Find the problematic line
    error_line_num = None
    for i, line in enumerate(lines):
        if '@app.route(\'/api/users/<username>\', methods=[\'DELETE\'])' in line:
            error_line_num = i
            break
    
    if error_line_num is None:
        print("❌ Could not find the problematic line")
        return
    
    print(f"✅ Found problematic line at: {error_line_num + 1}")
    
    # Check the previous line to determine correct indentation
    if error_line_num > 0:
        prev_line = lines[error_line_num - 1]
        # Count spaces in previous line to determine indentation level
        if prev_line.strip():  # If previous line is not empty
            indent_level = len(prev_line) - len(prev_line.lstrip())
            current_line = lines[error_line_num]
            
            # Fix current line indentation
            if not current_line.startswith(' ' * indent_level):
                lines[error_line_num] = ' ' * indent_level + current_line.lstrip()
                print(f"✅ Fixed indentation for line {error_line_num + 1}")
            
            # Also check and fix the next lines (the function definition and decorators)
            # Look for the next few lines that should be at the same indentation level
            for i in range(error_line_num, min(error_line_num + 10, len(lines))):
                line = lines[i]
                if line.strip() and not line.startswith(' ' * indent_level):
                    if not (line.strip().startswith('@') or line.strip().startswith('def ')):
                        break
                    lines[i] = ' ' * indent_level + line.lstrip()
                    print(f"✅ Fixed indentation for line {i + 1}")
    
    # Write fixed content back
    with open('ai_ml_auto_bot_final.py', 'w') as f:
        f.writelines(lines)
    
    print("🎉 Indentation errors fixed!")
    
    # Verify the fix by checking the problematic area
    print("\n📋 VERIFYING FIX:")
    with open('ai_ml_auto_bot_final.py', 'r') as f:
        content = f.read()
    
    # Find the user deletion route and show context
    deletion_route_pos = content.find('@app.route(\'/api/users/<username>\', methods=[\'DELETE\'])')
    if deletion_route_pos != -1:
        start = max(0, deletion_route_pos - 200)
        end = min(len(content), deletion_route_pos + 500)
        context = content[start:end]
        print("Context around the fixed route:")
        print("..." + context + "...")
    
    print("\n🚀 Now try starting your app again:")
    print("python3 ai_ml_auto_bot_final.py")

if __name__ == '__main__':
    fix_indentation_errors()
