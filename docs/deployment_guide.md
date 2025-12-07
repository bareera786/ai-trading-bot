# VPS Deployment Guide for AI Trading Bot

This guide walks through provisioning a fresh virtual private server, installing system prerequisites, configuring the trading bot, and wiring observability so it can run 24/7 with the new logging stack and journal/backtest telemetry. Steps assume Ubuntu 22.04 LTS on a $20–40/mo tier (4 vCPU, 8 GB RAM, 80+ GB SSD). Adjust paths for your own user if different.

## 1. Prepare the Server

1. **Harden SSH**
   - Create the VPS, add your SSH key, and disable password authentication.
   - Update packages and install baseline tooling:
     ```bash
     sudo apt update && sudo apt upgrade -y
     sudo apt install -y build-essential git curl unzip ufw htop
     ```
   - Enable a simple firewall (open HTTP if exposing the dashboard externally):
     ```bash
     sudo ufw allow OpenSSH
     sudo ufw allow 5000/tcp  # Flask dashboard (optional)
     sudo ufw enable
     ```

2. **Create a dedicated runtime user** (optional but recommended):
   ```bash
   sudo adduser --disabled-password --gecos "AI Bot" aibot
   sudo usermod -aG sudo aibot
   sudo su - aibot
   ```

## 2. Install Python & Native Libraries

1. **Python runtime**
   ```bash
   sudo apt install -y python3.10 python3.10-venv python3.10-dev
   ```

2. **TA-Lib and scientific stack** (required for indicators and ML):
   ```bash
   sudo apt install -y libopenblas-dev libatlas-base-dev liblapack-dev gfortran
   sudo apt install -y ta-lib libta-lib0
   ```
   > Some cloud images dont ship the TA-Lib package. If `apt` cant find it, build from source:
   > ```bash
   > curl -L https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz | tar xz
   > cd ta-lib
   > ./configure --prefix=/usr
   > make
   > sudo make install
   > ```

## 3. Clone the Repository

```bash
cd ~/ && git clone https://github.com/<your-org>/ai-bot.git
cd ai-bot
```

If copying files manually, ensure `start_server.py`, `wsgi.py`, the `app/` package, and the `docs/` + `bot_persistence/` directories land in the same root.

## 4. Create the Python Environment

1. **Virtual environment & pip**
   ```bash
   python3.10 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

2. **Install Python dependencies**
   ```bash
   pip install flask numpy pandas scipy scikit-learn matplotlib python-binance joblib requests aiohttp apscheduler python-dateutil cryptography ta-lib
   ```
   - `ta-lib` here corresponds to the Python bindings; the native lib from step 2 must already be present.
   - If futures trading is disabled, python-binance can remain optional; the bot will fall back to offline mode.

3. **Optional extras**
   ```bash
   pip install gunicorn supervisor
   ```
   Useful if fronting the Flask app behind a process manager or reverse proxy.

## 5. Configure Runtime Paths & Environment

1. **Directory layout (per profile)**
   ```bash
   PROFILE=${BOT_PROFILE:-default}
   mkdir -p ~/ai-bot/logs/$PROFILE
   mkdir -p ~/ai-bot/bot_persistence/$PROFILE/backups
   mkdir -p ~/ai-bot/credentials
   mkdir -p ~/ai-bot/trade_data/$PROFILE
   ```
   Each instance now writes to profile-scoped folders (`bot_persistence/<profile>/`, `logs/<profile>/`,
   and `credentials/<profile>.json`). Switching `BOT_PROFILE` keeps tenants isolated on the same host.

2. **Environment variables** (append to `~/.bashrc` or a systemd unit):
   ```bash
   export BOT_PROFILE=default            # set per tenant/container
   export BOT_LOG_LEVEL=INFO
   export BOT_LOG_DIR="/home/aibot/ai-bot/logs"
   export BOT_LOG_COMPONENTS="ALL"     # e.g. TRADE_ENGINE,ML_SYSTEM,UI
   export BINANCE_TESTNET=1             # Stays in paper mode
   export FLASK_RUN_PORT=5000
   export BINANCE_CREDENTIAL_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
   export BINANCE_TERMS_ACCEPTED=0
   ```
   - Override `BOT_LOG_COMPONENTS` with a comma-separated list (e.g. `TRADE_ENGINE,ORDER_ROUTER`) to restrict noise.
   - Set `BOT_REAL_TRADING=1` only after wiring secure credentials.

3. **Binance credentials & compliance flags**
   - For spot/futures, POST them via the dashboard UI or `curl` to `/api/binance/credentials` once the app is running.
   - Store keys in the provided encrypted persistence store; never hardcode them.
   - Non-testnet trading remains blocked until both `BINANCE_TERMS_ACCEPTED=1` and `FINAL_HAMMER=TRUE` are set.

## 6. Launch the Bot

### Development mode (manual shell)
```bash
source ~/ai-bot/.venv/bin/activate
python start_server.py
```
- The dashboard renders at `http://<server-ip>:5000/`.
- Logs stream to `logs/bot.log` and `logs/bot.debug.log` while also teeing to stdout.

