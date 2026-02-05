#!/bin/bash
# Complete deployment script for premium UI and bot service restart

echo "🚀 AI Trading Bot - Complete Deployment"
echo "========================================"
echo ""

# Step 1: Fix service file
echo "📝 Step 1: Updating systemd service configuration..."
sudo cp /home/aibot/ai-bot/scripts/ai-trading-bot.service /etc/systemd/system/ai-trading-bot.service
echo "✅ Service file updated"
echo ""

# Step 2: Reload systemd
echo "🔄 Step 2: Reloading systemd daemon..."
sudo systemctl daemon-reload
echo "✅ Systemd reloaded"
echo ""

# Step 3: Restart the bot service
echo "🚀 Step 3: Restarting AI trading bot service..."
sudo systemctl restart ai-trading-bot
echo "⏳ Waiting 5 seconds for service to start..."
sleep 5
echo ""

# Step 4: Check service status
echo "📊 Step 4: Checking service status..."
sudo systemctl status ai-trading-bot --no-pager -l
echo ""

# Step 5: Check recent logs
echo "📋 Step 5: Recent bot logs (last 20 lines)..."
tail -20 /home/aibot/ai-bot/bot_stdout.log
echo ""

# Step 6: Verify files are in place
echo "✅ Step 6: Verifying premium UI files..."
if [ -f "/home/aibot/ai-bot/app/static/css/premium-trading.css" ]; then
    echo "✅ premium-trading.css found"
else
    echo "❌ premium-trading.css missing"
fi

if [ -f "/home/aibot/ai-bot/app/static/js/trading-ui.js" ]; then
    echo "✅ trading-ui.js found"
else
    echo "❌ trading-ui.js missing"
fi

if [ -f "/home/aibot/ai-bot/app/templates/spot_trading.html" ]; then
    echo "✅ spot_trading.html found"
else
    echo "❌ spot_trading.html missing"
fi

if [ -f "/home/aibot/ai-bot/app/templates/futures_trading.html" ]; then
    echo "✅ futures_trading.html found"
else
    echo "❌ futures_trading.html missing"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Check if service is 'active (running)' above"
echo "2. If running, test the UI at:"
echo "   - http://151.243.171.80:5000/trading/spot"
echo "   - http://151.243.171.80:5000/trading/futures"
echo "3. If not running, check logs: tail -f /home/aibot/ai-bot/bot_stdout.log"
