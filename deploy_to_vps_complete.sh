#!/bin/bash
# Complete VPS Deployment Script for AI Trading Bot
# This script handles file transfer and systemd service setup

set -e  # Exit on any error

# Configuration - Update these variables for your VPS
VPS_HOST="your-vps-ip-or-domain"
VPS_USER="tahir"
VPS_PATH="/home/tahir/ai-bot"
VPS_SSH_PORT="22"

echo "🚀 Starting complete AI Trading Bot deployment to VPS..."
echo "📍 Target: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo ""

# Check if required tools are installed
command -v rsync >/dev/null 2>&1 || { echo "❌ rsync is required but not installed. Aborting."; exit 1; }
command -v ssh >/dev/null 2>&1 || { echo "❌ ssh is required but not installed. Aborting."; exit 1; }

# Step 1: Sync files to VPS
echo "📦 Step 1: Syncing files to VPS..."
RSYNC_OPTS=(
    -az
    --progress
    --exclude ".git/"
    --exclude ".venv/"
    --exclude "__pycache__/"
    --exclude "*.pyc"
    --exclude "logs/"
    --exclude "bot_persistence/backups/"
    --exclude "*.pkl"  # Skip large model files initially
    --exclude "*.joblib"
)

rsync "${RSYNC_OPTS[@]}" -e "ssh -p $VPS_SSH_PORT" ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✅ Files synced successfully!"
echo ""

# Step 2: Setup systemd service on VPS
echo "⚙️  Step 2: Setting up systemd service on VPS..."

SSH_CMD="ssh -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST"

# Copy service file and setup script to VPS
echo "📋 Copying systemd service files..."
$SSH_CMD "sudo cp $VPS_PATH/ai-trading-bot.service /etc/systemd/system/"
$SSH_CMD "sudo chmod 644 /etc/systemd/system/ai-trading-bot.service"

# Reload systemd and enable service
echo "🔄 Reloading systemd and enabling service..."
$SSH_CMD "sudo systemctl daemon-reload"
$SSH_CMD "sudo systemctl enable ai-trading-bot"

# Start the service
echo "▶️  Starting AI Trading Bot service..."
$SSH_CMD "sudo systemctl start ai-trading-bot"

# Check service status
echo "📊 Service status:"
$SSH_CMD "sudo systemctl status ai-trading-bot --no-pager"

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "🌐 Your bot should be accessible at: http://$VPS_HOST:5000"
echo ""
echo "📋 Useful commands on your VPS:"
echo "  Check status:    sudo systemctl status ai-trading-bot"
echo "  View logs:       sudo journalctl -u ai-trading-bot -f"
echo "  Restart service: sudo systemctl restart ai-trading-bot"
echo "  Stop service:    sudo systemctl stop ai-trading-bot"
echo ""
echo "🔧 To update the bot later, just run this script again!"
echo "   It will sync changes and restart the service automatically."