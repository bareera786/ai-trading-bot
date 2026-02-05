#!/bin/bash
KEY="/Users/tahir/.ssh/ai_bot_deploy"
HOST="151.243.171.80"
USER="aibot"

echo "🔍 Checking VPS Logs..."
echo "----------------------"
echo "1. Worker Container Status:"
ssh -o StrictHostKeyChecking=no -i $KEY -p 22 $USER@$HOST "docker ps | grep worker"

echo ""
echo "2. Worker Logs (Last 50 lines):"
# Attempt to fetch logs
ssh -o StrictHostKeyChecking=no -i $KEY -p 22 $USER@$HOST "docker logs --tail 50 ai-trading-bot-worker"

echo ""
echo "3. Application Config Check:"
ssh -o StrictHostKeyChecking=no -i $KEY -p 22 $USER@$HOST "docker exec ai-trading-bot-prod env | grep -E 'ENCRYPTION|REDIS_URL'"   
