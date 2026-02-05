#!/bin/bash
# FRESH Deployment Script - Wipes Database and Code on Remote
# Use this when the server state is corrupted or you want a clean slate.

set -e

# Load Config
if [ -f "config/deploy.env.production" ]; then
    source config/deploy.env.production
else
    echo "❌ Missing config/deploy.env.production"
    exit 1
fi

VPS_HOST="${VPS_HOST:-your-vps-ip}"
VPS_USER="${VPS_USER:-aibot}"
VPS_PATH="${VPS_PATH:-/home/aibot/ai-bot}"
VPS_SSH_PORT="${VPS_SSH_PORT:-22}"

echo "⚠️  WARNING: THIS WILL WIPE THE REMOTE DATABASE AND FILES ⚠️"
SSH_CMD="ssh -t -o StrictHostKeyChecking=no -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST"

echo "1. 🔥 STOPPING SERVICES & WIPING REMOTE DATA..."
# Restart Docker first to clear network zombies/DNS issues
echo "   🔄 Restarting Docker Daemon..."
$SSH_CMD "sudo systemctl restart docker"

# Stop containers and remove volumes first to release file locks
$SSH_CMD "cd $VPS_PATH && docker compose -f docker-compose.prod.yml down --volumes --remove-orphans || true"

# Cleanup and Wipe (Combined to minimize password prompts)
echo "   💥 Obliterating $VPS_PATH (and fixing permissions)..."
# 1. Chown to user (to ensure we can delete)
# 2. Rm -rf
# 3. Mkdir
# 4. Chown new dir
$SSH_CMD "sudo sh -c 'chown -R $VPS_USER:$VPS_USER $VPS_PATH 2>/dev/null; rm -rf $VPS_PATH; mkdir -p $VPS_PATH; chown $VPS_USER:$VPS_USER $VPS_PATH'"

echo "2. 📦 Syncing fresh files..."
# Rsync to now-empty directory
rsync -rlt \
    --no-perms --no-owner --no-group --no-times \
    --exclude ".DS_Store" \
    --exclude ".git/" \
    --exclude ".venv/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    --exclude "logs/" \
    --exclude "node_modules/" \
    --exclude "bot_persistence/" \
    --exclude "ultimate_models/" \
    --exclude "optimized_models/" \
    --exclude "futures_models/" \
    --exclude "bot_persistence_backup_new/" \
    --exclude "bot.log" \
    --exclude "final_reset.log" \
    --exclude "assets_fix.log" \
    --exclude "trade_data/" \
    --exclude "config/deploy.env" \
    -e "ssh -o StrictHostKeyChecking=no -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT" \
    ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✅ Files synced."

echo "3. � Configuring Environment..."
# Docker Compose needs config/deploy.env to exist (referenced in env_file)
$SSH_CMD "cp $VPS_PATH/config/deploy.env.production $VPS_PATH/config/deploy.env"

echo "4. �🚀 Starting Fresh..."
$SSH_CMD "cd $VPS_PATH && docker compose --env-file config/deploy.env.production -f docker-compose.prod.yml up -d --build"

echo "✅ Fresh Deployment Complete."
echo "The database has been reset. The schema will be created from scratch."
