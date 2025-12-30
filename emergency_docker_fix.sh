#!/bin/bash
# Emergency Docker Permission Fix
# Run this when you get "No such file or directory" errors for bot_persistence

set -e

echo "🚨 EMERGENCY DOCKER PERMISSION FIX"
echo "=================================="

# Stop all containers
echo "🛑 Stopping all containers..."
docker stop $(docker ps -aq) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true

# Remove old images to force rebuild
echo "🗑️  Removing old images..."
docker rmi ai-bot-app:latest 2>/dev/null || true

# Clean up volumes (optional - be careful!)
echo "🧹 Cleaning up old volumes..."
docker volume prune -f

# Create directories with correct permissions
echo "📁 Creating host directories..."
mkdir -p ./bot_persistence/default/default/backups
mkdir -p ./bot_persistence/default/default/logs
mkdir -p ./bot_persistence/default/default/models
mkdir -p ./logs
mkdir -p ./artifacts
mkdir -p ./reports

echo "🔐 Setting correct permissions..."
chmod -R 755 ./bot_persistence 2>/dev/null || true
chmod -R 755 ./logs 2>/dev/null || true
chmod -R 755 ./artifacts 2>/dev/null || true
chmod -R 755 ./reports 2>/dev/null || true

# Set ownership to UID 1000 (matches container user)
chown -R 1000:1000 ./bot_persistence 2>/dev/null || true
chown -R 1000:1000 ./logs 2>/dev/null || true
chown -R 1000:1000 ./artifacts 2>/dev/null || true
chown -R 1000:1000 ./reports 2>/dev/null || true

echo "✅ Host permissions fixed"

# Rebuild and start with the fixed configuration
echo "🔨 Rebuilding container with fixes..."
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose down
    docker compose build --no-cache
    docker compose up -d
else
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
fi

echo ""
echo "📊 Checking status..."
sleep 5
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose ps
    docker compose logs -f --tail=20
else
    docker-compose ps
    docker-compose logs -f --tail=20
fi

echo ""
echo "🎉 Emergency fix completed!"
echo "If you still see permission errors, check that your host user has UID 1000:"
echo "  id -u  # Should show 1000"
echo "  id -g  # Should show 1000 or compatible group"