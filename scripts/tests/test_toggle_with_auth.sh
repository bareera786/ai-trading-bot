#!/bin/bash
echo "Starting bot..."
python3 ai_ml_auto_bot_final.py &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"
sleep 10

echo "Testing health endpoint..."
curl -s http://localhost:5000/health
echo ""

echo "Logging in as admin..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  -c cookies.txt)

echo "Login response: $LOGIN_RESPONSE"

# Extract session cookie if login was successful
if echo "$LOGIN_RESPONSE" | grep -q '"success":true'; then
    echo "Login successful, testing toggle API..."

    # First toggle - should enable trading
    echo "Testing toggle API (enable)..."
    TOGGLE1=$(curl -s -X POST http://localhost:5000/api/toggle_trading \
      -H "Content-Type: application/json" \
      -b cookies.txt)
    echo "Toggle response 1: $TOGGLE1"

    # Second toggle - should disable trading
    echo "Testing toggle API (disable)..."
    TOGGLE2=$(curl -s -X POST http://localhost:5000/api/toggle_trading \
      -H "Content-Type: application/json" \
      -b cookies.txt)
    echo "Toggle response 2: $TOGGLE2"

    # Third toggle - should enable trading again
    echo "Testing toggle API (enable again)..."
    TOGGLE3=$(curl -s -X POST http://localhost:5000/api/toggle_trading \
      -H "Content-Type: application/json" \
      -b cookies.txt)
    echo "Toggle response 3: $TOGGLE3"

else
    echo "Login failed, cannot test toggle API"
fi

echo "Killing bot..."
kill $BOT_PID
wait $BOT_PID 2>/dev/null
echo "Done"
