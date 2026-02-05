#!/bin/bash
# Quick fix - just copy the corrected service file and restart

echo "🔧 Deploying corrected service file..."
sudo cp /home/aibot/ai-bot/scripts/ai-trading-bot.service /etc/systemd/system/ai-trading-bot.service

echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

echo "🚀 Starting service..."
sudo systemctl restart ai-trading-bot

echo "⏳ Waiting 5 seconds..."
sleep 5

echo ""
echo "✅ Service status:"
sudo systemctl status ai-trading-bot --no-pager

echo ""
echo "📊 Recent logs (last 20 lines):"
tail -20 /home/aibot/ai-bot/bot_stdout.log
