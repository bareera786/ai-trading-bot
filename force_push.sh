#!/bin/bash
# Smart Force Update
# Zips files locally and transfers in one go to minimize password prompts

echo "🚀 Smart Force Update"
echo "====================="

# Load config
source config/deploy.env.production
PORT="${VPS_SSH_PORT:-22}"

# Create a temporary archive of the specific files we want to push
echo "📦 Packaging files..."
tar -czf deploy_patch.tar.gz \
    app/routes/trading.py \
    app/templates/futures_trading.html \
    app/static/js/trading-ui.js \
    app/services/market_data.py \
    app/services/binance.py \
    app/core/bot.py

echo "📤 Uploading package (Enter password ONCE)..."
scp -P $PORT deploy_patch.tar.gz $VPS_USER@$VPS_HOST:$VPS_PATH/deploy_patch.tar.gz

echo "🔄 Extracting and Rebuilding (Enter password ONCE)..."
ssh -p $PORT $VPS_USER@$VPS_HOST "cd $VPS_PATH && \
    tar -xzf deploy_patch.tar.gz && \
    rm deploy_patch.tar.gz && \
    echo '✅ Files extracted' && \
    docker compose -f docker-compose.prod.yml build --no-cache ai-trading-bot && \
    docker compose -f docker-compose.prod.yml up -d ai-trading-bot"

# Cleanup local archive
rm deploy_patch.tar.gz

echo ""
echo "🎉 Update complete!"
