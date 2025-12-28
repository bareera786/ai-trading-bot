#!/bin/bash
# Production Update Script for AI Trading Bot (Docker-only)
# Run this on your VPS to rebuild and restart the container

set -e

APP_DIR="/home/aibot/ai-bot"
BACKUP_DIR="/home/aibot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.prod.yml}
SERVICE_NAME=${SERVICE_NAME:-ai-trading-bot}
CONTAINER_NAME=${CONTAINER_NAME:-ai-trading-bot-prod}

echo "🚀 Starting production update: $DATE"

# Create pre-update backup
echo "📦 Creating pre-update backup..."
mkdir -p "$BACKUP_DIR"
tar -czf "$BACKUP_DIR/pre_update_$DATE.tar.gz" "$APP_DIR/"

# Navigate to app directory
cd "$APP_DIR"

# Pull latest changes
echo "📥 Pulling latest changes from git..."
git pull origin main

# Rebuild and restart docker service
echo "🔄 Rebuilding and restarting Docker service ($SERVICE_NAME)..."
docker compose -f "$COMPOSE_FILE" build --pull "$SERVICE_NAME"
docker compose -f "$COMPOSE_FILE" up -d "$SERVICE_NAME"

# Wait for container to become healthy
echo "⏳ Waiting for container to become healthy..."
sleep 10

# Show container status
echo "📊 Container status:"
docker compose -f "$COMPOSE_FILE" ps "$SERVICE_NAME"

# Test health endpoint
echo "🏥 Testing health endpoint..."
curl -s http://localhost:5000/health | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print('✅ Health check passed:', data.get('status', 'unknown'))
except:
    print('❌ Health check failed')
"

echo ""
echo "🎉 Production update completed successfully!"
echo "📋 Service should be available at: http://your-domain.com"
echo "📊 Check logs with: docker logs -f $CONTAINER_NAME"