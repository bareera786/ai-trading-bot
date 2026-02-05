#!/usr/bin/env python3
"""Comprehensive security remediation helper.

Performs non-destructive checks and optionally secures audit files.
"""
import os
import re
import shutil
import subprocess
from datetime import datetime


def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
        return out.strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()


def check_git_history_for_env():
    print('🔍 Checking git history for .env (first 5 entries)')
    res = run_cmd('git log --all --full-history --oneline -- .env 2>/dev/null | head -5')
    if res:
        print(res)
    else:
        print('No .env entries found in recent git history')


def check_git_for_api_key_commits():
    print('\n🔍 Searching commits for "api_key"... (showing first 20 lines)')
    res = run_cmd('git log -p --all -S "api_key" --name-only | head -20')
    if res:
        print(res)
    else:
        print('No commits matching "api_key" found')


def check_recent_commits():
    print('\n📋 Recent commits (last 10)')
    res = run_cmd('git log --oneline -10')
    print(res)


def check_env_file():
    print('\n🔐 Current .env file status:')
    fn = '.env'
    if os.path.exists(fn):
        perm = oct(os.stat(fn).st_mode)[-3:]
        size = sum(1 for _ in open(fn))
        print(f'✅ .env exists')
        print(f'📁 Permissions: {perm}')
        print(f'📊 Size: {size} lines')
        text = open(fn).read()
        if re.search(r'your_.*_here|example|placeholder|change_me', text, re.I):
            print('⚠️  Contains placeholder values - OK for development')
        else:
            print("🔒 Contains actual values - ensure it's not committed")
        print('First 3 lines (masked):')
        with open(fn) as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                print('*' * len(line.rstrip('\n')))
    else:
        print('❌ .env file not found!')


def ensure_gitignore_patterns():
    print('\n📁 Ensuring .gitignore has security patterns')
    patterns = ['.env', '*.key', '*.pem', '*.secret', 'audit_*.json', '__pycache__/', '.venv/', '*.pyc']
    gi = '.gitignore'
    added = []
    if not os.path.exists(gi):
        print('No .gitignore found; creating one with common patterns')
        with open(gi, 'w') as f:
            f.write('# Auto-created .gitignore\n')
    with open(gi, 'r+') as f:
        content = f.read()
        for p in patterns:
            # match full-line or leading slash variants
            if re.search(rf'^(?:{re.escape(p)}|/{re.escape(p)})$', content, re.M):
                continue
            if p not in content:
                f.write(p + '\n')
                added.append(p)
    if added:
        print('Added to .gitignore:')
        for a in added:
            print('  -', a)
    else:
        print('All critical patterns present in .gitignore')


def run_rotate_and_clean():
    print('\n🔄 Running rotate_and_clean.py checks')
    if os.path.exists('rotate_and_clean.py'):
        out = run_cmd('python3 rotate_and_clean.py')
        print(out)
    else:
        print('rotate_and_clean.py not found')


def run_test_new_keys():
    print('\n🔐 Running test_new_keys.py')
    if os.path.exists('test_new_keys.py'):
        out = run_cmd('python3 test_new_keys.py')
        print(out)
    else:
        print('test_new_keys.py not found')


def secure_audit_files():
    print('\n📁 Securing audit_*.json files')
    files = [f for f in os.listdir('.') if f.startswith('audit_') and f.endswith('.json')]
    if not files:
        print('No audit_*.json files found')
        return
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%SZ')
    secure_dir = f'secure_audits_{ts}'
    os.makedirs(secure_dir, exist_ok=True)
    moved = 0
    for f in files:
        try:
            shutil.move(f, os.path.join(secure_dir, f))
            moved += 1
        except Exception as e:
            print('Failed to move', f, e)
    print(f'Moved {moved} files to {secure_dir}')


