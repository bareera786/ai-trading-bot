#!/bin/bash
# Automated VPS Deployment Script for AI Trading Bot
# Uses SSH key authentication for secure deployment

set -e

# Configuration
VPS_HOST="151.243.171.80"
VPS_USER="aibot"
VPS_PATH="/home/aibot/ai-bot"
SSH_KEY="$HOME/.ssh/ai_bot_deploy"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

echo "🚀 Automated AI Trading Bot Deployment to VPS..."
echo "📍 Target: $VPS_USER@$VPS_HOST:$VPS_PATH"
echo ""

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    echo "Please run: ssh-keygen -t rsa -b 4096 -f ~/.ssh/ai_bot_deploy -N '' -C 'ai-bot-deployment'"
    exit 1
fi

# Check if we can connect to VPS
echo "🔑 Testing SSH connection..."
if ! ssh $SSH_OPTS $VPS_USER@$VPS_HOST "echo 'SSH connection successful'" 2>/dev/null; then
    echo "❌ SSH connection failed. Copying public key to VPS..."
    echo "Please provide your VPS password when prompted:"

    # Copy public key to VPS
    ssh-copy-id -i $SSH_KEY $VPS_USER@$VPS_HOST

    # Test connection again
    if ! ssh $SSH_OPTS $VPS_USER@$VPS_HOST "echo 'SSH connection successful'" 2>/dev/null; then
        echo "❌ SSH setup failed"
        exit 1
    fi
fi

echo "✅ SSH authentication working!"
echo ""

# Step 1: Sync files to VPS
echo "📦 Step 1: Syncing files to VPS..."
RSYNC_OPTS=(
    -az
    --progress
    --delete
    --exclude ".git/"
    --exclude ".venv/"
    --exclude "__pycache__/"
    --exclude "*.pyc"
    --exclude "logs/"
    --exclude "bot_persistence/backups/"
    --exclude "*.pkl"
    --exclude "*.joblib"
    -e "ssh $SSH_OPTS"
)

rsync "${RSYNC_OPTS[@]}" ./ "$VPS_USER@$VPS_HOST:$VPS_PATH/"

echo "✅ Files synced successfully!"
echo ""

# Step 2: Setup systemd service on VPS
echo "⚙️  Step 2: Setting up systemd service on VPS..."

# Copy service file and setup
ssh $SSH_OPTS $VPS_USER@$VPS_HOST "sudo cp $VPS_PATH/ai-trading-bot.service /etc/systemd/system/"
ssh $SSH_OPTS $VPS_USER@$VPS_HOST "sudo chmod 644 /etc/systemd/system/ai-trading-bot.service"
ssh $SSH_OPTS $VPS_USER@$VPS_HOST "sudo systemctl daemon-reload"
ssh $SSH_OPTS $VPS_USER@$VPS_HOST "sudo systemctl enable ai-trading-bot"

echo "🔄 Restarting service..."
ssh $SSH_OPTS $VPS_USER@$VPS_HOST "sudo systemctl restart ai-trading-bot"

echo "📊 Service status:"
ssh $SSH_OPTS $VPS_USER@$VPS_HOST "sudo systemctl status ai-trading-bot --no-pager"

echo ""
echo "🎉 Deployment completed successfully!"
echo ""
echo "🌐 Your bot is accessible at: http://$VPS_HOST:5000"
echo ""
echo "📋 Useful commands:"
echo "  Check status:    ssh $SSH_OPTS $VPS_USER@$VPS_HOST 'sudo systemctl status ai-trading-bot'"
echo "  View logs:       ssh $SSH_OPTS $VPS_USER@$VPS_HOST 'sudo journalctl -u ai-trading-bot -f'"
echo "  Restart service: ssh $SSH_OPTS $VPS_USER@$VPS_HOST 'sudo systemctl restart ai-trading-bot'"