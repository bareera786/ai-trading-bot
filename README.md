# AI Trading Bot - Ultimate Professional Version

A comprehensive AI-powered cryptocurrency trading bot with advanced machine learning, parallel processing, enterprise-grade features, and self-improvement capabilities.

## 🚀 Features

### Core Capabilities
- **Advanced ML Models**: Random Forest, Gradient Boosting, Voting Classifier with 43+ indicators
- **Parallel Processing**: Joblib-based multi-core signal generation
- **Real-time Trading**: Live Binance API integration with testnet and futures support
- **Comprehensive Indicators**: 43+ technical indicators with TA-Lib fallbacks
- **Multi-timeframe Analysis**: 1h, 4h, 1d, 1w analysis
- **Self-Improvement Worker**: Continuous model training and optimization (runs every 6 hours)

### Signal Generation Modules
- **CRT (Composite Rhythm Trading)**: Multi-timeframe momentum analysis
- **ICT (Inner Circle Trader)**: Institutional trading patterns
- **SMC (Smart Money Concepts)**: Market structure analysis
- **Quantum Fusion Momentum (QFM)**: Advanced momentum indicators with regime detection

### Safety & Risk Management
- **Dynamic Position Sizing**: Risk-adjusted position management with adaptive risk multipliers
- **Circuit Breakers**: Automatic trading halts on loss streaks
- **Volatility Filters**: Market stress detection and regime-based adjustments
- **API Failure Handling**: Robust error recovery and retry mechanisms

### Professional Features
- **Comprehensive Trade History**: Detailed P&L tracking with live portfolio updates
- **Backtesting Engine**: Historical performance analysis with health monitoring
- **Web Dashboard**: Real-time monitoring interface with admin controls
- **Admin Dashboard**: User management, symbol management, backtest lab, system settings
- **Configurable Profiles**: Multiple trading strategies with profile-scoped storage
- **Logging & Monitoring**: Enterprise-grade logging with Prometheus metrics
- **PostgreSQL Support**: Production-ready database with migrations
- **Systemd Deployment**: Automated service management for VPS deployment
- **Multi-User Support**: Tenant isolation with profile-based data separation
- **Futures Trading**: Advanced leverage trading with risk controls

### Advanced Analytics
- **Correlation Matrix**: Real-time symbol correlation analysis
- **Ensemble Predictions**: Multi-model voting for improved accuracy
- **Live P&L Updates**: Real-time portfolio performance monitoring
- **Marketing Analytics**: Optional Plausible-style tracking integration

## 📋 Requirements

- Python 3.10+ (3.11 recommended for best performance)
- pip 23+ with virtualenv support
- TA-Lib C library installed on the host (macOS: `brew install ta-lib`, Ubuntu/Debian: build from source as shown below)
- Binance API keys (only when enabling live trading)
- 8GB+ RAM recommended
- Multi-core CPU for parallel processing

## 🛠️ Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-trading-bot.git
   cd ai-trading-bot
   ```

2. **Install TA-Lib (system dependency)**

   ```bash
   # macOS
   brew install ta-lib

   # Debian/Ubuntu (build from source)
   sudo apt update && sudo apt install -y build-essential wget
   cd /tmp && wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
   tar -xzf ta-lib-0.4.0-src.tar.gz && cd ta-lib-0.4.0
   ./configure --prefix=/usr && make && sudo make install
   ```

3. **Create a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

4. **Install Python dependencies**

   ```bash
   pip install --upgrade pip wheel
   pip install -r requirements.txt
   ```

5. **Configure environment variables**

   ```bash
   cp config/deploy.env.example config/deploy.env
   nano config/deploy.env
   ```

   Key environment flags:

   - `FINAL_HAMMER`: Defaults to `FALSE`. Keep it `FALSE` for development, paper trading, and futures/real-market dry runs. Set it to `TRUE` **only** after verifying live keys, balances, and risk controls—the bot refuses to place real or futures orders until this is explicitly enabled.
   - `BOT_PROFILE`: Selects which profile under `config/default` to load (defaults to `default`).
   - `DATABASE_URL`: Point this at Postgres/MySQL in production; falls back to `sqlite:///trading_bot.db` locally.
   - `ENABLE_MARKETING_ANALYTICS`, `MARKETING_ANALYTICS_SRC`, `MARKETING_ANALYTICS_DOMAIN`, `MARKETING_ANALYTICS_API_HOST`: Optional Plausible-style tracking snippet injected on `/marketing`, `/login`, `/register` when enabled (set `ENABLE_MARKETING_ANALYTICS=1`).

