## RIBS Stress Test Runbook

This document describes how to run an extended RIBS optimization stress test on a server (VPS) and monitor checkpoint health.

1. Pull the latest code and activate your virtualenv:

```bash
cd ~/ai-bot
git pull origin main
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the stress runner (example 1000 iterations):

```bash
./scripts/ribs_stress_runner.py 1000 > logs/ribs_stress.log 2>&1 &
```

3. Monitor checkpoints and status file:

```bash
tail -f logs/ribs_stress.log
python3 scripts/check_ribs_health.py 21600  # warn if older than 6 hours
```

4. To add a cron job that checks health every hour and POSTs to `RIBS_ALERT_WEBHOOK` if stale:

```cron
0 * * * * cd /home/ubuntu/ai-bot && /home/ubuntu/ai-bot/.venv/bin/python3 scripts/check_ribs_health.py 21600
```

5. After the run, inspect `bot_persistence/ribs_checkpoints` for checkpoint files and `ribs_status.json`.
