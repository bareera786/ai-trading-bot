import os
import json
from dotenv import load_dotenv
from audit_agent import TradingBotAuditor

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not API_KEY:
    print("❌ Set DEEPSEEK_API_KEY in .env file")
    exit(1)

# Focus on 2-3 critical modules to start
CRITICAL_MODULES = [
    "risk_management.py",        # Highest priority
    "exchange_api.py",           # API integration
    "app/runtime/context.py",    # Core runtime
]

auditor = TradingBotAuditor(API_KEY, ".")

print("🎯 FOCUSED AUDIT - Critical Modules Only")
print("=" * 50)

results = []
for module in CRITICAL_MODULES:
    if os.path.exists(module):
        print(f"\n🔍 Auditing: {module}")
        
        # Security audit
        print("  🔒 Security check...")
        sec_result = auditor.audit_module(module, "security")
        
        # Performance audit
        print("  ⚡ Performance check...")
        perf_result = auditor.audit_module(module, "performance")
        
        # Logic audit
        print("  🧠 Logic check...")
        logic_result = auditor.audit_module(module, "logic")
        
        results.append({
            "module": module,
            "security": sec_result,
            "performance": perf_result,
            "logic": logic_result
        })
        
        # Save intermediate results
        out_name = f"audit_{module.replace('/', '_').replace('.py', '')}.json"
        with open(out_name, 'w') as f:
            json.dump(results[-1], f, indent=2)
        
        print(f"  ✅ Saved to: {out_name}")
    else:
        print(f"\n⚠️  Module not found: {module}")

# Generate summary
print("\n" + "=" * 50)
print("📊 AUDIT SUMMARY")
print("=" * 50)

for result in results:
    module = result["module"]
    has_issues = False
    
    # Check if any issues found (very rudimentary check)
    for category in ["security", "performance", "logic"]:
        analysis = result.get(category, {})
        ai_analysis = analysis.get("ai_analysis", "")
        if isinstance(ai_analysis, str) and ("CRITICAL" in ai_analysis or "ERROR" in ai_analysis or "ISSUE" in ai_analysis):
            has_issues = True
            break
    
    status = "❌ ISSUES FOUND" if has_issues else "✅ CLEAN"
    print(f"{status} - {module}")

print("\n📝 Next steps:")
print("1. Review individual audit_*.json files")
print("2. Prioritize security issues first")
print("3. Run tests after applying fixes")
print("4. Back up original files before changes")
