#!/bin/bash
# Quick Redeploy - Just sync code changes without full rebuild
# Use this for quick fixes after initial deployment

cd /Users/tahir/Desktop/ai-bot

echo "🔄 Quick Redeploy to VPS"
echo "========================"
echo ""

# Load config
source config/deploy.env.production

echo "📦 Syncing code changes..."
rsync -rlt --inplace --no-perms --no-owner --no-group \
    --exclude ".git/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    --exclude "logs/" \
    --exclude "bot_persistence/" \
    -e "ssh -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT" \
    app/ "$VPS_USER@$VPS_HOST:$VPS_PATH/app/"

echo "✅ Code synced"
echo ""

echo "🔄 Restarting container..."
ssh -i /Users/tahir/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST \
    "cd $VPS_PATH && docker compose -f docker-compose.prod.yml restart ai-trading-bot"

echo ""
echo "✅ Redeploy complete!"
echo "🌐 Check: http://$VPS_HOST:5000"

echo "🔍 Fetching Container Logs..."
ssh -i $HOME/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST "grep -A 5 'Bootstrap patch active' $VPS_PATH/app/bootstrap.py || echo '❌ Patch NOT found in remote file'"
ssh -i $HOME/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST "docker logs ai-trading-bot-prod --tail 50"
