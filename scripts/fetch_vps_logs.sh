#!/bin/bash
# Load env
if [ -f config/deploy.env.production ]; then
    export $(cat config/deploy.env.production | grep -v '#' | awk '/=/ {print $1}')
fi

echo "🔍 Fetching logs from $VPS_HOST..."
ssh -i $HOME/.ssh/ai_bot_deploy -p $VPS_SSH_PORT $VPS_USER@$VPS_HOST "docker logs ai-trading-bot-prod --tail 200"
