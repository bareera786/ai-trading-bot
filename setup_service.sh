#!/bin/bash
# Manual systemd service setup script
# Run this on your VPS as the aibot user

echo "🔧 Setting up AI Trading Bot systemd service..."
echo ""

# Copy service file
echo "📋 Copying service file..."
sudo cp ~/ai-bot/ai-trading-bot.service /etc/systemd/system/

# Set permissions
echo "🔒 Setting permissions..."
sudo chmod 644 /etc/systemd/system/ai-trading-bot.service

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling service..."
sudo systemctl enable ai-trading-bot

# Start service
echo "🚀 Starting service..."
sudo systemctl start ai-trading-bot

# Check status
echo "📊 Service status:"
sudo systemctl status ai-trading-bot --no-pager

echo ""
echo "🎉 Service setup complete!"
echo ""
echo "🌐 Your bot should be accessible at: http://151.243.171.80:5000"
echo "📊 Prometheus metrics at: http://151.243.171.80:9090/metrics"
echo ""
echo "📋 Useful commands:"
echo "  Check status: sudo systemctl status ai-trading-bot"
echo "  View logs: sudo journalctl -u ai-trading-bot -f"
echo "  Restart: sudo systemctl restart ai-trading-bot"
echo "  Stop: sudo systemctl stop ai-trading-bot"