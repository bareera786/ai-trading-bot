#!/bin/bash
# Quick Deployment Script (No Sudo)
# Bypasses permission fixes since we verified rsync access already.

set -e

# Load configuration
if [ -f "config/deploy.env.production" ]; then
    source config/deploy.env.production
else
    echo "Using default config"
fi

VPS_HOST="${VPS_HOST:-151.243.171.80}"
VPS_USER="${VPS_USER:-aibot}"
VPS_PATH="${VPS_PATH:-/home/aibot/ai-bot}"
VPS_SSH_PORT="${VPS_SSH_PORT:-22}"

echo "🚀 Starting QUICK deployment (No Sudo)..."

# Step 1: Sync files
echo "📦 Syncing files..."
RSYNC_OPTS=(
    -rlt
    --no-perms
    --no-owner
    --no-group
    --no-times
    --progress
    --exclude ".DS_Store"
    --exclude ".git/"
    --exclude ".venv/"
    --exclude "__pycache__/"
    --exclude "logs/"
    --exclude "bot_persistence/"
    --exclude "bot_persistence_backup_new/"
    --exclude "trade_data/"
    --exclude "reports/"
    --exclude "optimized_trade_data/"
    --exclude "ultimate_models/"
    --exclude "optimized_models/"
    --exclude "futures_models/"
    --exclude "*.pkl"
    --exclude "*.joblib"
    --exclude "htmlcov/"
    --exclude "node_modules/"
)

rsync "${RSYNC_OPTS[@]}" -e "ssh -o StrictHostKeyChecking=no -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT" ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✅ Files synced."

# Step 2: Restart Docker
echo "🔄 Restarting Container..."
SSH_CMD="ssh -o StrictHostKeyChecking=no -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST"

$SSH_CMD "cd $VPS_PATH && docker compose --env-file config/deploy.env.production -f docker-compose.prod.yml down"
$SSH_CMD "cd $VPS_PATH && docker compose --env-file config/deploy.env.production -f docker-compose.prod.yml up -d --build"

echo "🎉 Deployment Complete!"
