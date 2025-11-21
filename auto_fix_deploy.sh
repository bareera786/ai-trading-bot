#!/bin/bash
# One-command auto-fix and redeploy

echo "🔧 Starting auto-fix and redeploy process..."

# Configuration
VPS_HOST="151.243.171.80"
VPS_USER="aibot"
VPS_PATH="/home/aibot/ai-bot"

echo "📋 Target: $VPS_USER@$VPS_HOST:$VPS_PATH"

# Step 1: Fix network binding on VPS
echo "🌐 Step 1: Fixing network binding..."
echo "Please enter your SSH password when prompted:"

ssh $VPS_USER@$VPS_HOST << 'ENDSSH'
echo "🛑 Stopping service..."
sudo systemctl stop aibot.service

echo "📝 Adding FLASK_RUN_HOST=0.0.0.0 to systemd service..."
sudo sed -i '/Environment="FLASK_RUN_PORT=5000"/a Environment="FLASK_RUN_HOST=0.0.0.0"' /etc/systemd/system/aibot.service

echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

echo "▶️  Starting service..."
sudo systemctl start aibot.service

echo "📊 Service status:"
sudo systemctl status aibot.service --no-pager | head -10
ENDSSH

if [ $? -ne 0 ]; then
    echo "❌ Network fix failed"
    exit 1
fi

echo "✅ Network binding fixed!"

# Step 2: Redeploy
echo "📦 Step 2: Redeploying bot..."
VPS_HOST=$VPS_HOST VPS_USER=$VPS_USER VPS_PATH=$VPS_PATH ./scripts/deploy_to_vps.sh

echo "�� Auto-fix and redeploy complete!"
echo "🌐 Your bot should now be accessible at: http://$VPS_HOST:5000"
