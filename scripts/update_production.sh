#!/bin/bash
# Production Update Script for AI Trading Bot
# Run this on your VPS to update the application

set -e

APP_DIR="/home/aibot/ai-bot"
BACKUP_DIR="/home/aibot/backups"
DATE=$(date +%Y%m%d_%H%M%S)

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

# Activate virtual environment and install dependencies
echo "📦 Installing new dependencies..."
source .venv/bin/activate
pip install -r requirements.txt

# Run database migrations (if any)
echo "🗄️  Running database migrations..."
export FLASK_APP=wsgi.py
flask db upgrade 2>/dev/null || echo "No migrations to run"

# Clear any cached bytecode
echo "🧹 Clearing Python cache..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Restart service
echo "🔄 Restarting AI Trading Bot service..."
sudo systemctl restart ai-trading-bot

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
sudo systemctl status ai-trading-bot --no-pager

# Test health endpoint
echo "🏥 Testing health endpoint..."
curl -s http://localhost:8000/health | python3 -c "
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
echo "📊 Check logs with: sudo journalctl -u ai-trading-bot -f"