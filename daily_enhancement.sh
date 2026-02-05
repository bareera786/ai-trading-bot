#!/bin/bash

echo "🚀 Daily Enhancement Routine for Trading Bot"
echo "=========================================="
echo "Date: $(date)"
echo ""

# Step 1: Run tests
echo "1. Running test suite..."
if [ -f "./run_tests.sh" ]; then
    ./run_tests.sh 2>&1 | tail -20
else
    echo "   ⚠️  Test runner not found"
fi
echo ""

# Step 2: Check performance
echo "2. Checking performance..."
if [ -f "performance_monitor.py" ]; then
    python3 -c "
from performance_monitor import TradingBotMonitor
m = TradingBotMonitor()
report = m.generate_performance_report()
print(f'   Trades: {report["trade_count"]}')
print(f'   Success rate: {report["success_rate"]*100:.1f}%')
print(f'   Slow operations: {len(report["slow_operations"])}')
for rec in report['recommendations'][:3]:
    print(f'   ⚠️  {rec}')
" 2>/dev/null || echo "   ⚠️  Performance monitor not configured"
else
    echo "   ⚠️  Performance monitor not found"
fi
echo ""

# Step 3: Check audit findings
echo "3. Reviewing audit findings..."
find secure_audits_* -name "*.json" 2>/dev/null | head -3 | while read file; do
    echo "   📄 $(basename $file)"
done
echo "   💡 Run: python3 analyze_audit_findings.py for details"
echo ""

# Step 4: Update enhancement progress
echo "4. Updating enhancement progress..."
completed=$(grep -c "\[x\]" enhancement_checklist.md 2>/dev/null || echo "0")
total=$(grep -c "\[[ x]\]" enhancement_checklist.md 2>/dev/null || echo "0")
if [ "$total" -gt 0 ]; then
    progress=$((completed * 100 / total))
    echo "   Progress: $progress% ($completed/$total tasks)"
    
    # Update checklist date
    sed -i '' "s/Last Updated: .*/Last Updated: $(date +'%Y-%m-%d %H:%M:%S')/" enhancement_checklist.md 2>/dev/null
else
    echo "   ⚠️  Checklist not found"
fi
echo ""

# Step 5: Git status
echo "5. Checking git status..."
git status --short 2>/dev/null | head -5 || echo "   Not a git repository or no changes"
echo ""

echo "✅ Daily enhancement routine complete!"
echo "📊 Next: Focus on high-priority audit findings"
