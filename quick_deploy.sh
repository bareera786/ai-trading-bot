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
echo "cd /home/aibot/ai-bot"
echo "docker compose -f docker-compose.prod.yml build --pull ai-trading-bot"
echo "docker compose -f docker-compose.prod.yml up -d ai-trading-bot"
echo "docker compose -f docker-compose.prod.yml ps ai-trading-bot"
echo "docker logs -f ai-trading-bot-prod"
echo ""
echo "🌐 Your bot will be accessible at: http://$VPS_HOST:5000"
