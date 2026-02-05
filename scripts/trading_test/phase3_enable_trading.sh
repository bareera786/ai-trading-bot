#!/bin/bash
# Phase 3: Enable Trading for Test User
# Run this on VPS: ssh aibot@151.243.171.80 'bash -s' < phase3_enable_trading.sh

set -e

echo "=========================================="
echo "PHASE 3: ENABLE TRADING"
echo "=========================================="
echo ""

# Load test user ID
if [ -f /tmp/test_user_id.txt ]; then
    TEST_USER_ID=$(cat /tmp/test_user_id.txt)
    echo "Test User ID: $TEST_USER_ID"
else
    echo "❌ ERROR: Test user ID not found. Run phase2_user_setup.sh first"
    exit 1
fi

# Enable trading for test user
echo ""
echo "[3.1] Enabling trading for user $TEST_USER_ID..."
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
UPDATE user_portfolio 
SET auto_trade_enabled = true 
WHERE user_id = '$TEST_USER_ID';
"

# Verify
echo ""
echo "[3.2] Verifying trading enabled..."
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
SELECT user_id, auto_trade_enabled, updated_at 
FROM user_portfolio 
WHERE user_id = '$TEST_USER_ID';
"

# Check that ONLY this user has trading enabled
echo ""
echo "[3.3] Verifying isolation..."
ENABLED_COUNT=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
SELECT COUNT(*) 
FROM user_portfolio 
WHERE auto_trade_enabled = true;
" | xargs)

if [ "$ENABLED_COUNT" -eq 1 ]; then
    echo "✅ Only 1 user has trading enabled (correct)"
else
    echo "⚠️  WARNING: $ENABLED_COUNT users have trading enabled!"
    sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
    SELECT user_id, auto_trade_enabled 
    FROM user_portfolio 
    WHERE auto_trade_enabled = true;
    "
fi

# Record start time
echo ""
echo "[3.4] Recording test start time..."
date "+%Y-%m-%d %H:%M:%S %Z" > /tmp/test_start_time.txt
echo "Test started at: $(cat /tmp/test_start_time.txt)"

echo ""
echo "=========================================="
echo "PHASE 3 COMPLETE - TRADING ENABLED"
echo "=========================================="
echo ""
echo "⚠️  IMPORTANT: Trading is now ACTIVE for user $TEST_USER_ID"
echo ""
echo "Next steps:"
echo "1. Monitor logs: sudo docker logs -f ai-trading-bot-ai-trading-bot-1 | grep -E '(TRADE|ORDER|SIGNAL)'"
echo "2. Run monitoring: bash phase4_monitor.sh"
echo "3. Emergency stop: bash emergency_stop.sh"
