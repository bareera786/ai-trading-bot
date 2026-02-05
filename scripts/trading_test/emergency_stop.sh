#!/bin/bash
# Emergency Stop Script
# Run this IMMEDIATELY if issues detected
# Usage: ssh aibot@151.243.171.80 'bash -s' < emergency_stop.sh

set -e

echo "=========================================="
echo "🚨 EMERGENCY STOP ACTIVATED"
echo "=========================================="
echo ""

# Load test user ID if available
if [ -f /tmp/test_user_id.txt ]; then
    TEST_USER_ID=$(cat /tmp/test_user_id.txt)
    echo "Test User ID: $TEST_USER_ID"
else
    echo "⚠️  Test user ID not found, will stop ALL trading"
    TEST_USER_ID=""
fi

echo ""
read -p "Choose stop method (1=Test User Only, 2=Global Kill Switch): " STOP_METHOD

if [ "$STOP_METHOD" = "1" ] && [ -n "$TEST_USER_ID" ]; then
    echo ""
    echo "[1] Disabling trading for test user only..."
    sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
    UPDATE user_portfolio 
    SET auto_trade_enabled = false 
    WHERE user_id = '$TEST_USER_ID';
    "
    echo "✅ Trading disabled for user $TEST_USER_ID"
    
elif [ "$STOP_METHOD" = "2" ]; then
    echo ""
    echo "[2] Activating GLOBAL kill switch..."
    sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
    INSERT INTO global_config (key, value, updated_at) 
    VALUES ('GLOBAL_TRADING_LOCK', 'true', NOW())
    ON CONFLICT (key) DO UPDATE SET value = 'true', updated_at = NOW();
    "
    echo "✅ Global trading LOCKED (all users stopped)"
    
else
    echo "❌ Invalid option or missing user ID"
    exit 1
fi

# Check for open positions
echo ""
echo "Checking for open positions..."
if [ -n "$TEST_USER_ID" ]; then
    OPEN_POSITIONS=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
    SELECT COUNT(*) 
    FROM comprehensive_trade_history
    WHERE user_id = '$TEST_USER_ID' AND status = 'open';
    " | xargs)
    
    if [ "$OPEN_POSITIONS" -gt 0 ]; then
        echo "⚠️  WARNING: $OPEN_POSITIONS open position(s) detected"
        sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
        SELECT id, symbol, side, quantity, entry_price, created_at
        FROM comprehensive_trade_history
        WHERE user_id = '$TEST_USER_ID' AND status = 'open';
        "
        echo ""
        echo "⚠️  You may need to manually close these positions via Binance"
    else
        echo "✅ No open positions"
    fi
fi

# Record stop time
date "+%Y-%m-%d %H:%M:%S %Z" > /tmp/test_stop_time.txt
echo ""
echo "=========================================="
echo "TRADING STOPPED"
echo "Stop time: $(cat /tmp/test_stop_time.txt)"
echo "=========================================="
echo ""
echo "Next step: Run phase5_final_report.sh to generate performance report"
