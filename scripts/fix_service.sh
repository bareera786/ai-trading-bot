#!/bin/bash
# Fix and restart the AI Trading Bot service

echo "🔍 Step 1: Checking current service configuration..."
sudo cat /etc/systemd/system/ai-trading-bot.service

echo ""
echo "📋 Step 2: Checking recent error logs..."
sudo journalctl -u ai-trading-bot -n 50 --no-pager | tail -20

echo ""
echo "🔧 Step 3: Copying fixed service file..."
sudo cp /home/aibot/ai-bot/scripts/ai-trading-bot.service /etc/systemd/system/ai-trading-bot.service

echo ""
echo "🔄 Step 4: Reloading systemd daemon..."
sudo systemctl daemon-reload

echo ""
echo "🚀 Step 5: Starting the service..."
sudo systemctl restart ai-trading-bot

echo ""
echo "⏳ Step 6: Waiting for service to start..."
sleep 5

echo ""
echo "✅ Step 7: Checking service status..."
sudo systemctl status ai-trading-bot --no-pager

echo ""
echo "📊 Step 8: Checking recent logs..."
tail -30 /home/aibot/ai-bot/bot_stdout.log

echo ""
echo "✅ Done! Service should now be running."
