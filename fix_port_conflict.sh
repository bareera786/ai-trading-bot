#!/bin/bash
# Fix port 5000 conflict on VPS

echo "🔍 Checking what's using port 5000..."
sudo lsof -i :5000 || echo "✅ No process found on port 5000"

echo ""
echo "🛑 Killing any Python processes..."
sudo pkill -f python || echo "✅ No Python processes to kill"

echo ""
echo "⏳ Waiting 2 seconds..."
sleep 2

echo ""
echo "🔄 Restarting ai-trading-bot service..."
sudo systemctl restart ai-trading-bot

echo ""
echo "⏳ Waiting 3 seconds for startup..."
sleep 3

echo ""
echo "📊 Service status:"
sudo systemctl status ai-trading-bot --no-pager

echo ""
echo "🌐 Testing connection..."
curl -s http://localhost:5000/health && echo "✅ Bot is responding!" || echo "❌ Bot not responding"