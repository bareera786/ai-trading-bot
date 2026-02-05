#!/bin/bash
# Phase 1: Pre-Flight Safety Checks
# Run this on VPS: ssh aibot@151.243.171.80 'bash -s' < phase1_safety_checks.sh

set -e

echo "=========================================="
echo "PHASE 1: PRE-FLIGHT SAFETY CHECKS"
echo "=========================================="
echo ""

# 1.1 Verify Multi-User Isolation
echo "[1.1] Checking for isolation fixes..."
if grep -q "ISOLATION VIOLATION" /home/aibot/ai-bot/app/routes/trading.py; then
    echo "✅ Isolation violation logging found"
else
    echo "❌ WARNING: Isolation logging not found!"
fi

echo ""
echo "[1.1] Checking for global fallbacks in spot toggle..."
if grep -A10 "def api_spot_toggle" /home/aibot/ai-bot/app/routes/trading.py | grep -q 'ctx.get("ultimate_trader")'; then
    echo "❌ CRITICAL: Global fallback still exists in spot toggle!"
    exit 1
else
    echo "✅ No global fallback in spot toggle"
fi

echo ""
echo "[1.1] Checking for global fallbacks in futures manual toggle..."
if grep -A10 "def api_futures_manual_toggle" /home/aibot/ai-bot/app/routes/trading.py | grep -q 'ctx.get("ultimate_trader")'; then
    echo "❌ CRITICAL: Global fallback still exists in futures manual toggle!"
    exit 1
else
    echo "✅ No global fallback in futures manual toggle"
fi

# 1.2 Verify Database Schema
echo ""
echo "[1.2] Verifying database schema..."
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "\d user_portfolio" | grep -q "auto_trade_enabled"
if [ $? -eq 0 ]; then
    echo "✅ auto_trade_enabled column exists"
else
    echo "❌ CRITICAL: auto_trade_enabled column missing!"
    exit 1
fi

# 1.3 Verify Emergency Kill Switch
echo ""
echo "[1.3] Checking emergency kill switch status..."
KILL_SWITCH=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "SELECT value FROM global_config WHERE key='GLOBAL_TRADING_LOCK';" | xargs)

if [ -z "$KILL_SWITCH" ]; then
    echo "✅ Kill switch not set (trading allowed)"
elif [ "$KILL_SWITCH" = "false" ]; then
    echo "✅ Kill switch is OFF (trading allowed)"
else
    echo "❌ WARNING: Kill switch is ON (trading blocked globally)"
    echo "   Run this to disable: sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c \"UPDATE global_config SET value='false' WHERE key='GLOBAL_TRADING_LOCK';\""
fi

echo ""
echo "=========================================="
echo "PHASE 1 COMPLETE"
echo "=========================================="
echo ""
echo "Next step: Run phase2_user_setup.sh"