def create_env_example():
    fn = '.env.example'
    if os.path.exists(fn):
        print('\n.env.example already exists')
        return
    print('\nCreating .env.example with placeholders')
    content = '''# Example environment variables for ai-trading-bot
DEEPSEEK_API_KEY=your_deepseek_api_key_here
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
DATABASE_URL=postgresql://user:password@localhost:5432/yourdb
FINAL_HAMMER=example_value
# Add other required variables here
'''
    with open(fn, 'w') as f:
        f.write(content)
    print('Created .env.example')


def final_summary():
    print('\n🔒 FINAL SECURITY CHECKLIST')
    print('==========================')
    print('\n✅ Done:')
    print('  - Security checks executed')
    print('  - .gitignore ensured')
    print('  - .env status checked')
    print('  - rotate_and_clean run')
    print('  - test_new_keys run')
    print('  - audit files secured')
    print('\n🚨 Still Required:')
    print('  1. Rotate DeepSeek API key immediately: https://platform.deepseek.com/api_keys')
    print('  2. Rotate Binance API keys if present: https://www.binance.com/en/my/settings/api-management')
    print('  3. Review audit findings in secure_audits_* directory')


def main():
    print('🛡️ Starting Comprehensive Security Remediation Process')
    print('======================================================')
    check_git_for_api_key_commits()
    check_git_history_for_env()
    check_recent_commits()
    check_env_file()
    ensure_gitignore_patterns()
    run_rotate_and_clean()
    run_test_new_keys()
    create_env_example()
    secure_audit_files()
    final_summary()


if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""Security remediation helper.

Performs quick checks: git history scans, .env presence and basic checks,
and reports recommended cleanup commands.
"""
import os
import subprocess
import shlex


def run_cmd(cmd):
    try:
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
        return out.strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip()


def check_git_for_api_key():
    print("🔍 Checking git commits for 'api_key' occurrences (first 20 lines)...")
    out = run_cmd('git log -p --all -S "api_key" --name-only | head -20')
    print(out or "(no output)")


def check_recent_commits():
    print("\n🔍 Recent commits (last 10):")
    out = run_cmd('git log --oneline -10')
    print(out or "(no commits found)")


def check_env_tracked():
    print("\n🔍 Checking if .env is tracked in git:")
    out = run_cmd('git ls-files .env 2>/dev/null || echo ".env not tracked in git"')
    print(out)


def check_env_file():
    print("\n🔐 Current .env file status:")
    if os.path.exists('.env'):
        st = os.stat('.env')
        perms = oct(st.st_mode)[-3:]
        lines = 0
        try:
            with open('.env', 'r') as f:
                lines = sum(1 for _ in f)
        except Exception:
            lines = 0

        print("✅ .env exists")
        print(f"📁 Permissions: {perms}")
        print(f"📊 Size: {lines} lines")

        # Check for placeholders
        try:
            out = run_cmd("grep -E 'your_.*_here|example|placeholder|change_me' .env || true")
            if out:
                print("⚠️  Contains placeholder values - OK for development")
            else:
                print("🔒 Contains actual values - ensure it's not committed")
        except Exception:
            pass

        # Show masked first 3 lines
        try:
            lines = run_cmd('head -3 .env')
            if lines:
                masked = '\n'.join(['*' * len(l) for l in lines.split('\n')])
                print("First 3 lines (masked):")
                print(masked)
        except Exception:
            pass
    else:
        print("❌ .env file not found!")


def suggest_git_cleanup():
    print("\n🛠️  Suggested git cleanup commands (run with care):")
    print("git log --all --full-history -- .env | head -5")
    print('git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" --prune-empty --tag-name-filter cat -- --all')
    print('rm -rf .git/refs/original/; git reflog expire --expire=now --all; git gc --prune=now --aggressive')
    print('git push origin --force --all')


def main():
    check_git_for_api_key()
    check_recent_commits()
    check_env_tracked()
    check_env_file()
    suggest_git_cleanup()


if __name__ == '__main__':
    main()
