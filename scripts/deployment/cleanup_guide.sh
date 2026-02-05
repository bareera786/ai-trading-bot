#!/bin/bash
# Interactive VPS Cleanup Guide
# This script provides step-by-step commands for manual cleanup

echo "🤖 AI TRADING BOT - COMPLETE VPS CLEANUP GUIDE"
echo "==============================================="
echo ""
echo "⚠️  IMPORTANT: You need to run these commands MANUALLY on your VPS"
echo "   because I cannot access your VPS directly (no passwords stored)"
echo ""
echo "📋 CLEANUP STEPS:"
echo ""

# Step 1: Root cleanup
echo "🔴 STEP 1: CLEAN AS ROOT USER"
echo "-----------------------------"
echo "Run this command in your terminal:"
echo "ssh root@151.243.171.80"
echo ""
echo "Then copy-paste these commands ONE BY ONE:"
echo ""
cat << 'ROOT_COMMANDS'
docker stop ai-trading-bot-prod trading-bot-postgres trading-bot-redis trading-bot-nginx 2>/dev/null || true
docker rm ai-trading-bot-prod trading-bot-postgres trading-bot-redis trading-bot-nginx 2>/dev/null || true
pkill -9 -f 'flask' || true
pkill -9 -f 'gunicorn' || true
pkill -9 -f 'python.*wsgi' || true
pkill -9 -f 'ai-ml-auto-bot' || true
pkill -9 -f 'ai_trading_bot' || true
echo "✅ Root cleanup completed"
exit
ROOT_COMMANDS

echo ""
echo "🔵 STEP 2: CLEAN AS AIBOT USER"
echo "------------------------------"
echo "Run this command in your terminal:"
echo "ssh aibot@151.243.171.80"
echo ""
echo "Then copy-paste these commands ONE BY ONE:"
echo ""
cat << 'AIBOT_COMMANDS'
cd /home/aibot
pkill -9 -f flask || true
pkill -9 -f gunicorn || true
pkill -9 -f 'python.*wsgi' || true
pkill -9 -f 'ai-ml-auto-bot' || true
pkill -9 -f 'ai_trading_bot' || true
if [ -d "ai-bot" ]; then
    mv ai-bot ai-bot.backup.$(date +%Y%m%d_%H%M%S)
    echo "Old ai-bot directory backed up"
fi
rm -rf ai-ml-auto-bot* 2>/dev/null || true
rm -rf trading_bot* 2>/dev/null || true
rm -rf *.db 2>/dev/null || true
rm -rf logs/ 2>/dev/null || true
rm -rf bot_persistence/ 2>/dev/null || true
rm -rf .venv/ 2>/dev/null || true
rm -rf __pycache__/ 2>/dev/null || true
rm -rf *.pyc 2>/dev/null || true
mkdir -p ai-bot
cd ai-bot
echo "✅ aibot cleanup completed"
exit
AIBOT_COMMANDS

echo ""
echo "🟢 STEP 3: DEPLOY FRESH BOT"
echo "--------------------------"
echo "After completing steps 1 & 2, run this on your LOCAL machine:"
echo "./deploy_to_vps_complete.sh"
echo ""

echo "🎯 WHAT THIS CLEANUP DOES:"
echo "- Stops and removes Docker containers (root level)"
echo "- Kills all running bot processes (both root and user)"
echo "- Backs up old ai-bot directory with timestamp"
echo "- Removes ALL old bot files, databases, logs, cache"
echo "- Creates fresh ai-bot directory"
echo "- Prepares for clean deployment"
echo ""

echo "⏱️  ESTIMATED TIME: 5-10 minutes"
echo "📞 SUPPORT: Run each command and check for errors"
echo ""

# Wait for user confirmation
echo "Ready to proceed? Press Enter when you've completed the cleanup..."
read -p ""