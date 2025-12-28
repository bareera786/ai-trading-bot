#!/bin/bash
# VPS Cleanup Script for AI Trading Bot
# This script removes old installations and prepares for fresh deployment

set -e  # Exit on any error

# Load configuration from production deploy.env
if [ -f "config/deploy.env.production" ]; then
    source config/deploy.env.production
    echo "✅ Using production configuration from config/deploy.env.production"
elif [ -f "config/deploy.env" ]; then
    source config/deploy.env
    echo "⚠️  Using legacy configuration from config/deploy.env"
else
    echo "❌ No config/deploy.env.production or config/deploy.env found. Please create production config."
    exit 1
fi

# Set defaults if not specified
VPS_HOST="${VPS_HOST:-your-vps-ip-or-domain}"
VPS_USER="${VPS_USER:-aibot}"
VPS_PATH="${VPS_PATH:-/home/aibot/ai-bot}"
VPS_SSH_PORT="${VPS_SSH_PORT:-22}"

echo "🧹 Starting VPS cleanup for fresh deployment..."
echo "📍 Target: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo ""

# Check if required tools are installed
command -v rsync >/dev/null 2>&1 || { echo "❌ rsync is required but not installed. Aborting."; exit 1; }
command -v ssh >/dev/null 2>&1 || { echo "❌ ssh is required but not installed. Aborting."; exit 1; }

SSH_CMD="ssh -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST"

echo "🔄 Step 1: Stopping running containers and processes..."
$SSH_CMD "docker stop ai-trading-bot-prod 2>/dev/null || true && docker rm ai-trading-bot-prod 2>/dev/null || true"
$SSH_CMD "docker stop trading-bot-postgres trading-bot-redis trading-bot-nginx 2>/dev/null || true"
$SSH_CMD "pkill -f 'flask run' || true"
$SSH_CMD "pkill -f 'gunicorn' || true"
$SSH_CMD "pkill -f 'python.*wsgi' || true"

echo "✅ Containers and local processes stopped"
echo ""

echo "🗑️  Step 2: Removing old files..."
# Backup old directory if it exists
$SSH_CMD "if [ -d '$VPS_PATH' ]; then mv '$VPS_PATH' '$VPS_PATH.backup.$(date +%Y%m%d_%H%M%S)'; fi"

# Create fresh directory
$SSH_CMD "mkdir -p '$VPS_PATH'"

echo "✅ Old files removed, fresh directory created"
echo ""

echo "🎉 VPS cleanup completed successfully!"
echo "📍 Ready for fresh deployment to: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo ""
echo "🚀 You can now run the deployment script:"
echo "   ./deploy_to_vps_complete.sh"