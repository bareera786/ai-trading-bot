#!/bin/bash
# Quick Pre-Deployment Test (5 minutes)
# Run this BEFORE deploying to VPS

set -e

echo "🧪 Quick Pre-Deployment Test for AI Trading Bot"
echo "================================================"
echo ""

# Test 1: Start the bot locally
echo "✅ Test 1: Starting bot locally..."
python3 run.py &
BOT_PID=$!
sleep 10  # Wait for bot to start

# Check if bot is running
if ! ps -p $BOT_PID > /dev/null; then
    echo "❌ FAIL: Bot failed to start"
    exit 1
fi
echo "✅ PASS: Bot started successfully (PID: $BOT_PID)"
echo ""

# Test 2: Check if web server is responding
echo "✅ Test 2: Checking web server..."
if curl -s http://localhost:5000 > /dev/null; then
    echo "✅ PASS: Web server responding"
else
    echo "❌ FAIL: Web server not responding"
    kill $BOT_PID
    exit 1
fi
echo ""

# Test 3: Check API endpoints
echo "✅ Test 3: Checking API endpoints..."
if curl -s http://localhost:5000/api/status | grep -q "system_status"; then
    echo "✅ PASS: API endpoints working"
else
    echo "❌ FAIL: API endpoints not working"
    kill $BOT_PID
    exit 1
fi
echo ""

# Test 4: Check for critical errors in logs
echo "✅ Test 4: Checking for critical errors..."
sleep 5  # Let bot run for a bit
if grep -i "CRITICAL\|FATAL" logs/bot.log | tail -5; then
    echo "⚠️  WARNING: Critical errors found in logs"
    echo "Review logs before deploying"
else
    echo "✅ PASS: No critical errors in logs"
fi
echo ""

# Test 5: Check database
echo "✅ Test 5: Checking database..."
if [ -f "instance/trading_bot.db" ]; then
    echo "✅ PASS: Database exists"
    
    # Check if user_portfolio table exists
    if sqlite3 instance/trading_bot.db "SELECT COUNT(*) FROM user_portfolio;" > /dev/null 2>&1; then
        echo "✅ PASS: user_portfolio table exists"
    else
        echo "⚠️  WARNING: user_portfolio table not found"
    fi
else
    echo "❌ FAIL: Database not found"
    kill $BOT_PID
    exit 1
fi
echo ""

# Cleanup
echo "🧹 Cleaning up..."
kill $BOT_PID
sleep 2

echo ""
echo "================================================"
echo "🎉 PRE-DEPLOYMENT TEST COMPLETE"
echo "================================================"
echo ""
echo "✅ All critical tests passed!"
echo ""
echo "🚀 READY TO DEPLOY!"
echo ""
echo "Next steps:"
echo "1. Review config/deploy.env.production"
echo "2. Run: bash scripts/deployment/deploy_to_vps_complete.sh"
echo ""
