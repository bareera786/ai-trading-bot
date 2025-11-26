#!/bin/bash
# Fix WSGI service script for AI Trading Bot
echo "🔧 Fixing AI Trading Bot WSGI service..."

# Stop the old service
echo "Stopping old service..."
sudo systemctl stop ai-trading-bot.service

# Reload systemd
echo "Reloading systemd configuration..."
sudo systemctl daemon-reload

# Start the new service
echo "Starting service with gunicorn..."
sudo systemctl start ai-trading-bot.service

# Check status
echo "Checking service status..."
sudo systemctl status ai-trading-bot.service

echo "✅ Service restart complete!"
echo "Monitor logs with: sudo journalctl -u ai-trading-bot.service -f"