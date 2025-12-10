#!/bin/bash
# Systemd Service Setup Script for AI Trading Bot
# Run this on your VPS as root or with sudo

SERVICE_NAME="ai-trading-bot"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
LOCAL_SERVICE_FILE="./ai-trading-bot.service"

echo "🚀 Setting up AI Trading Bot systemd service..."

# Check if running as root or sudo
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root or with sudo"
   exit 1
fi

# Copy service file
echo "📋 Copying service file to /etc/systemd/system/"
cp "$LOCAL_SERVICE_FILE" "$SERVICE_FILE"

# Set proper permissions
chmod 644 "$SERVICE_FILE"

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable the service
echo "✅ Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

# Start the service
echo "▶️  Starting service..."
systemctl start "$SERVICE_NAME"

# Check status
echo "📊 Service status:"
systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "🎉 Service setup complete!"
echo ""
echo "📋 Useful commands:"
echo "  Check status:    sudo systemctl status $SERVICE_NAME"
echo "  View logs:       sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart service: sudo systemctl restart $SERVICE_NAME"
echo "  Stop service:    sudo systemctl stop $SERVICE_NAME"
echo "  Start service:   sudo systemctl start $SERVICE_NAME"
echo ""
echo "🌐 Your bot should be accessible at: http://your-vps-ip:5000"
