import json
import os

def create_custom_audit_config():
    """Create audit config based on your actual project structure"""
    
    # First, discover what we have
    discovered_files = []
    for root, dirs, files in os.walk('.'):
        if '.git' in root or '.venv' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                discovered_files.append(path)
    
    # Map keywords to likely important files
    importance_keywords = {
        'risk': 10,
        'security': 9,
        'auth': 8,
        'api': 7,
        'exchange': 7,
        'trade': 6,
        'strategy': 5,
        'core': 5,
        'main': 4,
        'bot': 4
    }
    
    scored_files = []
    for file in discovered_files:
        score = 0
        file_lower = file.lower()
        for keyword, points in importance_keywords.items():
            if keyword in file_lower:
                score += points
        
        # Adjust score by location
        if 'app/runtime' in file:
            score += 3
        if 'core/' in file:
            score += 2
        if 'test' in file_lower:
            score = 0  # Tests are less critical for security audit
        
        if score > 0:
            scored_files.append((score, file))
    
    # Sort by score
    scored_files.sort(reverse=True)
    
    # Create new audit config
    config = {
        "project_name": "ai-trading-bot",
        "audit_priority": []
    }
    
    print("🎯 UPDATED AUDIT PRIORITY LIST:")
    print("=" * 60)
    
    for i, (score, file) in enumerate(scored_files[:15], 1):
        config["audit_priority"].append({
            "rank": i,
            "file": file,
            "score": score
        })
        print(f"{i:2d}. {file} (score: {score})")
    
    # Save config
    with open("audit_config.json", "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Saved to audit_config.json")
    
    # Create a new focused audit script
    create_focused_audit_script([f for _, f in scored_files[:8]])

def create_focused_audit_script(top_files):
    """Create a new audit script targeting your actual files"""
    
    script = '''#!/usr/bin/env python3
"""
Updated audit script for YOUR project structure
"""
import os
import json
from dotenv import load_dotenv
from audit_agent import TradingBotAuditor

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    print("❌ Set DEEPSEEK_API_KEY in .env file")
    exit(1)

# YOUR ACTUAL CRITICAL FILES (auto-discovered)
CRITICAL_MODULES = [
'''
    for file in top_files:
        script += f'    "{file}",\n'
    
    script += ''']

auditor = TradingBotAuditor(API_KEY, ".")

print("🎯 UPDATED AUDIT - Your Actual Structure")
print("=" * 60)

results = []
for module in CRITICAL_MODULES:
    if os.path.exists(module):
        print(f"\n🔍 Auditing: {module}")
        
        # Security audit (most important)
        print("  🔒 Security check...")
        sec_result = auditor.audit_module(module, "security")
        
        # Save immediately after each module (in case of failures)
        module_safe = module.replace("/", "_").replace(".", "_")
        with open(f"audit_{module_safe}.json", "w") as f:
            json.dump(sec_result, f, indent=2)
        
        print(f"  💾 Saved security audit")
        
        # Only do performance if security was clean
        if "CRITICAL" not in sec_result.get("ai_analysis", ""):
            print("  ⚡ Performance check...")
            perf_result = auditor.audit_module(module, "performance")
            results.append({"module": module, "performance": perf_result})
        else:
            print("  ⏭️  Skipping performance (security issues found)")
        
        results.append({"module": module, "security": sec_result})
    else:
        print(f"\n⚠️  Module not found: {module}")

# Summary
print("\n" + "=" * 60)
print("📊 AUDIT COMPLETE - See individual audit_*.json files")
print("=" * 60)

for result in results:
    module = result.get("module", "unknown")
    sec_analysis = result.get("security", {}).get("ai_analysis", "")
    
    if "CRITICAL" in sec_analysis:
        print(f"❌ {module} - SECURITY ISSUES FOUND")
    elif sec_analysis:
        print(f"✅ {module} - Security audit clean")
    else:
        print(f"⚠️  {module} - No analysis available")
'''
    
    with open("audit_actual_structure.py", "w") as f:
        f.write(script)
    
    os.chmod("audit_actual_structure.py", 0o755)
    print(f"\n📝 Created: audit_actual_structure.py")
    print("Run with: python3 audit_actual_structure.py")

if __name__ == "__main__":
    create_custom_audit_config()
