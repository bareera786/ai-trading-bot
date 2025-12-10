#!/bin/bash
# Quick VPS Deployment Script - Files Only
# Uses SSH key authentication

set -e

# Configuration
VPS_HOST="151.243.171.80"
VPS_USER="aibot"
VPS_PATH="/home/aibot/ai-bot"
SSH_KEY="$HOME/.ssh/ai_bot_deploy"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "📦 Quick AI Trading Bot File Deployment to VPS..."
echo "📍 Target: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo ""

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    exit 1
fi

# Step 1: Sync files to VPS
echo "📦 Syncing files to VPS..."
RSYNC_OPTS=(
    -az
    --progress
    --delete
    --exclude ".git/"
    --exclude ".venv/"
    --exclude "__pycache__/"
    --exclude "*.pyc"
    --exclude "logs/"
    --exclude "bot_persistence/backups/"
    --exclude "*.pkl"
    --exclude "*.joblib"
    -e "ssh $SSH_OPTS"
)

rsync "${RSYNC_OPTS[@]}" ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✅ Files synced successfully!"
echo ""
echo "🔄 To complete deployment on VPS, run these commands:"
echo ""
echo "sudo cp /home/aibot/ai-bot/ai-trading-bot.service /etc/systemd/system/"
echo "sudo chmod 644 /etc/systemd/system/ai-trading-bot.service"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable ai-trading-bot"
echo "sudo systemctl restart ai-trading-bot"
echo "sudo systemctl status ai-trading-bot --no-pager"
echo ""
echo "🌐 Your bot will be accessible at: http://$VPS_HOST:5000"
