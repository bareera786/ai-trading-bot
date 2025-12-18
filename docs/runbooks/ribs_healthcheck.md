## RIBS Health Check

This runbook describes the lightweight health-check added to monitor RIBS optimizer progress.

Files:
- `scripts/check_ribs_health.py` - checks `bot_persistence/ribs_checkpoints/ribs_status.json` and optionally posts to `RIBS_ALERT_WEBHOOK`.
- `deployments/systemd/check-ribs.service` and `.timer` - templates to run the check every 5 minutes.

Installation (on VPS):

1. Copy `deployments/systemd/check-ribs.service` to `/etc/systemd/system/check-ribs.service` and the timer file to `/etc/systemd/system/check-ribs.timer`.
2. Reload systemd: `sudo systemctl daemon-reload`.
3. Enable and start the timer: `sudo systemctl enable --now check-ribs.timer`.
4. Ensure `RIBS_ALERT_WEBHOOK` is set in `/home/aibot/ai-bot/config/deploy.env.production` if you want webhook alerts.

Behavior:
- The check fails if `ribs_status.json` or the latest checkpoint is older than `--max-age-seconds` (default 3600s in service template).
- On failure, the script will POST a JSON payload to the configured webhook if present. It will also print the message to stdout/stderr so systemd will capture it.
