#!/bin/bash
# Simple file deployment script for AI Trading Bot
# Only syncs files; restart containers separately

set -e

# Load configuration
if [ -f "config/deploy.env" ]; then
    source config/deploy.env
else
    echo "❌ config/deploy.env not found"
    exit 1
fi

VPS_HOST="${VPS_HOST:-your-vps-ip-or-domain}"
VPS_USER="${VPS_USER:-aibot}"
VPS_PATH="${VPS_PATH:-/home/aibot/ai-bot}"

echo "📦 Syncing files to VPS: $VPS_USER@$VPS_HOST:$VPS_PATH"

# Rsync options
RSYNC_OPTS=(
    -az
    --progress
    --exclude ".git/"
    --exclude ".venv/"
    --exclude "__pycache__/"
    --exclude "*.pyc"
    --exclude "logs/"
    --exclude "bot_persistence/backups/"
    --exclude "*.pkl"
    --exclude "*.joblib"
)

rsync "${RSYNC_OPTS[@]}" ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✅ Files synced successfully!"
echo ""
echo "🔄 To redeploy the container on the VPS:"
echo "   cd $VPS_PATH && docker compose -f docker-compose.prod.yml build --pull ai-trading-bot"
echo "   cd $VPS_PATH && docker compose -f docker-compose.prod.yml up -d ai-trading-bot"
echo "   cd $VPS_PATH && docker compose -f docker-compose.prod.yml logs ai-trading-bot --tail 50"
