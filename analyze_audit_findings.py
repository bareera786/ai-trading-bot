#!/usr/bin/env python3
"""
Analyze audit findings and create actionable tasks
"""
import json
import os
import glob
from collections import defaultdict

def analyze_all_findings():
    """Analyze all audit JSON files and create prioritized fixes"""
    
    print("🔍 ANALYZING AUDIT FINDINGS FOR ACTION")
    print("=" * 80)
    
    # Find all audit files
    audit_dirs = glob.glob("secure_audits_*")
    if not audit_dirs:
        print("❌ No audit directories found")
        return
    
    audit_dir = sorted(audit_dirs)[-1]  # Use latest
    audit_files = glob.glob(f"{audit_dir}/*.json")
    
    if not audit_files:
        print(f"❌ No audit files in {audit_dir}")
        return
    
    print(f"📊 Found {len(audit_files)} audit files")
    
    # Categorize findings
    categories = {
        "CRITICAL": [],
        "HIGH": [],
        "MEDIUM": [],
        "PERFORMANCE": [],
        "CODE_QUALITY": []
    }
    
    for audit_file in audit_files:
        try:
            with open(audit_file, 'r') as f:
                data = json.load(f)
            
            module = data.get('module', 'Unknown')
            ai_analysis = data.get('ai_analysis', '')
            
            if not ai_analysis or ai_analysis == "DRY_RUN_COMPLETE":
                continue
            
            # Categorize based on content
            ai_lower = ai_analysis.lower()
            
            if any(word in ai_lower for word in ['critical', 'security risk', 'vulnerability', 'exposed']):
                categories["CRITICAL"].append({
                    'module': module,
                    'file': audit_file,
                    'excerpt': ai_analysis[:200] + "..."
                })
            elif any(word in ai_lower for word in ['high priority', 'important', 'should fix', 'must fix']):
                categories["HIGH"].append({
                    'module': module,
                    'file': audit_file,
                    'excerpt': ai_analysis[:200] + "..."
                })
            elif any(word in ai_lower for word in ['performance', 'slow', 'bottleneck', 'optimize']):
                categories["PERFORMANCE"].append({
                    'module': module,
                    'file': audit_file,
                    'excerpt': ai_analysis[:200] + "..."
                })
            else:
                categories["MEDIUM"].append({
                    'module': module,
                    'file': audit_file,
                    'excerpt': ai_analysis[:200] + "..."
                })
        
        except Exception as e:
            print(f"⚠️ Error reading {audit_file}: {e}")
    
    # Generate actionable report
    print("\n📋 PRIORITIZED FIXES:")
    print("=" * 80)
    
    total_issues = sum(len(issues) for issues in categories.values())
    print(f"Total issues found: {total_issues}")
    
    for priority, issues in categories.items():
        if issues:
            print(f"\n🔴 {priority} PRIORITY ({len(issues)} issues):")
            for issue in issues[:5]:  # Show top 5 per category
                print(f"   • {issue['module']}")
                print(f"     {issue['excerpt']}")
    
    # Create action plan
    print("\n" + "=" * 80)
    print("🎯 ACTION PLAN FOR NEXT 7 DAYS:")
    print("=" * 80)
    
    if categories["CRITICAL"]:
        print("\n📅 DAY 1-2: CRITICAL ISSUES")
        for issue in categories["CRITICAL"][:3]:
            print(f"   Fix: {issue['module']}")
    
    if categories["HIGH"]:
        print("\n📅 DAY 3-4: HIGH PRIORITY")
        for issue in categories["HIGH"][:3]:
            print(f"   Fix: {issue['module']}")
    
    if categories["PERFORMANCE"]:
        print("\n📅 DAY 5: PERFORMANCE")
        for issue in categories["PERFORMANCE"][:2]:
            print(f"   Optimize: {issue['module']}")
    
    print("\n📅 DAY 6-7: TESTING & VALIDATION")
    print("   • Run full test suite")
    print("   • Backtest strategies")
    print("   • Deploy to test environment")
    
    # Save to file
    with open("enhancement_plan.md", "w") as f:
        f.write("# Trading Bot Enhancement Plan\n\n")
        f.write(f"Total issues identified: {total_issues}\n\n")
        
        for priority, issues in categories.items():
            if issues:
                f.write(f"## {priority} Priority ({len(issues)} issues)\n\n")
                for issue in issues:
                    f.write(f"- **{issue['module']}**: {issue['excerpt']}\n")
                f.write("\n")
    
    print(f"\n✅ Enhancement plan saved to: enhancement_plan.md")

if __name__ == "__main__":
    analyze_all_findings()
