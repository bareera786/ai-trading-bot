# AI Trading Bot - Ultimate Professional Version

A comprehensive AI-powered cryptocurrency trading bot with advanced machine learning, parallel processing, and enterprise-grade features.

## 🚀 Features

### Core Capabilities
- **Advanced ML Models**: Random Forest, Gradient Boosting, Voting Classifier
- **Parallel Processing**: Joblib-based multi-core signal generation
- **Real-time Trading**: Live Binance API integration with testnet support
- **Comprehensive Indicators**: 20+ technical indicators with TA-Lib fallbacks
- **Multi-timeframe Analysis**: 1h, 4h, 1d, 1w analysis

### Signal Generation Modules
- **CRT (Composite Rhythm Trading)**: Multi-timeframe momentum analysis
- **ICT (Inner Circle Trader)**: Institutional trading patterns
- **SMC (Smart Money Concepts)**: Market structure analysis
- **Quantum Fusion Momentum**: Advanced momentum indicators

### Safety & Risk Management
- **Dynamic Position Sizing**: Risk-adjusted position management
- **Circuit Breakers**: Automatic trading halts on loss streaks
- **Volatility Filters**: Market stress detection
- **API Failure Handling**: Robust error recovery

### Professional Features
- **Comprehensive Trade History**: Detailed P&L tracking
- **Backtesting Engine**: Historical performance analysis
- **Web Dashboard**: Real-time monitoring interface
- **Configurable Profiles**: Multiple trading strategies
- **Logging & Monitoring**: Enterprise-grade logging

## 📋 Requirements

- Python 3.8+
- Binance API keys (for live trading)
- 8GB+ RAM recommended
- Multi-core CPU for parallel processing

## 🛠️ Installation

1. **Clone and Setup**:
```bash
cd /Users/tahir/Desktop/ai-bot
pip install -r requirements.txt
```

2. **Environment Configuration**:
```bash
# Copy environment template
cp config/deploy.env.example config/.env

# Edit with your settings
nano config/.env
```

3. **Binance API Setup** (Optional for live trading):
```bash
# Add to config/.env
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BOT_PROFILE=default
```

## 🚀 Usage

### Development Mode
```bash
python ai_ml_auto_bot_final.py
```

The bot will start a web server at `http://localhost:5000`

### Production Deployment
```bash
# Using the deployment script
bash scripts/deploy.sh
```

### Backtesting
```bash
python scripts/backtest_health_check.py
```

## 📁 Project Structure

```
ai-bot/
├── ai_ml_auto_bot_final.py    # Main trading bot
├── requirements.txt           # Python dependencies
├── config/
│   └── deploy.env.example     # Environment template
├── scripts/
│   ├── status_diagnostics.py      # System diagnostics
│   ├── backtest_health_check.py  # Backtesting utilities
│   └── deploy.sh                 # Deployment script
├── trade_data/                 # Trade history storage
├── artifacts/                  # ML model artifacts
├── reports/                    # Backtest reports
└── logs/                       # Application logs
```

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


### User Management
- `GET /api/users` - List all users
- `POST /api/users` - Create a new user
- `DELETE /api/users/<username>` - Delete a user (admin only, use username not user ID)

### Dashboard
- `GET /` - Main dashboard
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
- Rotating file logs in `logs/bot.log`
- Debug logs in `logs/bot.debug.log`
- Component-specific filtering

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
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## 📄 License

This project is for educational and research purposes. Use at your own risk.

## ⚠️ Disclaimer

Cryptocurrency trading involves significant risk. This software is provided as-is without warranty. Past performance does not guarantee future results. Always test thoroughly before live trading.

# AI Bot: State-of-the-Art User Management & Admin Dashboard

## Flask User Management & Admin Dashboard (2025 Update)

### Overview
The AI trading bot now features a fully integrated, state-of-the-art user management and admin dashboard system—directly in the Flask UI. All user/admin management, robot control, and config editing are available from the main dashboard at `http://localhost:5000`.

### Key Features
- **User Management:**
  - List, add, edit, and delete users (admin-only)
  - Assign admin/user roles
  - Activate/deactivate users
  - View last login, creation date, and status
- **Admin Dashboard:**
  - Real-time user CRUD via dashboard
  - Robot control panel (start/stop/restart)
  - Config editor (view/edit bot config)
  - System status, trade history, and analytics
- **Security:**
  - Session management, RBAC, admin-only endpoints
  - Secure password handling

### Quick Start

1. **Install Requirements**
	```bash
	pip install -r requirements.txt
	```

2. **Run Flask Bot Locally**
	```bash
	FLASK_APP=ai_ml_auto_bot_final.py flask run
	# or
	.venv/bin/python -m flask run
	```
	- Access the dashboard at `http://localhost:5000`

3. **User Management Demo**
	- Log in as admin
	- Use the dashboard to add/edit/delete users
	- Assign roles and manage user status

4. **Admin Features**
	- Control bot (start/stop/restart)
	- Edit config files from dashboard
	- View system status and analytics

### API Endpoints (Flask)

- `GET /api/users` — List all users (admin-only)
- `POST /api/users` — Create new user (admin-only)
- `GET /api/users/<username>` — Get user details (admin-only)
- `PUT /api/users/<username>` — Update user (admin-only)
- `DELETE /api/users/<username>` — Delete user (admin-only)
- `GET /api/dashboard` — Dashboard data
- `POST /api/trade` — Execute trade
- `GET /api/positions` — Current positions
- `GET /api/config` — Get config
- `POST /api/config` — Update config

### Dashboard Usage
- All user/admin management is available in the dashboard UI (no separate frontend needed)
- Real-time updates: Add, edit, delete users instantly
- Robot and config controls are accessible from the admin panel

### Folder Structure (Relevant to Flask UI)
- `ai_ml_auto_bot_final.py` — Main Flask app, backend logic, dashboard UI
- `database_layer/` — Modular DB logic
- `robot_module/` — Bot control functions
- `configs/` — Config files and prompts
- `api_routes/` — API route handlers

---

For full instructions, see the dashboard at `http://localhost:5000` or review the code in `ai_ml_auto_bot_final.py`.