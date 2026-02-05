#!/bin/bash
# Phase 4: Performance Monitoring
# Run this on VPS: ssh aibot@151.243.171.80 'bash -s' < phase4_monitor.sh

set -e

# Load test user ID
if [ -f /tmp/test_user_id.txt ]; then
    TEST_USER_ID=$(cat /tmp/test_user_id.txt)
else
    echo "❌ ERROR: Test user ID not found. Run phase2_user_setup.sh first"
    exit 1
fi

echo "=========================================="
echo "TRADING PERFORMANCE MONITOR"
echo "Test User: $TEST_USER_ID"
echo "Time: $(date)"
echo "=========================================="
echo ""

# Total trades
echo "📊 TOTAL TRADES (Last 24 Hours)"
echo "----------------------------------------"
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
SELECT COUNT(*) as total_trades
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID'
  AND created_at > NOW() - INTERVAL '24 hours';
"

# Win rate
echo ""
echo "🎯 WIN RATE (Closed Trades)"
echo "----------------------------------------"
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
SELECT 
  COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins,
  COUNT(CASE WHEN pnl <= 0 THEN 1 END) as losses,
  ROUND(COUNT(CASE WHEN pnl > 0 THEN 1 END)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) as win_rate_pct
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID'
  AND created_at > NOW() - INTERVAL '24 hours'
  AND status = 'closed';
"

# Profitability
echo ""
echo "💰 PROFITABILITY"
echo "----------------------------------------"
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
SELECT 
  ROUND(SUM(pnl)::NUMERIC, 2) as total_pnl,
  ROUND(AVG(pnl)::NUMERIC, 4) as avg_pnl_per_trade,
  ROUND(MAX(pnl)::NUMERIC, 2) as best_trade,
  ROUND(MIN(pnl)::NUMERIC, 2) as worst_trade
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID'
  AND created_at > NOW() - INTERVAL '24 hours'
  AND status = 'closed';
"

# Position sizing
echo ""
echo "📏 POSITION SIZING"
echo "----------------------------------------"
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
SELECT 
  ROUND(AVG(quantity * entry_price)::NUMERIC, 2) as avg_position_usd,
  ROUND(MAX(quantity * entry_price)::NUMERIC, 2) as max_position_usd,
  ROUND(MIN(quantity * entry_price)::NUMERIC, 2) as min_position_usd
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID'
  AND created_at > NOW() - INTERVAL '24 hours';
"

# Open positions
echo ""
echo "🔓 OPEN POSITIONS"
echo "----------------------------------------"
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
SELECT id, symbol, side, quantity, entry_price, created_at
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID'
  AND status = 'open'
ORDER BY created_at DESC;
"

# Multi-user isolation check
echo ""
echo "🔒 ISOLATION CHECK"
echo "----------------------------------------"
OTHER_TRADES=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
SELECT COUNT(*) 
FROM comprehensive_trade_history
WHERE created_at > NOW() - INTERVAL '6 hours'
  AND user_id != '$TEST_USER_ID';
" | xargs)

if [ "$OTHER_TRADES" -eq 0 ]; then
    echo "✅ No trades from other users (isolation intact)"
else
    echo "❌ WARNING: $OTHER_TRADES trades from other users detected!"
    echo "   ISOLATION MAY BE COMPROMISED"
fi

# Check for isolation violations in logs
echo ""
echo "🚨 ISOLATION VIOLATIONS (Last 6 Hours)"
echo "----------------------------------------"
VIOLATIONS=$(sudo docker logs ai-trading-bot-ai-trading-bot-1 --since 6h 2>&1 | grep "ISOLATION VIOLATION" | wc -l)
echo "Violations found: $VIOLATIONS"

if [ "$VIOLATIONS" -gt 0 ]; then
    echo "❌ CRITICAL: Isolation violations detected!"
    echo "   Recent violations:"
    sudo docker logs ai-trading-bot-ai-trading-bot-1 --since 6h 2>&1 | grep "ISOLATION VIOLATION" | tail -5
fi

echo ""
echo "=========================================="
echo "Monitor complete. Run again in 6 hours."
echo "=========================================="
