import json
import os
from pathlib import Path

def summarize_audit_results(json_file="audit_app_runtime_context.json"):
    """Summarize DeepSeek audit findings in a readable format"""
    
    if not os.path.exists(json_file):
        print(f"❌ File not found: {json_file}")
        return
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    print("📊 AUDIT RESULTS SUMMARY")
    print("=" * 60)
    print(f"Module: {data.get('module', 'Unknown')}")
    print(f"Focus: {data.get('focus', 'Unknown')}")
    print(f"Timestamp: {data.get('timestamp', 'Unknown')}")
    print("\n" + "=" * 60)
    
    # AST Issues
    ast_issues = data.get('ast_issues', [])
    if ast_issues:
        print("🔍 STATIC ANALYSIS (AST) ISSUES:")
        for i, issue in enumerate(ast_issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ No static analysis issues found")
    
    # AI Analysis
    ai_analysis = data.get('ai_analysis', '')
    if ai_analysis and ai_analysis != "DRY_RUN_COMPLETE":
        print("\n🤖 DEEPSEEK AI ANALYSIS:")
        print("-" * 40)
        
        # Extract key sections
        lines = ai_analysis.split('\n')
        in_section = False
        current_section = ""
        
        for line in lines:
            line_stripped = line.strip()
            
            # Look for section headers
            if line_stripped.endswith(':') and not line_stripped.startswith('    '):
                current_section = line_stripped
                print(f"\n{current_section}")
                print("-" * len(current_section))
                in_section = True
            elif in_section and line_stripped:
                print(f"  • {line_stripped}")
            elif not line_stripped:
                in_section = False
        
        # If no clear sections, print the whole thing
        if "CRITICAL:" not in ai_analysis and "ISSUE:" not in ai_analysis:
            print("\nFull Analysis:")
            print("-" * 40)
            print(ai_analysis[:1000] + ("..." if len(ai_analysis) > 1000 else ""))
    else:
        print("\n⚠️ No AI analysis available or dry run mode")
    
    # Recommendations
    print("\n" + "=" * 60)
    print("🎯 RECOMMENDED ACTIONS:")
    print("-" * 40)
    
    if isinstance(ai_analysis, str) and "CRITICAL" in ai_analysis.upper():
        print("1. ⚠️  Address CRITICAL issues immediately")
        print("2. Review security findings before deployment")
        print("3. Create tests for fixed code")
    elif ast_issues:
        print("1. Fix static analysis issues (print statements, bare excepts)")
        print("2. Run full security audit on remaining modules")
        print("3. Generate tests for this module")
    else:
        print("1. ✅ Module appears clean - proceed to next module")
        print("2. Consider adding more comprehensive tests")
        print("3. Verify module integrates correctly with others")

def find_project_structure():
    """Discover the actual structure of your trading bot"""
    
    print("\n🔍 PROJECT STRUCTURE DISCOVERY")
    print("=" * 60)
    
    # Look for key directories
    key_dirs = ['app', 'core', 'strategies', 'tests', 'scripts', 'config']
    found_dirs = [d for d in key_dirs if os.path.exists(d)]
    
    print(f"Found directories: {', '.join(found_dirs) if found_dirs else 'None'}")
    
    # Look for critical files with different possible locations
    critical_files = {
        'risk_management': ['risk_management.py', 'core/risk.py', 'app/risk_management.py', 'strategies/risk.py'],
        'exchange_api': ['exchange_api.py', 'core/exchange.py', 'app/api/exchange.py', 'app/runtime/services.py'],
        'trading_engine': ['trading_bot.py', 'main.py', 'core/engine.py', 'app/trading.py'],
        'backtest': ['backtest.py', 'core/backtest.py', 'scripts/backtest.py']
    }
    
    for module, possible_paths in critical_files.items():
        found = None
        for path in possible_paths:
            if os.path.exists(path):
                found = path
                break
        
        if found:
            print(f"✅ {module}: {found}")
        else:
            print(f"❌ {module}: Not found (tried: {', '.join(possible_paths[:2])}...)")

if __name__ == "__main__":
    summarize_audit_results()
    find_project_structure()
    
    # Additional check for git history
    print("\n" + "=" * 60)
    print("🔐 GIT SECURITY CHECK")
    print("-" * 40)
    
    if os.path.exists('.env'):
        # Check if .env might be in git history
        result = os.popen('git log --all --full-history -- .env 2>/dev/null | head -5').read()
        if result:
            print("⚠️  .env file found in git history!")
            print("   Run: git filter-branch --force --index-filter \"")
            print("        git rm --cached --ignore-unmatch .env \"")
            print("        --prune-empty --tag-name-filter cat -- --all")
        else:
            print("✅ .env not found in recent git history")
    else:
        print("ℹ️  No .env file in current directory")
