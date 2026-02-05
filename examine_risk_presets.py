import json
import os

def examine_specific_audit(file_path="audit__app_core_risk_presets_py.json"):
    """Examine a specific audit file in detail"""
    
    print(f"🔍 DETAILED ANALYSIS: {file_path}")
    print("=" * 80)
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        module = data.get('module', 'Unknown')
        ai_analysis = data.get('ai_analysis', '')
        ast_issues = data.get('ast_issues', [])
        
        print(f"Module: {module}")
        print(f"AST Issues: {len(ast_issues)}")
        if ast_issues:
            for issue in ast_issues:
                print(f"  • {issue}")
        
        print(f"\nAI Analysis (first 1000 chars):")
        print("-" * 60)
        if ai_analysis and ai_analysis != "DRY_RUN_COMPLETE":
            # Try to format it better
            lines = ai_analysis.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith(('CRITICAL:', 'HIGH:', 'MEDIUM:', 'RECOMMENDATION:', 'ISSUE:')):
                    print(f"\n{line}")
                elif line and not line.startswith('   '):
                    print(f"  {line}")
                elif line:
                    print(f"    {line}")
        else:
            print("No AI analysis available or dry run")
        
        return data
    
    except Exception as e:
        print(f"Error: {e}")
        return None

# Also check what the actual risk_presets.py file looks like
def preview_actual_file():
    """Preview the actual risk_presets.py file"""
    
    file_path = "app/core/risk_presets.py"
    if os.path.exists(file_path):
        print(f"\n📄 ACTUAL FILE PREVIEW: {file_path}")
        print("=" * 60)
        
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        print(f"Total lines: {len(lines)}")
        
        # Show first 30 lines
        for i, line in enumerate(lines[:30]):
            print(f"{i+1:3d}: {line.rstrip()}")
        
        # Check for potential issues
        print("\n🔍 POTENTIAL ISSUES FOUND:")
        for i, line in enumerate(lines):
            if 'print(' in line and '# DEBUG' not in line:
                print(f"  Line {i+1}: print() statement - use logging instead")
            if 'except:' in line or 'except Exception:' in line:
                print(f"  Line {i+1}: Broad exception - specify exception types")
            if 'api_key' in line.lower() or 'secret' in line.lower():
                print(f"  Line {i+1}: Possible credential reference")
    else:
        print(f"\n❌ File not found: {file_path}")

if __name__ == "__main__":
    examine_specific_audit()
    preview_actual_file()