Prefer using the Flask CLI for iterative dev/testing so you can override settings via `FLASK_APP=app:create_app`:

```bash
export FLASK_APP=app:create_app
flask run --host=0.0.0.0 --port=5000
```

### Production mode (systemd)
Create `/etc/systemd/system/aibot.service` (as `root`):
```ini
[Unit]
Description=AI Trading Bot
After=network.target

[Service]
User=aibot
WorkingDirectory=/home/aibot/ai-bot
Environment="BOT_LOG_DIR=/home/aibot/ai-bot/logs"
Environment="BOT_LOG_LEVEL=INFO"
Environment="FLASK_RUN_PORT=5000"
EnvironmentFile=/home/aibot/.aibot-env  # optional extra vars
ExecStart=/home/aibot/ai-bot/.venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 2 --timeout 120 wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now aibot.service
sudo systemctl status aibot.service
```
Tail logs with `journalctl -u aibot.service -f` or the log files under `~/ai-bot/logs`.

> Tip: The repo ships with `ai-trading-bot.service` plus `setup_systemd_service.sh` to copy it into `/etc/systemd/system/`—customize the paths/env vars there if your deployment layout differs.

### Updating the VPS without Git

If you maintain the project locally and prefer not to install Git on the server, use the provided deployment helper:

1. Copy the sample dotenv file and fill in your VPS settings (the real file is ignored by Git):
   ```bash
   cp config/deploy.env.example config/deploy.env
   # edit config/deploy.env with your VPS_* values
   ```

2. Run the deploy script (it will auto-load `config/deploy.env`; direct env vars still override if provided):
   ```bash
   chmod +x scripts/deploy_to_vps.sh
   ./scripts/deploy_to_vps.sh
   ```

The script copies the workspace via `rsync`, compiles the main module on the VPS, and restarts the systemd service. Customize via environment variables:

- `VPS_PORT` (default `22`)
- `VPS_SERVICE` (default `aibot.service`)
- `SKIP_RESTART=1` to avoid restarting immediately
- `RSYNC_DELETE=1` to mirror exactly (removes files absent locally)
- `SYNC_STATE=1` to include runtime state folders (`bot_persistence/`, `trade_data/`, `optimized_trade_data/`). By default these are skipped so deployments do not clobber live trading flags or journals.
- `DEPLOY_ENV_FILE` to point at an alternate dotenv file if `config/deploy.env` isn’t desired.

Ensure the remote `.venv/` exists with dependencies installed; the script skips syncing that directory to speed up deployments.

### Reverse proxy (optional)
- Use Nginx/Traefik to terminate TLS and proxy to `localhost:5000`.
- Add HTTP auth or VPN if exposing the dashboard publicly.

## 7. Persistence & Backups

- State auto-saves on clean shutdown or when `persistence_scheduler` triggers.
- To create manual backups: `curl -X POST http://localhost:5000/api/persistence/save`.
- Copy `bot_persistence/` and `trade_data/` nightly using `rsync` or object storage.

## 8. Monitoring & Health Checks

- **Ping endpoints**: `/api/status`, `/api/journal?mode=ultimate`, `/api/backtests`.
- **Log rotation**: Already handled via rotating file handlers (defaults 5 MB × 5 files). Adjust with env vars `BOT_LOG_MAX_BYTES` and `BOT_LOG_BACKUPS`.
- **Metrics scraping**: Use `curl` + `jq` to expose selected fields into your monitoring stack.
- **Backtest health**: Run `python scripts/backtest_health_check.py` (or hit `/api/health`) to surface underperforming symbols and top strategies from `reports/backtest_top10.json`.
- **Dashboard health tab**: Open the new **Health** tab in the dashboard to review the full strategy health report, top performers, breaches, and raw symbol metrics; the status overview also shows the current badge for a quick glance.
- **Alerts**: Watch for `badge-danger` journal entries or runtime exceptions in `bot.debug.log`.

## 9. Multi-User & Tenancy Considerations

The current build remains single-tenant; state, credentials, and logs share one workspace. To run multiple distinct users:
- Instantiate separate system users or containers, each with its own checkout and persistence folder.
- Isolate API ports (`FLASK_RUN_PORT`, `BOT_SOCKET_PORT`, etc.) per instance.
- Follow the refactor plan in `docs/multi_user_strategy.md` before sharing persistence layers between tenants.

## 10. Maintenance Checklist

- Patch the OS monthly (`sudo apt upgrade`).
- Rotate Binance API keys regularly; revoke compromised keys.
- Test journal/backtest tabs after every upgrade (ensures the dashboard script changes deployed here remain intact).
- Keep virtualenv packages current (`pip list --outdated`).

With these steps, the bot should boot cleanly on a new VPS, log richly for debugging, and surface journal/backtest data in the dashboard without manual tweaks. Reach out to the ops runbook in `docs/ui_journal_backtest_fix_notes.md` if UI panels regress.
