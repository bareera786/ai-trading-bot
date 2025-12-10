#!/bin/bash
# Complete VPS Cleanup Script for AI Trading Bot
# This script removes old installations from both root and aibot user

set -e  # Exit on any error

# Load configuration from production deploy.env
if [ -f "config/deploy.env.production" ]; then
    source config/deploy.env.production
    echo "✅ Using production configuration from config/deploy.env.production"
elif [ -f "config/deploy.env" ]; then
    source config/deploy.env
    echo "⚠️  Using legacy configuration from config/deploy.env"
else
    echo "❌ No config/deploy.env.production or config/deploy.env found. Please create production config."
    exit 1
fi

# Set defaults if not specified
VPS_HOST="${VPS_HOST:-your-vps-ip-or-domain}"
VPS_USER="${VPS_USER:-aibot}"
VPS_PATH="${VPS_PATH:-/home/aibot/ai-bot}"
VPS_SSH_PORT="${VPS_SSH_PORT:-22}"

echo "🧹 Starting COMPLETE VPS cleanup for fresh deployment..."
echo "📍 Target: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo "⚠️  This will remove ALL old bot data from both root and aibot user"
echo ""

# Check if required tools are installed
command -v rsync >/dev/null 2>&1 || { echo "❌ rsync is required but not installed. Aborting."; exit 1; }
command -v ssh >/dev/null 2>&1 || { echo "❌ ssh is required but not installed. Aborting."; exit 1; }

SSH_CMD="ssh -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST"
SSH_ROOT_CMD="ssh -p $VPS_SSH_PORT root@$VPS_HOST"

echo "🔄 Step 1: Stopping all services (as root)..."
echo "Please run these commands as ROOT on your VPS:"
echo ""
echo "# Connect as root:"
echo "ssh root@$VPS_HOST"
echo ""
echo "# Then run these commands:"
echo "systemctl stop ai-trading-bot 2>/dev/null || true"
echo "systemctl disable ai-trading-bot 2>/dev/null || true"
echo "rm -f /etc/systemd/system/ai-trading-bot.service"
echo "systemctl daemon-reload"
echo ""
echo "# Kill any processes running anywhere"
echo "pkill -9 -f 'flask' || true"
echo "pkill -9 -f 'gunicorn' || true"
echo "pkill -9 -f 'python.*wsgi' || true"
echo "pkill -9 -f 'ai-ml-auto-bot' || true"
echo "pkill -9 -f 'ai_trading_bot' || true"
echo ""

# Try to connect as root and run cleanup
echo "Attempting automated root cleanup..."
if $SSH_ROOT_CMD "echo 'Root access confirmed'" 2>/dev/null; then
    echo "✅ Root access available, running automated cleanup..."
    $SSH_ROOT_CMD "systemctl stop ai-trading-bot 2>/dev/null || true"
    $SSH_ROOT_CMD "systemctl disable ai-trading-bot 2>/dev/null || true"
    $SSH_ROOT_CMD "rm -f /etc/systemd/system/ai-trading-bot.service"
    $SSH_ROOT_CMD "systemctl daemon-reload"
    $SSH_ROOT_CMD "pkill -9 -f flask || true"
    $SSH_ROOT_CMD "pkill -9 -f gunicorn || true"
    $SSH_ROOT_CMD "pkill -9 -f 'python.*wsgi' || true"
    $SSH_ROOT_CMD "pkill -9 -f 'ai-ml-auto-bot' || true"
    $SSH_ROOT_CMD "pkill -9 -f 'ai_trading_bot' || true"
    echo "✅ Root-level services stopped"
else
    echo "⚠️  Root access not available without password. Please run the commands above manually as root."
fi

echo ""
echo "🔄 Step 2: Cleaning aibot user directory..."
echo "Please run these commands as aibot user on your VPS:"
echo ""
echo "# Connect as aibot:"
echo "ssh aibot@$VPS_HOST"
echo ""
echo "# Then run these commands:"
echo "cd /home/aibot"
echo "pkill -9 -f flask || true"
echo "pkill -9 -f gunicorn || true"
echo "pkill -9 -f 'python.*wsgi' || true"
echo "pkill -9 -f 'ai-ml-auto-bot' || true"
echo "pkill -9 -f 'ai_trading_bot' || true"
echo ""
echo "# Backup and remove old directory"
echo "if [ -d 'ai-bot' ]; then"
echo "    mv ai-bot ai-bot.backup.\$(date +%Y%m%d_%H%M%S)"
echo "fi"
echo ""
echo "# Remove any other bot-related files"
echo "rm -rf ai-ml-auto-bot* 2>/dev/null || true"
echo "rm -rf trading_bot* 2>/dev/null || true"
echo "rm -rf *.db 2>/dev/null || true"
echo "rm -rf logs/ 2>/dev/null || true"
echo "rm -rf bot_persistence/ 2>/dev/null || true"
echo ""
echo "# Create fresh directory"
echo "mkdir -p ai-bot"
echo "echo '✅ aibot user directory cleaned'"
echo ""

# Try to connect as aibot and run cleanup
echo "Attempting automated aibot cleanup..."
if $SSH_CMD "echo 'aibot access confirmed'" 2>/dev/null; then
    echo "✅ aibot access available, running automated cleanup..."
    $SSH_CMD "cd /home/aibot"
    $SSH_CMD "pkill -9 -f flask || true"
    $SSH_CMD "pkill -9 -f gunicorn || true"
    $SSH_CMD "pkill -9 -f 'python.*wsgi' || true"
    $SSH_CMD "pkill -9 -f 'ai-ml-auto-bot' || true"
    $SSH_CMD "pkill -9 -f 'ai_trading_bot' || true"

    # Backup old directory
    $SSH_CMD "if [ -d 'ai-bot' ]; then mv ai-bot ai-bot.backup.\$(date +%Y%m%d_%H%M%S); fi"

    # Remove other bot files
    $SSH_CMD "rm -rf ai-ml-auto-bot* 2>/dev/null || true"
    $SSH_CMD "rm -rf trading_bot* 2>/dev/null || true"
    $SSH_CMD "rm -rf *.db 2>/dev/null || true"
    $SSH_CMD "rm -rf logs/ 2>/dev/null || true"
    $SSH_CMD "rm -rf bot_persistence/ 2>/dev/null || true"

    # Create fresh directory
    $SSH_CMD "mkdir -p ai-bot"
    echo "✅ aibot user directory cleaned"
else
    echo "⚠️  aibot access not available without password. Please run the commands above manually as aibot user."
fi

echo ""
echo "🎉 VPS cleanup completed successfully!"
echo "📍 Ready for fresh deployment to: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo ""
echo "🚀 You can now run the deployment script:"
echo "   ./deploy_to_vps_complete.sh"