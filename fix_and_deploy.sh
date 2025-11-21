#!/bin/bash
# Auto-fix network binding and redeploy script

echo "🔧 Auto-fixing Flask network binding and redeploying..."

# Set variables
VPS_HOST=${VPS_HOST:-151.243.171.80}
VPS_USER=${VPS_USER:-aibot}
VPS_PATH=${VPS_PATH:-/home/aibot/ai-bot}

echo "📋 Configuration:"
echo "  Host: $VPS_HOST"
echo "  User: $VPS_USER"  
echo "  Path: $VPS_PATH"

# Create remote fix script
cat > /tmp/fix_service.sh << 'REMOTE_EOF'
#!/bin/bash
echo "🛑 Stopping service..."
sudo systemctl stop aibot.service

echo "📝 Updating systemd service..."
sudo sed -i '/Environment="FLASK_RUN_PORT=5000"/a Environment="FLASK_RUN_HOST=0.0.0.0"' /etc/systemd/system/aibot.service

echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

echo "▶️  Starting service..."
sudo systemctl start aibot.service

echo "📊 Service status:"
sudo systemctl status aibot.service --no-pager -l

echo "✅ Network binding fix applied!"
REMOTE_EOF

chmod +x /tmp/fix_service.sh

echo "📤 Uploading fix script to VPS..."
scp /tmp/fix_service.sh $VPS_USER@$VPS_HOST:/tmp/ 2>/dev/null || {
    echo "❌ SCP failed - you may need to enter password"
    exit 1
}

echo "🔧 Running fix on VPS..."
ssh $VPS_USER@$VPS_HOST "bash /tmp/fix_service.sh" 2>/dev/null || {
    echo "❌ SSH failed - you may need to enter password"
    exit 1
}

echo "📦 Redeploying updated bot..."
VPS_HOST=$VPS_HOST VPS_USER=$VPS_USER VPS_PATH=$VPS_PATH ./scripts/deploy_to_vps.sh

echo "🎉 Auto-fix and redeploy complete!"
