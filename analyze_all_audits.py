import json
import os
import glob
from collections import defaultdict

def analyze_audit_files():
    """Analyze all audit JSON files and extract key findings"""
    
    audit_files = glob.glob("audit_*.json")
    if not audit_files:
        print("❌ No audit files found")
        return None
    
    print("🔍 ANALYZING ALL AUDIT RESULTS")
    print("=" * 80)
    
    summary = {
        "total_modules": 0,
        "modules_with_issues": 0,
        "critical_issues": [],
        "performance_issues": [],
        "security_issues": [],
        "by_module": {}
    }
    
    for audit_file in audit_files:
        try:
            with open(audit_file, 'r') as f:
                data = json.load(f)
            
            module = data.get('module', audit_file.replace('audit_', '').replace('.json', ''))
            ai_analysis = data.get('ai_analysis', '')
            ast_issues = data.get('ast_issues', [])
            
            summary["total_modules"] += 1
            summary["by_module"][module] = {
                "file": audit_file,
                "has_ai_analysis": bool(ai_analysis and ai_analysis != "DRY_RUN_COMPLETE"),
                "ast_issue_count": len(ast_issues),
                "analysis_preview": ai_analysis[:500] if ai_analysis else ""
            }
            
            # Parse AI analysis for critical keywords
            if ai_analysis and ai_analysis != "DRY_RUN_COMPLETE":
                ai_lower = ai_analysis.lower()
                
                # Check for critical issues
                if any(keyword in ai_lower for keyword in ['critical', 'vulnerability', 'security risk', 'exposed', 'insecure']):
                    summary["modules_with_issues"] += 1
                    summary["critical_issues"].append({
                        "module": module,
                        "file": audit_file,
                        "keyword": "CRITICAL"
                    })
                
                # Check for performance issues
                if any(keyword in ai_lower for keyword in ['performance', 'bottleneck', 'slow', 'inefficient', 'memory', 'optimization']):
                    summary["performance_issues"].append({
                        "module": module,
                        "file": audit_file,
                        "keyword": "PERFORMANCE"
                    })
                
                # Check for security issues
                if any(keyword in ai_lower for keyword in ['security', 'vulnerability', 'risk', 'exposure', 'leak']):
                    summary["security_issues"].append({
                        "module": module,
                        "file": audit_file,
                        "keyword": "SECURITY"
                    })
            
            # Count AST issues
            if ast_issues:
                summary["modules_with_issues"] += 1
        
        except Exception as e:
            print(f"❌ Error reading {audit_file}: {e}")
    
    return summary

def generate_action_plan(summary):
    """Generate actionable plan based on audit results"""
    
    if not summary:
        print("No summary available")
        return
    
    print("\n📋 AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total modules audited: {summary['total_modules']}")
    print(f"Modules with issues: {summary['modules_with_issues']}")
    
    if summary['critical_issues']:
        print(f"\n🔴 CRITICAL ISSUES: {len(summary['critical_issues'])}")
        for issue in summary['critical_issues']:
            print(f"  • {issue['module']} - {issue['file']}")
    
    if summary['security_issues']:
        print(f"\n🟡 SECURITY ISSUES: {len(summary['security_issues'])}")
        for issue in summary['security_issues'][:5]:  # Show first 5
            print(f"  • {issue['module']}")
    
    if summary['performance_issues']:
        print(f"\n🟢 PERFORMANCE ISSUES: {len(summary['performance_issues'])}")
        for issue in summary['performance_issues'][:5]:  # Show first 5
            print(f"  • {issue['module']}")
    
    print("\n" + "=" * 80)
    print("🎯 PRIORITIZED ACTION PLAN")
    print("=" * 80)
    
    # Priority 1: Critical issues
    if summary['critical_issues']:
        print("\n1. 🔴 IMMEDIATE ACTION - CRITICAL ISSUES:")
        print("   " + "-" * 40)
        for issue in summary['critical_issues']:
            print(f"   • Fix {issue['module']}")
            print(f"     Review: {issue['file']}")
            print("     Action: Address before any deployment")
    
    # Priority 2: Security issues (non-critical)
    if summary['security_issues']:
        print("\n2. 🟡 HIGH PRIORITY - SECURITY ISSUES:")
        print("   " + "-" * 40)
        security_modules = list(set([i['module'] for i in summary['security_issues'] if i not in summary['critical_issues']]))
        for module in security_modules[:3]:  # Top 3
            print(f"   • Review {module} for security improvements")
    
    # Priority 3: Performance issues
    if summary['performance_issues']:
        print("\n3. 🟢 MEDIUM PRIORITY - PERFORMANCE:")
        print("   " + "-" * 40)
        perf_modules = list(set([i['module'] for i in summary['performance_issues']]))
        for module in perf_modules[:3]:  # Top 3
            print(f"   • Optimize {module} for better performance")
    
    # Priority 4: Modules with AST issues
    modules_with_ast = [m for m, data in summary['by_module'].items() if data['ast_issue_count'] > 0]
    if modules_with_ast:
        print("\n4. ⚪ CODE QUALITY - AST ISSUES:")
        print("   " + "-" * 40)
        for module in modules_with_ast[:3]:
            print(f"   • Clean up {module} (AST found {summary['by_module'][module]['ast_issue_count']} issues)")
    
    # Priority 5: Modules without AI analysis
    modules_no_ai = [m for m, data in summary['by_module'].items() if not data['has_ai_analysis']]
    if modules_no_ai:
        print("\n5. ℹ️  CHECK NEEDED - NO AI ANALYSIS:")
        print("   " + "-" * 40)
        for module in modules_no_ai[:3]:
            print(f"   • Re-audit {module} (analysis missing or incomplete)")

