#!/bin/bash
echo "🧪 Running Generated Test Suite"
echo "==============================="

# Run pytest with coverage
python -m pytest tests/ -v --tb=short

# Generate coverage report
python -m pytest tests/ --cov=. --cov-report=html --cov-report=term

echo ""
echo "📊 Test Coverage Report generated in htmlcov/"
echo "📝 Review and implement TODO tests in test files"
