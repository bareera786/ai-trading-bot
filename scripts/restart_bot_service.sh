#!/bin/bash
# Bot Service Restart Script
# This script restarts the AI trading bot service on the VPS

set -e

echo "🔍 Checking current bot service status..."
sudo systemctl status ai-trading-bot --no-pager || true

echo ""
echo "🔄 Restarting AI trading bot service..."
sudo systemctl restart ai-trading-bot

echo ""
echo "⏳ Waiting for service to start..."
sleep 5

echo ""
echo "✅ Checking new service status..."
sudo systemctl status ai-trading-bot --no-pager

echo ""
echo "📋 Checking recent logs..."
sudo journalctl -u ai-trading-bot -n 50 --no-pager

echo ""
echo "✅ Bot service restart complete!"