6. **(Optional) Configure Binance credentials for live trading**

   ```bash
   # In config/deploy.env
   BINANCE_API_KEY=your_api_key_here
   BINANCE_API_SECRET=your_api_secret_here
   BOT_PROFILE=default
   ```

## ✅ Binance Compliance & Submission

If you're preparing this bot for Binance Academy/API approval, start with `docs/binance_compliance.md`. It captures:

- A requirement→implementation matrix mapping Binance guidelines to the controls in this repo.
- Security practices for API key handling, storage, logging, and network boundaries.
- Test suites & uptime probes Binance reviewers typically request as evidence.
- A submission checklist (architecture diagram, demo video, compliance attestation, etc.).

**New safeguards to configure before submitting:**

- Generate a credential encryption key and set `BINANCE_CREDENTIAL_KEY` so Binance API keys are written to disk only after Fernet encryption. Example: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- Set `BINANCE_TERMS_ACCEPTED=1` only after accepting the [Binance Developer Terms](https://developers.binance.com/docs/binance-api/terms); the bot blocks non-testnet trading until this flag is enabled.
- Keep `FINAL_HAMMER=FALSE` + `BINANCE_TESTNET=1` for demos and review sessions—switching either flag requires a full compliance re-check.

Keep your deployment on `BINANCE_TESTNET=1` with `FINAL_HAMMER=FALSE` until Binance approves the integration, then follow the rotation steps outlined in that document before enabling live trading.

## 🚀 Usage

### Local dashboard (development)

```bash
source .venv/bin/activate
export FINAL_HAMMER=FALSE
python start_server.py
```

This starts the Flask dashboard at `http://localhost:5000`. You can also run it via Flask CLI:

```bash
export FLASK_APP=start_server.py
export FINAL_HAMMER=FALSE
flask run --host=0.0.0.0 --port=5000
```

> **Note:** `ai_ml_auto_bot_final.py` is kept for backwards compatibility, but the preferred entrypoint is `start_server.py`/Flask CLI so the modular `app/` package wiring is respected—helper scripts such as `simple_server.py` and `create_admin.py` now bootstrap through `create_app()` as well.

## 🧩 Runtime architecture

The legacy monolith has been decomposed into typed runtime modules so the Flask factory (and tests) can wire everything without importing `ai_ml_auto_bot_final.py` directly:

- `app/runtime/context.py` – typed wrapper around the dashboard payload plus helpers for attaching to Flask apps.
- `app/runtime/builder.py` – assembles the runtime context (indicator + symbol + persistence + background + service runtimes) and is used by `app/bootstrap.py`.
- `app/runtime/factories.py` – builds ML/trading service bundles so both Flask bootstrap and `ai_ml_auto_bot_final.py` can import them without side effects.
- `app/runtime/indicators.py`, `symbols.py`, `persistence.py`, `background.py`, `services.py` – focused builders for each subsystem.
- `app/runtime/system.py` – runs the legacy initialization flow (`initialize_runtime_from_context`) using only the assembled payload.

When `create_app()` runs, `bootstrap_runtime()` calls the builder, attaches the resulting context to Flask, and then hands the payload to `initialize_runtime_from_context()` to start schedulers, background workers, and health monitoring. Running `ai_ml_auto_bot_final.py` directly still works, but it now calls `register_ai_bot_context(app, force=True)` only when executed as a script, keeping imports side-effect free.

To keep the initializer honest, `tests/test_runtime_system.py` spins up dummy traders, ML systems, and background managers to assert that persistence, background tasks, health monitoring, and signal handlers all wire up correctly with (and without) optional services.

### Refreshing hashed dashboard assets

The dashboard HTML references hashed bundles generated under `app/static/dist/`. If those bundles are missing or were checked in as empty files, the Flask helper now falls back to the legacy `app/static/css/*.css` and `app/static/js/*.js` assets so you still get a working UI. For the production look and smaller payloads, rebuild the hashed bundles:

```bash
npm install         # once per machine
npm run build:assets
```

The command populates `app/static/dist/` and rewrites `app/static/dist/manifest.json`. After rebuilding you can restart `flask run` (or `start_server.py`) and the dashboard/login pages will automatically pick up the fresh hashed assets.

### Creating an admin user

Use the shared CLI helper (it now bootstraps the Flask app via `create_app()` so it works against the exact same database/extension wiring):

```bash
source .venv/bin/activate
python create_admin.py --username admin --email admin@example.com
```

- Omit `--password` to be prompted securely; include it for scripted environments.
- Pass `--reset-password` to rotate credentials for an existing admin without deleting records.
- Log in at `http://localhost:5000/login` afterwards and force a password change in production.

### Profile-scoped storage sanity check

Phase 0 of the multi-tenant roadmap is complete: persistence, logs, and Binance credentials now live under per-profile directories. You can smoke-test this behavior without touching live data:

```bash
source .venv/bin/activate
pytest tests/test_profile_pathing.py
```

The suite provisions temporary `BOT_PROFILE` values (e.g., `alpha`, `bravo`) and verifies that:

- `resolve_profile_path()` routes persistence assets to distinct folders per profile and leaves prior data untouched.
- `BinanceCredentialStore` reads/writes vault files scoped to `<profile>.json`, so credentials saved for one tenant never appear in another tenant's store.

Run the tests whenever you change profile/pathing logic or before rolling out new tenant profiles.

### Backtesting & diagnostics

```bash
source .venv/bin/activate
FINAL_HAMMER=FALSE python scripts/backtest_health_check.py
python scripts/status_diagnostics.py
```

### Production deployment

#### VPS Deployment with PostgreSQL and Systemd

1. **Prepare your VPS** (Ubuntu/Debian recommended):
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install PostgreSQL
   sudo apt install -y postgresql postgresql-contrib

   # Start and enable PostgreSQL
   sudo systemctl enable postgresql
   sudo systemctl start postgresql

   # Create database and user
   sudo -u postgres psql -c "CREATE USER aibot_test WITH PASSWORD 'test_password_123';"
   sudo -u postgres psql -c "CREATE DATABASE ai_trading_bot_test OWNER aibot_test;"
   ```

2. **Deploy the application**:
   ```bash
   # Clone repository on VPS
   git clone https://github.com/bareera786/ai-trading-bot.git
   cd ai-trading-bot

   # Install system dependencies
   sudo apt install -y python3 python3-pip python3-venv build-essential ta-lib

   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate

   # Install Python dependencies
   pip install -r requirements.txt

   # Configure environment
   cp config/deploy.env.example config/deploy.env.production
   nano config/deploy.env.production  # Set DATABASE_URL and other configs

   # Create admin user
   python create_admin.py --username admin --password admin123 --email admin@example.com

   # Setup systemd service
   sudo cp ai-trading-bot.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable ai-trading-bot
   sudo systemctl start ai-trading-bot
   ```

3. **Verify deployment**:
   ```bash
   # Check service status
   sudo systemctl status ai-trading-bot

   # View logs
   sudo journalctl -u ai-trading-bot -f

   # Test health endpoint
   curl -s http://localhost:5000/health

   # Access dashboard at http://your-vps-ip:5000
   ```

#### Alternative: Automated deployment script

```bash
# From your local machine
./deploy_to_vps_complete.sh
```

### Systemd service management

```bash
sudo systemctl status ai-trading-bot      # check status
sudo journalctl -u ai-trading-bot -f      # follow logs
sudo systemctl restart ai-trading-bot     # restart
sudo systemctl stop ai-trading-bot        # stop
sudo systemctl start ai-trading-bot       # start
```

## 🧩 Modular architecture status

The legacy single-file app has been split into a maintainable Flask package housed under `app/`. Highlights:

- `create_app()` in `app/__init__.py` is now the default entrypoint for `start_server.py`, `wsgi.py`, CLI helpers, and tests. The old `ai_ml_auto_bot_final.py` simply imports shared services for backwards compatibility.
- Blueprints under `app/routes/` replace inline route declarations, so auth, users, dashboard, trading, analytics, and persistence APIs live in dedicated modules.
- Services such as traders, ML pipelines, persistence, futures control, market data, health checks, and live P&L schedulers reside in `app/services/` and are wired through a common AI bot context to keep global state in one place.
- Background jobs live in `app/tasks/`, giving schedulers predictable lifecycle hooks for market data, self-improvement, persistence snapshots, and live portfolio refresh.
- Dashboard UI assets have moved into `app/templates/` and `app/static/` (with ES-module JS controllers), paving the way for future bundlers without blocking legacy usage.

Remaining modularization work:

1. Optional asset bundling (Flask-Assets/esbuild) so the new JS modules can emit hashed builds for CDN caching.
2. Final audit for any helper functions still imported directly from the legacy monolith and migrate them into the services/tasks packages.
3. Broaden the automated test matrix (see `tests/`) to cover the newly extracted services once the bundling step is complete.

## 🔄 Differences vs the legacy GitHub release

Compared to the public `bareera786/ai-trading-bot` repository snapshot:

- **Safety controls** – `FINAL_HAMMER`, Binance credential encryption, and compliance toggles are enforced across services, whereas the public repo had manual safeguards only.
- **Documentation** – This README plus `docs/binance_compliance.md`, `docs/modularization_plan.md`, `docs/runtime_component_matrix.md`, and others document the new architecture, deployment paths, and review checklists.
- **Modular codebase** – The `app/` package, blueprints, and services/tasks do not exist in the old repo, which still relies on the single-file `ai_ml_auto_bot_final.py`.
- **Testing & automation** – A full `tests/` suite (user APIs, subscriptions, toggles, compliance probes, persistence) now backs the code; the legacy repo only had a handful of scripts.
- **Deployment experience** – Updated scripts (`deploy_to_vps_complete.sh`, `scripts/deploy_to_vps.sh`, systemd helpers) and the README’s production checklist reflect real-world operations and compliance steps absent in the older version.

These deltas are intentionally kept in this workspace for review before we push them to GitHub; once you’re ready, committing and pushing this README plus the modular code will update the online repo.
## 🧭 Modularization Progress

The repository is mid-flight from the legacy single-file app toward a modular Flask package housed in `app/`. Most services, background workers, and blueprints have already moved; outstanding work focuses on finalising the `create_app` factory, trimming duplicated endpoints, and modernising the asset pipeline. For the full milestone tracker and detailed checklist, see `docs/modularization_plan.md`.

## ⚙️ Configuration

### Trading Parameters
- **Confidence Threshold**: 0.45-0.52 (dynamic)
- **Max Positions**: 3 concurrent trades
- **Risk per Trade**: 1% of portfolio
- **Take Profit**: 8%
- **Stop Loss**: 3%

### Signal Configuration
- **Primary Indicators**: RSI, MACD, Bollinger Bands, Stochastic, ADX
- **Ensemble Voting**: 75% agreement required
- **Market Regime Aware**: Automatic adaptation

## 🔧 API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - Authenticate user
- `POST /logout` - Logout user

### User Management
- `GET /api/users` - List all users (admin only)
- `POST /api/users` - Create a new user (admin only)
- `PUT /api/users/<username>` - Update user (admin only)
- `DELETE /api/users/<username>` - Delete user (admin only)

### Dashboard
- `GET /` - Main dashboard (redirects to login if not authenticated)
- `GET /api/dashboard` - Dashboard data
- `GET /api/status` - System status

### Trading
- `POST /api/trade` - Execute trade
- `GET /api/positions` - Current positions
- `DELETE /api/positions/{symbol}` - Close position

### Configuration
- `GET /api/config` - Current config
- `POST /api/config` - Update config
- `GET /api/symbols` - Available symbols

## 📊 Monitoring

### Health Checks
- Automatic backtesting validation
- API connectivity monitoring
- Balance verification
- Performance metrics

### Logs
- Rotating file logs in `bot_persistence/logs/`
- Debug logs with component-specific filtering

## 🛡️ Safety Features

### Risk Controls
- Daily loss limits (10% default)
- Position size limits (8% default)
- Consecutive loss circuit breakers
- Volatility-based trading halts

### Error Handling
- Graceful API failure recovery
- Fallback indicator calculations
- Automatic reconnection logic

### FINAL_HAMMER safeguard
- `FINAL_HAMMER=FALSE` is the default and blocks real-money or futures execution; paper trading, backtesting, and dashboard exploration all work normally in this mode.
- Set `FINAL_HAMMER=TRUE` only after confirming environment variables, balances, circuit breakers, and credentials. The bot validates this flag at startup and before each order, so failing to enable it keeps trading logic read-only.
- Follow the [FINAL_HAMMER Launch Checklist](docs/final_hammer_checklist.md) every time you promote a build. It captures the non-negotiables: build hashed dashboard assets via `npm run build:assets`, verify the Futures Manual Service endpoints (`/api/futures/manual`, `/api/futures/manual/select`, `/api/futures/manual/toggle`), and rerun the regression set (`pytest tests/test_public_landing.py tests/test_public_subscriptions.py tests/test_user_api.py tests/test_toggle.py tests/test_futures_toggle.py`).

## 🔍 Troubleshooting

### Common Issues

**TA-Lib Import Error**:
- The bot includes fallback implementations
- Install TA-Lib: `pip install TA-Lib`

**Binance API Errors**:
- Verify API keys in config
- Check testnet vs live mode
- Monitor API rate limits

**Memory Issues**:
- Reduce parallel processing cores
- Increase system RAM
- Use smaller datasets

### Diagnostic Tools
```bash
# Run system diagnostics
python scripts/status_diagnostics.py

# Check backtest health
python scripts/backtest_health_check.py

# View logs
tail -f bot_persistence/logs/bot.log
```

## 📈 Performance

### Backtesting Results
- Sharpe Ratio: Target > 1.5
- Win Rate: Target > 60%
- Max Drawdown: Target < 15%
- Annual Return: Variable by market conditions

### Live Trading
- Paper trading mode available
- Testnet validation recommended
- Gradual position sizing advised

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is for educational and research purposes. Use at your own risk.

## ⚠️ Disclaimer

Cryptocurrency trading involves significant risk. This software is provided as-is without warranty. Past performance does not guarantee future results. Always test thoroughly before live trading.

---

## GitHub Setup Instructions

1. **Create Repository**:
   - Go to [GitHub.com](https://github.com) and create a new repository
   - Name: `ai-trading-bot`
   - Description: Complete AI/ML Trading Bot with Flask Admin Panel
   - Make it Public or Private as preferred
   - **Important**: Don't initialize with README, .gitignore, or license

2. **Push Code to GitHub**:
```bash
# After creating the repository, run these commands:
git remote add origin https://github.com/YOUR_USERNAME/ai-trading-bot.git
git branch -M main
git push -u origin main
```

3. **Verify Upload**:
   - Check your GitHub repository to ensure all files are uploaded
   - The repository should contain all bot files, scripts, and documentation
