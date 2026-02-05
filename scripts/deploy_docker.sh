#!/bin/bash
# Docker-based deployment script for premium UI updates

echo "🐳 AI Trading Bot - Docker Deployment"
echo "======================================"
echo ""

# Navigate to project directory
cd /home/aibot/ai-bot

# Step 1: Verify files are in place
echo "✅ Step 1: Verifying premium UI files..."
if [ -f "app/static/css/premium-trading.css" ]; then
    echo "✅ premium-trading.css found"
else
    echo "❌ premium-trading.css missing"
    exit 1
fi

if [ -f "app/static/js/trading-ui.js" ]; then
    echo "✅ trading-ui.js found"
else
    echo "❌ trading-ui.js missing"
    exit 1
fi

if [ -f "app/templates/spot_trading.html" ]; then
    echo "✅ spot_trading.html found"
else
    echo "❌ spot_trading.html missing"
    exit 1
fi

if [ -f "app/templates/futures_trading.html" ]; then
    echo "✅ futures_trading.html found"
else
    echo "❌ futures_trading.html missing"
    exit 1
fi

echo ""

# Step 2: Restart the ai-bot container
echo "🔄 Step 2: Restarting ai-bot container..."
docker-compose restart ai-bot

echo "⏳ Waiting 10 seconds for container to start..."
sleep 10
echo ""

# Step 3: Check container status
echo "📊 Step 3: Checking container status..."
docker-compose ps ai-bot
echo ""

# Step 4: Check container logs
echo "📋 Step 4: Recent container logs (last 30 lines)..."
docker-compose logs --tail=30 ai-bot
echo ""

# Step 5: Check if Flask is responding
echo "🌐 Step 5: Testing Flask application..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health | grep -q "200"; then
    echo "✅ Flask application is responding"
else
    echo "⚠️  Flask application may not be ready yet"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Check if container is 'Up' above"
echo "2. Test the premium UI at:"
echo "   - http://151.243.171.80:5000/trading/spot"
echo "   - http://151.243.171.80:5000/trading/futures"
echo "3. If issues, check full logs: docker-compose logs -f ai-bot"
