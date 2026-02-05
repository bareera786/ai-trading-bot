import os
import re

def check_for_hardcoded_secrets():
    """Look for potential hardcoded API keys/secrets"""
    secrets_patterns = [
        r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'api[_-]?secret["\']?\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'binance.*key["\']?\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'secret["\']?\s*[:=]\s*["\'][^"\']{10,}["\']',
        r'password["\']?\s*[:=]\s*["\']{5,}',
        r'token["\']?\s*[:=]\s*["\'][^"\']{10,}["\']',
    ]
    
    issues = []
    for root, dirs, files in os.walk('.'):
        # Skip virtual environments and git
        if any(d in root for d in ['.venv', '.git', '__pycache__', 'node_modules']):
            continue
            
        for file in files:
            if file.endswith(('.py', '.env', '.yaml', '.yml', '.json')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    for i, pattern in enumerate(secrets_patterns):
                        if re.search(pattern, content, re.IGNORECASE):
                            # Extract line for context
                            lines = content.split('\n')
                            for line_num, line in enumerate(lines, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    issues.append({
                                        'file': filepath,
                                        'line': line_num,
                                        'pattern': pattern,
                                        'snippet': line.strip()[:200]
                                    })
                except Exception:
                    pass
    
    return issues

def check_env_files():
    """Check if .env files exist"""
    env_files = []
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.env') and '.git' not in root:
                env_files.append(os.path.join(root, file))
    
    return env_files

def main():
    print("🔒 SECURITY AUDIT - Hardcoded Secrets Check")
    print("=" * 50)
    
    # Check for secrets
    secrets = check_for_hardcoded_secrets()
    
    if secrets:
        print(f"❌ Found {len(secrets)} potential hardcoded secrets:")
        for secret in secrets[:20]:  # show up to 20
            print(f"\n📄 {secret['file']}:{secret['line']}")
            print(f"   {secret['snippet']}")
        if len(secrets) > 20:
            print(f"\n... and {len(secrets) - 20} more")
    else:
        print("✅ No hardcoded secrets found in scanned files")
    
    # Check .env files
    env_files = check_env_files()
    if env_files:
        print(f"\n📁 Found {len(env_files)} .env files:")
        for env in env_files:
            print(f"   • {env}")
        print("\n⚠️  Ensure .env is in .gitignore!")
    
    # Check .gitignore
    if os.path.exists('.gitignore'):
        try:
            with open('.gitignore', 'r') as f:
                gitignore = f.read()
            if '.env' not in gitignore:
                print("❌ .env not found in .gitignore - ADD THIS!")
            if '*.key' not in gitignore:
                print("❌ *.key not found in .gitignore - CONSIDER ADDING")
        except Exception:
            print("❌ Could not read .gitignore")
    else:
        print("❌ No .gitignore file found!")

if __name__ == "__main__":
    main()
