#!/bin/bash
# VPS Cleanup Verification Script

echo "🔍 VPS CLEANUP VERIFICATION"
echo "==========================="
echo ""

# Check if we can connect
echo "Testing SSH connections..."
ssh -o ConnectTimeout=5 aibot@151.243.171.80 "echo '✅ aibot SSH: OK'" 2>/dev/null || echo "❌ aibot SSH: FAILED"
ssh -o ConnectTimeout=5 root@151.243.171.80 "echo '✅ root SSH: OK'" 2>/dev/null || echo "❌ root SSH: FAILED"
echo ""

# Check if old files are gone
echo "Checking aibot user directory..."
ssh aibot@151.243.171.80 "ls -la /home/aibot/ | grep -E '(ai-ml-auto-bot|trading_bot|\.db$)' || echo '✅ No old bot files found'" 2>/dev/null
ssh aibot@151.243.171.80 "if [ -d '/home/aibot/ai-bot' ]; then echo '✅ Fresh ai-bot directory exists'; else echo '❌ ai-bot directory missing'; fi" 2>/dev/null
echo ""

# Check running processes
echo "Checking for running bot processes..."
ssh root@151.243.171.80 "ps aux | grep -E '(flask|gunicorn|ai-ml-auto-bot|ai_trading_bot)' | grep -v grep || echo '✅ No bot processes running'" 2>/dev/null
echo ""

echo "🎯 If all checks show ✅, you're ready for deployment!"
echo "🚀 Run: ./deploy_to_vps_complete.sh"