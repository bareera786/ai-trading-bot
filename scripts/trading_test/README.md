# Live Trading Test Scripts

## Quick Start

These scripts implement the **Live Trading Performance Test Plan** for safe, controlled evaluation of the AI trading strategy.

### Prerequisites
- Multi-user isolation fixes deployed to VPS
- SSH access to VPS: `ssh aibot@151.243.171.80`
- Docker containers running

### Execution Order

```bash
# 1. Safety checks (verify isolation fixes)
bash phase1_safety_checks.sh

# 2. Select and verify test user
bash phase2_user_setup.sh

# 3. Enable trading for test user
bash phase3_enable_trading.sh

# 4. Monitor performance (run every 6 hours)
bash phase4_monitor.sh

# 5. Emergency stop (if needed)
bash emergency_stop.sh

# 6. Final report (after 72+ hours)
bash phase5_final_report.sh
```

### Running from Local Machine

Transfer scripts to VPS:
```bash
cd /Users/tahir/Desktop/ai-bot/scripts/trading_test
scp *.sh aibot@151.243.171.80:/home/aibot/
```

Then SSH and run:
```bash
ssh aibot@151.243.171.80
cd /home/aibot
chmod +x *.sh
./phase1_safety_checks.sh
```

### Monitoring Schedule

**Every 6 hours**: Run `phase4_monitor.sh`
**Daily**: Check for isolation violations
**After 72 hours**: Run `phase5_final_report.sh`

### Emergency Stop

If ANY of these occur, run `emergency_stop.sh` immediately:
- Isolation violations in logs
- Trades from other users
- Total PnL < -$500
- Drawdown > 20%

### Pass/Fail Criteria

**PASS** (after 72 hours):
- Win rate ≥55%
- Total PnL > 0
- Max drawdown <10%
- 20+ trades

**FAIL** (stop immediately):
- Win rate <40% (after 30+ trades)
- Total PnL < -$500
- Drawdown >20%
- Isolation violations

### Files Created

- `/tmp/test_user_id.txt` - Test user ID
- `/tmp/test_start_time.txt` - Test start timestamp
- `/tmp/test_stop_time.txt` - Test stop timestamp

### Support

See full documentation: `LIVE_TRADING_TEST_PLAN.md`
