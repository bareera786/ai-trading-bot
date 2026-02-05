"""
g-bot
"""
import requests
import json
import os
import ast
import subprocess
from typing import List, Dict, Tuple
from pathlib import Path
import time


class TradingBotAuditor:
    def __init__(self, api_key: str, project_root: str = "."):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com"
        self.project_root = Path(project_root)
        
        # Models optimized for different audit tasks
        self.models = {
            "security": "deepseek-reasoner",
            "performance": "deepseek-coder", 
            "logic": "deepseek-reasoner",
            "testing": "deepseek-coder"
        }
        
        # Your bot's specific modules (from your README)
        self.critical_modules = [
            "app/runtime/context.py",
            "app/runtime/builder.py", 
            "app/runtime/system.py",
            "core/optimized_bot.py",
            "risk_management.py",
            "strategies/moving_average_cross.py",
            "strategies/rsi_divergence.py",
            "backtest.py",
            "exchange_api.py"
        ]
        
    def audit_module(self, module_path: str, focus: str = "security") -> Dict:
        """
        Audit a specific module from your trading bot
        Returns: {"issues": list, "suggestions": list, "patch": str}
        """
        full_path = self.project_root / module_path
        
        if not full_path.exists():
            return {"error": f"Module not found: {module_path}"}
        
        with open(full_path, 'r') as f:
            code = f.read()
        
        # Get AST analysis
        ast_issues = self._analyze_ast(code)
        
        # DeepSeek analysis based on focus
        prompt = self._create_audit_prompt(code, module_path, focus, ast_issues)
        ai_analysis = self._query_deepseek(prompt, model=self.models.get(focus, "deepseek-reasoner"))
        
        return {
            "module": module_path,
            "focus": focus,
            "ast_issues": ast_issues,
            "ai_analysis": ai_analysis,
            "timestamp": time.time()
        }
    
    def _create_audit_prompt(self, code: str, module_path: str, focus: str, ast_issues: List) -> str:
        """Create specialized audit prompts for your trading bot"""
        
        focus_prompts = {
            "security": """
            Analyze for SECURITY issues in this trading bot module:
            1. API key exposure or improper storage
            2. Insufficient error handling that could leak sensitive info
            3. Missing authentication/authorization checks
            4. SQL injection or other injection vulnerabilities
            5. Insecure API communications
            
            Module: {module}
            
            Return format:
            CRITICAL: [list critical security issues with line numbers]
            HIGH: [list high-risk issues]
            MEDIUM: [list medium-risk issues]
            PATCH: [provide corrected code snippets]
            """,
            
            "performance": """
            Analyze for PERFORMANCE bottlenecks in this trading bot:
            1. Inefficient loops or nested operations on large datasets
            2. Unnecessary database queries or API calls
            3. Memory leaks or inefficient data structures
            4. Parallel processing issues (joblib/threading)
            5. I/O bottlenecks in data fetching/caching
            
            Module: {module}
            
            Return format:
            BOTTLENECK: [describe performance issue with metrics]
            OPTIMIZATION: [suggest specific optimizations]
            CODE: [provide optimized code]
            """,
            
            "logic": """
            Analyze TRADING LOGIC correctness:
            1. Mathematical errors in indicator calculations
            2. Flaws in entry/exit conditions
            3. Risk management logic errors
            4. Edge cases in market data handling
            5. Ensemble prediction voting issues
            
            Module: {module}
            
            Return format:
            LOGIC_ERROR: [describe logical error]
            IMPACT: [potential financial impact]
            CORRECTION: [corrected logic]
            TEST_CASE: [test to verify fix]
            """,
            
            "testing": """
            Generate COMPREHENSIVE TESTS for this trading module:
            1. Unit tests for all public functions
            2. Integration tests for API interactions
            3. Mock tests for external dependencies (Binance API)
            4. Edge case tests for market extremes
            5. Performance benchmark tests
            
            Module: {module}
            
            Return ONLY pytest-compatible test code.
            """
        }
        
        prompt_template = focus_prompts.get(focus, focus_prompts["security"])
        return prompt_template.format(module=module_path) + f"\n\nCode:\n```python\n{code}\n```"
    
    def run_comprehensive_audit(self) -> Dict:
        """
        Run full audit on all critical modules
        Returns consolidated report
        """
        print("🔍 Starting comprehensive audit of AI Trading Bot...")
        print(f"📁 Project root: {self.project_root}")
        
        audit_report = {
            "project": "ai-trading-bot",
            "audit_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "modules_audited": [],
            "critical_issues": [],
            "performance_issues": [],
            "security_issues": [],
            "test_coverage": {}
        }
        
        for module in self.critical_modules:
            print(f"\n📊 Auditing: {module}")
            
            # Security audit
            security_result = self.audit_module(module, "security")
            audit_report["security_issues"].append(security_result)
            
            # Performance audit  
            perf_result = self.audit_module(module, "performance")
            audit_report["performance_issues"].append(perf_result)
            
            # Logic audit
            logic_result = self.audit_module(module, "logic")
            audit_report["critical_issues"].append(logic_result)
            
            audit_report["modules_audited"].append(module)
            
            # Rate limiting
            time.sleep(2)
        
        return audit_report
    
    def generate_test_suite(self, module_path: str) -> str:
        """Generate pytest suite for a module"""
        with open(self.project_root / module_path, 'r') as f:
            code = f.read()
        
        prompt = f"""
        Generate comprehensive pytest tests for this trading bot module.
        
        Module: {module_path}
        
        Requirements:
        1. Test ALL public functions
        2. Mock Binance API responses
        3. Test edge cases (market crashes, API failures)
        4. Include performance benchmarks
        5. Test risk management logic
        
        Return ONLY the test code in a single pytest file.
        
        Code to test:
        ```python
        {code}
        ```
        """
        
        return self._query_deepseek(prompt, model="deepseek-coder")
    
    def fix_specific_issue(self, module_path: str, issue_description: str) -> Dict:
        """
        Generate fix for a specific issue
        """
        with open(self.project_root / module_path, 'r') as f:
            code = f.read()
        
        prompt = f"""
        Fix this specific issue in the trading bot:
        
        Module: {module_path}
        Issue: {issue_description}
        
        Requirements:
        1. Provide COMPLETE fixed code (not just patch)
        2. Include explanation of the fix
        3. Add relevant tests
        4. Ensure backward compatibility
        
        Original Code:
        ```python
        {code}
        ```
        """
        
        fixed_code = self._query_deepseek(prompt, model="deepseek-coder")
        
        return {
            "module": module_path,
            "issue": issue_description,
            "fixed_code": fixed_code,
            "backup_path": f"{module_path}.backup_{int(time.time())}"
        }
    
    def _analyze_ast(self, code: str) -> List:
        """Static analysis using AST"""
        issues = []
        
        try:
            tree = ast.parse(code)
            
            # Check for common issues
            for node in ast.walk(tree):
                # Check for print() calls (logging issue) — AST.Print is Python2-only
                if isinstance(node, ast.Call):
                    func = getattr(node, 'func', None)
                    if isinstance(func, ast.Name) and getattr(func, 'id', None) == 'print':
                        lineno = getattr(node, 'lineno', 'unknown')
                        issues.append(f"Line {lineno}: print() statement found - use proper logging")
                
                # Check for hardcoded credentials
                if isinstance(node, ast.Constant):
                    if isinstance(node.value, str) and ("api_key" in node.value.lower() or "secret" in node.value.lower()):
                        issues.append(f"Line {node.lineno}: Possible hardcoded credential pattern")
                
                # Check for broad exceptions
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:  # bare except
                        issues.append(f"Line {node.lineno}: Bare except clause - specify exception types")
        
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        
        return issues
    
    def _query_deepseek(self, prompt: str, model: str = "deepseek-reasoner") -> str:
        """Query DeepSeek API"""
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 4000
            }
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"API Error: {response.status_code} - {response.text}"
    
    def save_report(self, report: Dict, filename: str = "audit_report.json"):
        """Save audit report"""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"✅ Report saved to: {filename}")


