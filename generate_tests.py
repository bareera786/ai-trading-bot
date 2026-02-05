#!/usr/bin/env python3
"""
Generate tests for critical trading bot modules
"""
import os
import ast
import re

def find_untested_modules():
    """Find Python modules without corresponding tests"""
    
    print("🔍 Finding untested modules...")
    
    # Get all Python files
    all_py_files = []
    for root, dirs, files in os.walk('.'):
        # Skip test directories and virtual envs
        if any(skip in root for skip in ['test', '.git', '.venv', '__pycache__']):
            continue
        
        for file in files:
            if file.endswith('.py') and not file.startswith('test_'):
                all_py_files.append(os.path.join(root, file))
    
    # Check for test files
    untested_modules = []
    for py_file in all_py_files:
        dir_name = os.path.dirname(py_file)
        file_name = os.path.basename(py_file)
        test_file = os.path.join(dir_name, f"test_{file_name}")
        
        if not os.path.exists(test_file):
            # Also check in tests/ directory
            test_file2 = os.path.join('tests', f"test_{file_name}")
            if not os.path.exists(test_file2):
                untested_modules.append(py_file)
    
    print(f"Found {len(untested_modules)} untested modules")
    return untested_modules

def analyze_module_for_test_cases(module_path):
    """Analyze a module to generate test cases"""
    
    try:
        with open(module_path, 'r') as f:
            content = f.read()
        
        # Parse AST to find functions and classes
        tree = ast.parse(content)
        
        test_cases = []
        
        for node in ast.walk(tree):
            # Find function definitions
            if isinstance(node, ast.FunctionDef):
                func_name = node.name
                if not func_name.startswith('_'):  # Skip private methods
                    test_cases.append({
                        'type': 'function',
                        'name': func_name,
                        'module': module_path
                    })
            
            # Find class definitions
            elif isinstance(node, ast.ClassDef):
                class_name = node.name
                test_cases.append({
                    'type': 'class',
                    'name': class_name,
                    'module': module_path
                })
        
        return test_cases
    
    except Exception as e:
        print(f"Error analyzing {module_path}: {e}")
        return []

def create_test_template(module_path, test_cases):
    """Create a test template for a module"""
    
    module_name = os.path.basename(module_path).replace('.py', '')
    test_file_name = f"test_{module_name}.py"
    
    # Import path
    rel_path = module_path[2:] if module_path.startswith('./') else module_path
    import_path = rel_path.replace('.py', '').replace('/', '.')
    
    template = f'''#!/usr/bin/env python3
"""
Tests for {module_name}
Generated from audit enhancement phase
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from {import_path} import *

# Fixtures
@pytest.fixture
def sample_data():
    """Sample data for testing"""
    return {{"test": "data"}}

# Test Cases
'''

    # Add test functions for each test case
    for i, test_case in enumerate(test_cases[:10]):  # Limit to 10 per file
        if test_case['type'] == 'function':
            template += f'''\ndef test_{test_case['name']}(sample_data):
    """Test {test_case['name']} function"""
    # TODO: Implement actual test
    # result = {test_case['name']}(...)
    # assert result is not None
    pass
'''
        elif test_case['type'] == 'class':
            template += f'''\nclass Test{test_case['name']}:
    """Test {test_case['name']} class"""
    
    def test_initialization(self, sample_data):
        """Test class initialization"""
        # obj = {test_case['name']}(...)
        # assert obj is not None
        pass
    
    def test_methods(self, sample_data):
        """Test class methods"""
        pass
'''
    
    # Add edge case tests
    template += f'''\n# Edge Cases
def test_edge_cases():
    """Test edge cases"""
    pass

# Integration Tests  
def test_integration():
    """Test integration with other modules"""
    pass

# Performance Tests
def test_performance():
    """Test performance characteristics"""
    pass

if __name__ == "__main__":
    pytest.main([__file__, "-v"])\n'''
    
    return test_file_name, template

def main():
    """Main function to generate tests"""
    
    print("🧪 Generating test suite for critical modules...")
    
    untested_modules = find_untested_modules()
    
    # Focus on critical modules first
    critical_keywords = ['risk', 'strategy', 'trading', 'exchange', 'bot', 'core']
    critical_modules = [
        m for m in untested_modules 
        if any(keyword in m.lower() for keyword in critical_keywords)
    ][:5]  # Limit to 5 modules
    
    print(f"\n🎯 Generating tests for {len(critical_modules)} critical modules:")
    
    for module in critical_modules:
        print(f"  • {module}")
    
    # Create tests directory if it doesn't exist
    os.makedirs("tests", exist_ok=True)
    
    # Generate test files
    generated_tests = []
    for module in critical_modules:
        test_cases = analyze_module_for_test_cases(module)
        if test_cases:
            test_file, template = create_test_template(module, test_cases)
            test_path = os.path.join("tests", test_file)
            
            with open(test_path, 'w') as f:
                f.write(template)
            
            generated_tests.append(test_path)
            print(f"✅ Created: {test_path} ({len(test_cases)} test cases)")
    
    # Create a test runner
    with open("run_tests.sh", "w") as f:
        f.write('''#!/bin/bash
echo "🧪 Running Generated Test Suite"
echo "==============================="

# Run pytest with coverage
python -m pytest tests/ -v --tb=short

# Generate coverage report
python -m pytest tests/ --cov=. --cov-report=html --cov-report=term

echo ""
echo "📊 Test Coverage Report generated in htmlcov/"
echo "📝 Review and implement TODO tests in test files"
''')
    
    os.chmod("run_tests.sh", 0o755)
    
    print(f"\n✅ Generated {len(generated_tests)} test files in tests/ directory")
    print("📝 Run tests with: ./run_tests.sh")
    print("💡 Remember to implement the TODO tests before production use")

if __name__ == "__main__":
    main()
