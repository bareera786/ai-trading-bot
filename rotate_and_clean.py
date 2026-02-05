import os
from pathlib import Path

def check_key_exposure():
    """Check if any keys were exposed in audit files"""

    print("🔍 Checking for key exposure in audit files...")

    exposed_keys = []

    # Check audit files for API key mentions
    for audit_file in Path('.').glob('audit_*.json'):
        try:
            with open(audit_file, 'r') as f:
                content = f.read()

            # Look for API key patterns
            if 'sk-' in content and len(content.split('sk-')[1]) > 20:
                exposed_keys.append({
                    'file': str(audit_file),
                    'type': 'DeepSeek API Key',
                    'context': content.split('sk-')[1][:30] + '...'
                })
        except Exception:
            pass

    return exposed_keys

def create_rotation_checklist():
    """Create a checklist for key rotation"""

    checklist = [
        {
            'service': 'DeepSeek API',
            'url': 'https://platform.deepseek.com/api_keys',
            'action': 'Revoke current key, generate new one',
            'priority': 'HIGH'
        },
        {
            'service': 'Binance API',
            'url': 'https://www.binance.com/en/my/settings/api-management',
            'action': 'Check if keys were exposed, rotate if needed',
            'priority': 'HIGH'
        },
        {
            'service': 'Database Credentials',
            'url': 'N/A',
            'action': 'Rotate database passwords if exposed',
            'priority': 'MEDIUM'
        },
        {
            'service': 'Other Third-party APIs',
            'url': 'N/A',
            'action': 'Check for any other API keys in code',
            'priority': 'MEDIUM'
        }
    ]

    return checklist

def generate_cleanup_commands():
    """Generate commands to clean up exposed keys"""

    commands = []

    # Check git history
    commands.append({
        'desc': 'Check git history for .env',
        'cmd': 'git log --all --full-history --oneline -- .env 2>/dev/null | head -5'
    })

    commands.append({
        'desc': 'Remove .env from git if committed',
        'cmd': 'git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all'
    })

    commands.append({
        'desc': 'Force push after cleanup',
        'cmd': 'git push origin --force --all'
    })

    return commands

if __name__ == "__main__":
    print("🔄 KEY ROTATION & CLEANUP ASSISTANT")
    print("=" * 80)

    # Check for exposed keys
    exposed = check_key_exposure()
    if exposed:
        print("🚨 POTENTIAL KEY EXPOSURE FOUND!")
        for exp in exposed:
            print(f"  • {exp['file']}: {exp['type']}")
        print("\n⚠️  These audit files may contain API keys. Consider:")
        print("   - Deleting audit files after review")
        print("   - Rotating exposed keys immediately")
    else:
        print("✅ No obvious key exposure found in audit files")

    # Show rotation checklist
    print("\n📋 KEY ROTATION CHECKLIST:")
    print("=" * 80)
    checklist = create_rotation_checklist()
    for item in checklist:
        print(f"\n{item['service']} [{item['priority']}]:")
        print(f"  Action: {item['action']}")
        print(f"  URL: {item['url']}")

    # Generate cleanup commands
    print("\n🛠️  CLEANUP COMMANDS (if needed):")
    print("=" * 80)
    commands = generate_cleanup_commands()
    for cmd in commands:
        print(f"\n{cmd['desc']}:")
        print(f"  {cmd['cmd']}")

    print("\n" + "=" * 80)
    print("🎯 IMMEDIATE ACTIONS:")
    print("1. Rotate DeepSeek API key (HIGHEST priority)")
    print("2. Rotate Binance API keys if exposed")
    print("3. Delete audit files after reviewing findings")
    print("4. Update .env with new keys")
    print("5. Run security audit again after changes")
#!/usr/bin/env python3
import os
import json
from pathlib import Path

def check_key_exposure():
    """Check if any keys were exposed in audit files"""
    print("🔍 Checking for key exposure in audit files...")
    exposed_keys = []
    for audit_file in Path('.').glob('audit_*.json'):
        try:
            with open(audit_file, 'r') as f:
                content = f.read()
            if 'sk-' in content and len(content.split('sk-')[1]) > 20:
                exposed_keys.append({
                    'file': str(audit_file),
                    'type': 'DeepSeek API Key',
                    'context': content.split('sk-')[1][:30] + '...'
                })
        except Exception:
            pass
    return exposed_keys

def create_rotation_checklist():
    checklist = [
        {
            'service': 'DeepSeek API',
            'url': 'https://platform.deepseek.com/api_keys',
            'action': 'Revoke current key, generate new one',
            'priority': 'HIGH'
        },
        {
            'service': 'Binance API',
            'url': 'https://www.binance.com/en/my/settings/api-management',
            'action': 'Check if keys were exposed, rotate if needed',
            'priority': 'HIGH'
        },
        {
            'service': 'Database Credentials',
            'url': 'N/A',
            'action': 'Rotate database passwords if exposed',
            'priority': 'MEDIUM'
        },
        {
            'service': 'Other Third-party APIs',
            'url': 'N/A',
            'action': 'Check for any other API keys in code',
            'priority': 'MEDIUM'
        }
    ]
    return checklist

def generate_cleanup_commands():
    commands = []
    commands.append({
        'desc': 'Check git history for .env',
        'cmd': 'git log --all --full-history --oneline -- .env 2>/dev/null | head -5'
    })
    commands.append({
        'desc': 'Remove .env from git if committed',
        'cmd': 'git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all'
    })
    commands.append({
        'desc': 'Force push after cleanup',
        'cmd': 'git push origin --force --all'
    })
    return commands

if __name__ == '__main__':
    print("🔄 KEY ROTATION & CLEANUP ASSISTANT")
    print("=" * 80)
    exposed = check_key_exposure()
    if exposed:
        print("🚨 POTENTIAL KEY EXPOSURE FOUND!")
        for exp in exposed:
            print(f"  • {exp['file']}: {exp['type']}")
        print("\n⚠️  These audit files may contain API keys. Consider:")
        print("   - Deleting audit files after review")
        print("   - Rotating exposed keys immediately")
    else:
        print("✅ No obvious key exposure found in audit files")

    print("\n📋 KEY ROTATION CHECKLIST:")
    print("=" * 80)
    checklist = create_rotation_checklist()
    for item in checklist:
        print(f"\n{item['service']} [{item['priority']}]:")
        print(f"  Action: {item['action']}")
        print(f"  URL: {item['url']}")

    print("\n🛠️  CLEANUP COMMANDS (if needed):")
    print("=" * 80)
    commands = generate_cleanup_commands()
    for cmd in commands:
        print(f"\n{cmd['desc']}:")
        print(f"  {cmd['cmd']}")

    print("\n" + "=" * 80)
    print("🎯 IMMEDIATE ACTIONS:")
    print("1. Rotate DeepSeek API key (HIGHEST priority)")
    print("2. Rotate Binance API keys if exposed")
    print("3. Delete audit files after reviewing findings")
    print("4. Update .env with new keys")
    print("5. Run security audit again after changes")
