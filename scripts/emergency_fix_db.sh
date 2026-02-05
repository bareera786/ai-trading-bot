#!/bin/bash
set -e

# Load config
source config/deploy.env

echo "🚑 Emergency DB Fix: Connecting to VPS ($VPS_HOST)..."

ssh $VPS_USER@$VPS_HOST "cd $VPS_PATH && \
    echo '🔍 Checking container logic...' && \
    docker compose -f docker-compose.prod.yml exec -T ai-trading-bot flask db upgrade && \
    echo '✅ Migration applied successfully.' && \
    docker compose -f docker-compose.prod.yml restart ai-trading-bot && \
    echo '♻️  Container restarted.' "

echo "🎉 Fix complete. Please try logging in again."