# Main runner for your existing project
def main():
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ Set DEEPSEEK_API_KEY in .env file")
        return
    
    # Initialize with YOUR project
    project_root = input("Enter path to your ai-trading-bot project: ").strip() or ".."
    
    auditor = TradingBotAuditor(api_key, project_root)
    
    print("\n🔧 Trading Bot Auditor - Enhancement Phase")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. 🔍 Run comprehensive audit (all modules)")
        print("2. 🧪 Generate test suite for module")
        print("3. 🐛 Fix specific issue in module")
        print("4. 📊 Audit single module")
        print("5. 💾 Save current report")
        print("6. 🚪 Exit")
        
        choice = input("\nSelect (1-6): ")
        
        if choice == "1":
            print("Running full audit... (this may take 5-10 minutes)")
            report = auditor.run_comprehensive_audit()
            auditor.save_report(report, "full_audit_report.json")
            
        elif choice == "2":
            module = input("Module path (e.g., risk_management.py): ")
            tests = auditor.generate_test_suite(module)
            test_file = f"test_{os.path.basename(module)}"
            with open(test_file, 'w') as f:
                f.write(tests)
            print(f"✅ Tests saved to: {test_file}")
            
        elif choice == "3":
            module = input("Module to fix: ")
            issue = input("Issue description: ")
            result = auditor.fix_specific_issue(module, issue)
            
            # Create backup
            import shutil
            shutil.copy2(module, result["backup_path"])
            
            # Write fix
            with open(module, 'w') as f:
                f.write(result["fixed_code"])
            
            print(f"✅ Fixed! Backup at: {result['backup_path']}")
            
        elif choice == "4":
            module = input("Module to audit: ")
            focus = input("Focus (security/performance/logic): ") or "security"
            result = auditor.audit_module(module, focus)
            print(json.dumps(result, indent=2))
            
        elif choice == "5":
            filename = input("Report filename: ") or "audit_report.json"
            auditor.save_report({}, filename)  # You'd need to have a report object
            
        elif choice == "6":
            print("👋 Goodbye!")
            break

if __name__ == "__main__":
    main()
