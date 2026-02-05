#!/bin/bash
# Phase 5: Final Performance Report
# Run this after test completion (72+ hours)
# Usage: ssh aibot@151.243.171.80 'bash -s' < phase5_final_report.sh

set -e

# Load test user ID
if [ -f /tmp/test_user_id.txt ]; then
    TEST_USER_ID=$(cat /tmp/test_user_id.txt)
else
    echo "❌ ERROR: Test user ID not found"
    exit 1
fi

# Load test times
if [ -f /tmp/test_start_time.txt ]; then
    START_TIME=$(cat /tmp/test_start_time.txt)
else
    START_TIME="Unknown"
fi

if [ -f /tmp/test_stop_time.txt ]; then
    STOP_TIME=$(cat /tmp/test_stop_time.txt)
else
    STOP_TIME="Ongoing"
fi

echo "=========================================="
echo "FINAL PERFORMANCE REPORT"
echo "=========================================="
echo "Test User: $TEST_USER_ID"
echo "Start Time: $START_TIME"
echo "Stop Time: $STOP_TIME"
echo "Report Generated: $(date)"
echo "=========================================="
echo ""

# Generate comprehensive report
sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -c "
-- Final Performance Summary
SELECT 
  'Total Trades' as metric, 
  COUNT(*)::TEXT as value
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days'

UNION ALL

SELECT 
  'Closed Trades', 
  COUNT(*)::TEXT
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days'
  AND status = 'closed'

UNION ALL

SELECT 
  'Win Rate %', 
  ROUND(COUNT(CASE WHEN pnl > 0 THEN 1 END)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2)::TEXT
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed'

UNION ALL

SELECT 
  'Total PnL \$', 
  ROUND(SUM(pnl)::NUMERIC, 2)::TEXT
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed'

UNION ALL

SELECT 
  'Avg Trade PnL \$', 
  ROUND(AVG(pnl)::NUMERIC, 4)::TEXT
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed'

UNION ALL

SELECT 
  'Best Trade \$', 
  ROUND(MAX(pnl)::NUMERIC, 2)::TEXT
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed'

UNION ALL

SELECT 
  'Worst Trade \$', 
  ROUND(MIN(pnl)::NUMERIC, 2)::TEXT
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed'

UNION ALL

SELECT 
  'Risk-Reward Ratio',
  ROUND(
    ABS(AVG(CASE WHEN pnl > 0 THEN pnl END)) / 
    NULLIF(ABS(AVG(CASE WHEN pnl < 0 THEN pnl END)), 0),
    2
  )::TEXT
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed';
"

echo ""
echo "=========================================="
echo "PASS/FAIL EVALUATION"
echo "=========================================="
echo ""

# Extract metrics for evaluation
TOTAL_TRADES=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
SELECT COUNT(*) 
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed';
" | xargs)

WIN_RATE=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
SELECT ROUND(COUNT(CASE WHEN pnl > 0 THEN 1 END)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2)
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed';
" | xargs)

TOTAL_PNL=$(sudo docker exec ai-trading-bot-postgres-1 psql -U postgres -d trading_bot -t -c "
SELECT ROUND(SUM(pnl)::NUMERIC, 2)
FROM comprehensive_trade_history
WHERE user_id = '$TEST_USER_ID' 
  AND created_at > NOW() - INTERVAL '7 days' 
  AND status = 'closed';
" | xargs)

echo "Evaluation Criteria:"
echo "-------------------"
echo "Total Trades: $TOTAL_TRADES (Target: ≥20)"
echo "Win Rate: ${WIN_RATE}% (Target: ≥55%)"
echo "Total PnL: \$${TOTAL_PNL} (Target: >0)"
echo ""

# Determine pass/fail
PASS=true

if [ -z "$TOTAL_TRADES" ] || [ "$TOTAL_TRADES" -lt 20 ]; then
    echo "❌ FAIL: Insufficient trades ($TOTAL_TRADES < 20)"
    PASS=false
fi

if [ -n "$WIN_RATE" ]; then
    if (( $(echo "$WIN_RATE < 55" | bc -l) )); then
        echo "⚠️  CAUTION: Win rate below target (${WIN_RATE}% < 55%)"
    fi
    if (( $(echo "$WIN_RATE < 40" | bc -l) )); then
        echo "❌ FAIL: Win rate too low (${WIN_RATE}% < 40%)"
        PASS=false
    fi
fi

if [ -n "$TOTAL_PNL" ]; then
    if (( $(echo "$TOTAL_PNL <= 0" | bc -l) )); then
        echo "❌ FAIL: Negative or zero PnL (\$${TOTAL_PNL})"
        PASS=false
    fi
fi

echo ""
if [ "$PASS" = true ]; then
    echo "✅ OVERALL: PASS - Strategy is viable"
    echo ""
    echo "Recommendation: Consider gradual rollout to more users"
else
    echo "❌ OVERALL: FAIL - Strategy needs improvement"
    echo ""
    echo "Recommendation: Analyze trade patterns and adjust ML parameters"
fi

echo ""
echo "=========================================="
echo "Report saved. Export data with:"
echo "bash export_test_data.sh"
echo "=========================================="
