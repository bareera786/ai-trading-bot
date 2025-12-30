#!/bin/bash
# Docker Deployment Fix Script
# This script ensures proper permissions and fixes read-only filesystem issues

set -e

echo "🔧 Preparing Docker deployment environment..."
echo "============================================="

# Create necessary directories on host
echo "📁 Creating host directories..."
mkdir -p ./bot_persistence/default/default/backups
mkdir -p ./bot_persistence/default/default/logs
mkdir -p ./bot_persistence/default/default/models
mkdir -p ./logs
mkdir -p ./artifacts
mkdir -p ./reports

# Set proper permissions (readable/writable by user 1000)
echo "🔐 Setting directory permissions..."
chmod -R 755 ./bot_persistence 2>/dev/null || true
chmod -R 755 ./logs 2>/dev/null || true
chmod -R 755 ./artifacts 2>/dev/null || true
chmod -R 755 ./reports 2>/dev/null || true

# Ensure user 1000 can write to these directories
chown -R 1000:1000 ./bot_persistence 2>/dev/null || true
chown -R 1000:1000 ./logs 2>/dev/null || true
chown -R 1000:1000 ./artifacts 2>/dev/null || true
chown -R 1000:1000 ./reports 2>/dev/null || true

echo "✅ Host environment prepared"
echo ""
echo "🐳 Starting Docker containers..."
# Try docker compose first (newer versions), fall back to docker-compose
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose down 2>/dev/null || true
    docker compose up -d --build
else
    docker-compose down 2>/dev/null || true
    docker-compose up -d --build
fi

echo ""
echo "📊 Checking deployment status..."
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose ps
else
    docker-compose ps
fi

echo ""
echo "🎉 Deployment completed successfully!"
echo "📋 View logs: docker-compose logs -f ai-bot"
echo "🌐 Access app at: http://your-server:5000"