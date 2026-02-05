#!/bin/bash
# Phase 2: Test User Setup
# Run this on VPS: ssh aibot@151.243.171.80 'bash -s' < phase2_user_setup.sh

set -e

echo "=========================================="
echo "PHASE 2: TEST USER SETUP"
echo "=========================================="
echo ""

# 2.1 List available users
echo "[2.1] Available users:"
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
SELECT id, username, email, is_admin, created_at 
FROM \"user\" 
WHERE is_active = true 
ORDER BY created_at 
LIMIT 10;
"

echo ""
echo "Enter the TEST_USER_ID from the list above:"
read -p "TEST_USER_ID: " TEST_USER_ID

if [ -z "$TEST_USER_ID" ]; then
    echo "❌ ERROR: No user ID provided"
    exit 1
fi

# Save to file for other scripts
echo "$TEST_USER_ID" > /tmp/test_user_id.txt
echo "✅ Test user ID saved: $TEST_USER_ID"

# 2.2 Verify user has credentials
echo ""
echo "[2.2] Checking credentials for user $TEST_USER_ID..."
CRED_COUNT=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
SELECT COUNT(*) 
FROM exchange_credential 
WHERE user_id = '$TEST_USER_ID' AND is_active = true;
" | xargs)

if [ "$CRED_COUNT" -gt 0 ]; then
    echo "✅ User has $CRED_COUNT active credential(s)"
    sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
    SELECT user_id, exchange, testnet, created_at 
    FROM exchange_credential 
    WHERE user_id = '$TEST_USER_ID' AND is_active = true;
    "
else
    echo "❌ ERROR: User has no active credentials!"
    echo "   User must complete onboarding wizard first"
    exit 1
fi

# 2.3 Check current trading status
echo ""
echo "[2.3] Current trading status for user $TEST_USER_ID..."
CURRENT_STATUS=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
SELECT auto_trade_enabled 
FROM user_portfolio 
WHERE user_id = '$TEST_USER_ID';
" | xargs)

echo "Current auto_trade_enabled: $CURRENT_STATUS"

# 2.4 Verify ONLY this user will have trading enabled
echo ""
echo "[2.4] Checking other users with trading enabled..."
OTHER_USERS=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
SELECT COUNT(*) 
FROM user_portfolio 
WHERE auto_trade_enabled = true AND user_id != '$TEST_USER_ID';
" | xargs)

if [ "$OTHER_USERS" -gt 0 ]; then
    echo "⚠️  WARNING: $OTHER_USERS other user(s) have trading enabled!"
    sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
    SELECT user_id, auto_trade_enabled 
    FROM user_portfolio 
    WHERE auto_trade_enabled = true;
    "
    echo ""
    read -p "Disable trading for other users? (yes/no): " DISABLE_OTHERS
    if [ "$DISABLE_OTHERS" = "yes" ]; then
        sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
        UPDATE user_portfolio 
        SET auto_trade_enabled = false 
        WHERE user_id != '$TEST_USER_ID';
        "
        echo "✅ Disabled trading for other users"
    fi
else
    echo "✅ No other users have trading enabled"
fi

echo ""
echo "=========================================="
echo "PHASE 2 COMPLETE"
echo "=========================================="
echo "Test User ID: $TEST_USER_ID"
echo ""
echo "Next step: Run phase3_enable_trading.sh"
