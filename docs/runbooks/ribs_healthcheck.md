## RIBS Health Check

This runbook describes the lightweight health-check added to monitor RIBS optimizer progress.

Files:
- `scripts/check_ribs_health.py` - checks `bot_persistence/ribs_checkpoints/ribs_status.json` and optionally posts to `RIBS_ALERT_WEBHOOK`.

Installation (on VPS via cron):

1. Create a cron entry (example: every 5 minutes) for the aibot user:
	```bash
	*/5 * * * * cd /home/aibot/ai-bot && /usr/bin/python3 scripts/check_ribs_health.py >> /home/aibot/ai-bot/logs/ribs_health.log 2>&1
	```
2. Ensure `RIBS_ALERT_WEBHOOK` is set in `/home/aibot/ai-bot/config/deploy.env.production` if you want webhook alerts.

Behavior:
- The check fails if `ribs_status.json` or the latest checkpoint is older than `--max-age-seconds` (default 3600s in service template).
- On failure, the script will POST a JSON payload to the configured webhook if present. Output is written to the cron log path above for inspection.
