#!/bin/bash
# Local CI Checks Script for AI Trading Bot
# This script runs all the checks that would be performed in CI/CD

set -e  # Exit on any error

echo "🚀 Starting Local CI Checks for AI Trading Bot"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    print_error "requirements.txt not found. Are you in the project root?"
    exit 1
fi

echo "📋 Running CI Checks..."
echo

# 1. Python Version Check
echo "🐍 Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
if [[ "$python_version" =~ ^3\.(10|11|12) ]]; then
    print_status "Python version: $python_version"
else
    print_warning "Python version $python_version - recommended: 3.10+"
fi

# 2. Virtual Environment Check
echo "🔧 Checking virtual environment..."
if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_status "Virtual environment active: $VIRTUAL_ENV"
else
    print_warning "No virtual environment detected"
fi

# 3. Dependencies Check
echo "📦 Checking dependencies..."
python3 -c "
import sys
deps = ['flask', 'sqlalchemy', 'pandas', 'numpy', 'sklearn', 'requests']
missing = []
for dep in deps:
    try:
        __import__(dep)
        print(f'✅ {dep}')
    except ImportError:
        missing.append(dep)
        print(f'❌ {dep}')

if missing:
    print(f'Missing dependencies: {missing}')
    sys.exit(1)
else:
    print('✅ All core dependencies installed')
"

# 4. Syntax Check
echo "🔍 Running Python syntax checks..."
if python3 -m py_compile app/__init__.py; then
    print_status "App factory syntax OK"
else
    print_error "App factory syntax error"
    exit 1
fi

# Check main application file
if python3 -m py_compile ai_ml_auto_bot_final.py; then
    print_status "Main application syntax OK"
else
    print_error "Main application syntax error"
    exit 1
fi

# 5. Import Test
echo "🔗 Testing imports..."
python3 -c "
try:
    from app import create_app
    print('✅ App factory import OK')
except ImportError as e:
    print(f'❌ App factory import failed: {e}')
    exit(1)

try:
    from app.extensions import db
    print('✅ Extensions import OK')
except ImportError as e:
    print(f'❌ Extensions import failed: {e}')
    exit(1)

try:
    from app.models import User
    print('✅ Models import OK')
except ImportError as e:
    print(f'❌ Models import failed: {e}')
    exit(1)
"

# 6. Configuration Validation
echo "⚙️  Checking configuration..."
python3 -c "
import os
from app.config import Config

# Test config loading
try:
    config = Config()
    print('✅ Config class loads OK')
except Exception as e:
    print(f'❌ Config loading failed: {e}')
    exit(1)

# Check required environment variables have defaults
required_vars = ['SECRET_KEY', 'DATABASE_URL']
for var in required_vars:
    if hasattr(config, var) or var in os.environ:
        print(f'✅ {var} configured')
    else:
        print(f'⚠️  {var} not configured (using defaults)')
"

# 7. Database Migration Check
echo "🗄️  Checking database migrations..."
python3 -c "
try:
    from app.migrations import migrate_database
    print('✅ Migrations module imports OK')
except ImportError as e:
    print(f'❌ Migrations import failed: {e}')
    exit(1)
"

# 8. Test Suite
echo "🧪 Running test suite..."
# Run only unit tests, exclude integration tests that require a running server
if python3 -m pytest tests/ -v --tb=short --disable-warnings -x \
    --ignore=tests/test_toggle.py \
    --ignore=tests/test_strategy_apis.py \
    --ignore=tests/test_futures_toggle.py \
    --ignore=tests/test_tenant_isolation.py \
    --ignore=tests/test_futures_spot_trading.py \
    --ignore=tests/test_paper_trading.py; then
    print_status "All unit tests passed"
else
    print_error "Some unit tests failed"
    exit 1
fi

# 9. Code Quality Checks (if tools are available)
echo "🔍 Running code quality checks..."

# Check for flake8
if command -v flake8 &> /dev/null; then
    echo "Running flake8..."
    if flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
        print_status "Flake8 checks passed"
    else
        print_warning "Flake8 found some issues"
    fi
else
    print_warning "flake8 not installed - skipping linting"
fi

# Check for black formatting
if command -v black &> /dev/null; then
    echo "Checking code formatting with black..."
    if black --check --diff app/ --quiet; then
        print_status "Code formatting OK"
    else
        print_warning "Code formatting issues found. Run: black app/"
    fi
else
    print_warning "black not installed - skipping format check"
fi

# 10. Security Check
echo "🔒 Running basic security checks..."
python3 -c "
import os
import re

# Check for hardcoded secrets
secrets_pattern = re.compile(r'(?i)(api_key|secret|password|token).*[\'\"]([^\'\"]{10,})[\'\"]')
found_secrets = []

for root, dirs, files in os.walk('.'):
    # Skip virtual env and git
    if '.venv' in root or '.git' in root or 'node_modules' in root:
        continue

    for file in files:
        if file.endswith(('.py', '.js', '.json', '.env')):
            try:
                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    matches = secrets_pattern.findall(content)
                    if matches:
                        found_secrets.extend([(os.path.join(root, file), match) for match in matches])
            except:
                pass

if found_secrets:
    print('⚠️  Potential hardcoded secrets found:')
    for file_path, match in found_secrets[:5]:  # Show first 5
        print(f'   {file_path}: {match[0]}')
else:
    print('✅ No obvious hardcoded secrets found')
"

# 11. Build Check
echo "🏗️  Checking application build..."
python3 -c "
try:
    from app import create_app
    app = create_app()
    print('✅ Flask app creates successfully')
    print(f'   Routes registered: {len(app.url_map._rules)}')
except Exception as e:
    print(f'❌ App creation failed: {e}')
    exit(1)
"

# 12. Performance Check (basic)
echo "⚡ Running basic performance checks..."
python3 -c "
import time
from app import create_app

start_time = time.time()
app = create_app()
creation_time = time.time() - start_time

if creation_time < 5.0:  # Should create in under 5 seconds
    print(f'✅ App creation time: {creation_time:.2f}s')
else:
    print(f'⚠️  Slow app creation: {creation_time:.2f}s')
"

echo
echo "🎉 Local CI Checks Complete!"
echo "==========================="
print_status "All critical checks passed!"
echo
echo "📝 Summary:"
echo "   • Python environment: OK"
echo "   • Dependencies: OK"
echo "   • Syntax: OK"
echo "   • Imports: OK"
echo "   • Configuration: OK"
echo "   • Database: OK"
echo "   • Tests: OK"
echo "   • Security: OK"
echo "   • Build: OK"
echo
echo "🚀 Your AI Trading Bot is ready for deployment!"
