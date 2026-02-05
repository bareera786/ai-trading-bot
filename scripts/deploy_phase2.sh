#!/bin/bash
# Phase 2 Deployment Script
# Targeted sync and rebuild

set -e

# Load config
if [ -f "config/deploy.env.production" ]; then
    source config/deploy.env.production
else
    echo "❌ No config/deploy.env.production found."
    exit 1
fi

KEY_FILE="/Users/tahir/.ssh/ai_bot_deploy"

echo "Using Key: $KEY_FILE"
echo "Target: $VPS_USER@$VPS_HOST:$VPS_PATH"

echo "📦 Syncing Config & Deps..."
rsync -avz \
  -e "ssh -i $KEY_FILE -p $VPS_SSH_PORT" \
  requirements.txt \
  docker-compose.prod.yml \
  Dockerfile.optimized \
  config/ \
  monitoring/ \
  "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "📦 Syncing App Code..."
rsync -rlt --inplace --delete \
    --exclude ".git/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    --exclude "logs/" \
    --exclude "bot_persistence/" \
    -e "ssh -i $KEY_FILE -p $VPS_SSH_PORT" \
    app/ "$VPS_USER@$VPS_HOST:$VPS_PATH/app/"
    
echo "🔄 Rebuilding and Restarting (Phase 2)..."
ssh -i $KEY_FILE -p $VPS_SSH_PORT "$VPS_USER@$VPS_HOST" \
    "cd $VPS_PATH && docker compose --env-file config/deploy.env.production -f docker-compose.prod.yml up -d --build --remove-orphans"

echo "✅ Phase 2 Deployment Complete!"
