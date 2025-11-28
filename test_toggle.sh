#!/bin/bash
echo "Starting bot..."
python3 ai_ml_auto_bot_final.py &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"
sleep 10
echo "Testing health endpoint..."
curl -s http://localhost:5000/health
echo ""
echo "Testing toggle API..."
curl -X POST http://localhost:5000/api/toggle_trading -H "Content-Type: application/json" -d '{"admin_token": "admin"}'
echo ""
echo "Testing toggle API again..."
curl -X POST http://localhost:5000/api/toggle_trading -H "Content-Type: application/json" -d '{"admin_token": "admin"}'
echo ""
echo "Killing bot..."
kill $BOT_PID
wait $BOT_PID 2>/dev/null
echo "Done"