def extract_specific_recommendations():
    """Extract specific recommendations from audit files"""
    
    print("\n" + "=" * 80)
    print("🔍 SPECIFIC RECOMMENDATIONS EXTRACTION")
    print("=" * 80)
    
    # Let's look at the most critical audit files first
    priority_order = [
        "audit__app_core_risk_presets_py.json",
        "audit__app_domain_trading_risk_py.json", 
        "audit__app_services_portfolio_risk_service_py.json",
        "audit__app_risk_stop_loss_py.json",
        "audit__app_risk_manager_py.json"
    ]
    
    for audit_file in priority_order:
        if os.path.exists(audit_file):
            try:
                with open(audit_file, 'r') as f:
                    data = json.load(f)
                
                module = data.get('module', 'Unknown')
                ai_analysis = data.get('ai_analysis', '')
                
                if ai_analysis and ai_analysis != "DRY_RUN_COMPLETE":
                    print(f"\n📄 {module} ({audit_file})")
                    print("-" * 60)
                    
                    # Extract key sections
                    lines = ai_analysis.split('\n')
                    recommendations = []
                    
                    for i, line in enumerate(lines):
                        line_lower = line.lower()
                        if any(keyword in line_lower for keyword in [
                            'recommend', 'suggest', 'should', 'consider', 
                            'improve', 'fix', 'issue', 'problem', 'critical'
                        ]):
                            # Get context (current line + next 2 lines)
                            context = lines[i:i+3]
                            recommendations.append(' '.join(context))
                    
                    # Show top 3 recommendations
                    if recommendations:
                        for j, rec in enumerate(recommendations[:3], 1):
                            print(f"   {j}. {rec[:200]}...")
                    else:
                        print("   No specific recommendations found in analysis")
            
            except Exception as e:
                print(f"❌ Error reading {audit_file}: {e}")

def check_for_hardcoded_secrets_in_audits():
    """Check audit results for mentions of secrets/credentials"""
    
    print("\n" + "=" * 80)
    print("🔐 SECRETS CHECK IN AUDIT RESULTS")
    print("=" * 80)
    
    secret_keywords = ['key', 'secret', 'password', 'token', 'credential', 'api']
    
    for audit_file in glob.glob("audit_*.json"):
        try:
            with open(audit_file, 'r') as f:
                data = json.load(f)
            
            ai_analysis = data.get('ai_analysis', '')
            if ai_analysis and any(keyword in ai_analysis.lower() for keyword in secret_keywords):
                module = data.get('module', 'Unknown')
                print(f"\n⚠️  {module} may have credential issues:")
                print(f"   File: {audit_file}")
                
                # Extract relevant lines
                lines = ai_analysis.split('\n')
                for line in lines:
                    if any(keyword in line.lower() for keyword in secret_keywords):
                        print(f"   • {line[:150]}")
        
        except Exception:
            pass

if __name__ == "__main__":
    # Step 1: Analyze all audit files
    summary = analyze_audit_files()
    
    # Step 2: Generate action plan
    generate_action_plan(summary)
    
    # Step 3: Extract specific recommendations
    extract_specific_recommendations()
    
    # Step 4: Check for secrets
    check_for_hardcoded_secrets_in_audits()
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review the prioritized action plan above")
    print("2. Check specific module recommendations")
    print("3. Address critical issues immediately")
    print("4. Run security audit on mentioned modules")
