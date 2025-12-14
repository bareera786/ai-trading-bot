# Quick Start Guide

## 🚀 10-Step Setup for Paper Trading

This guide gets you trading safely with paper money in under 30 minutes.

### ⚠️ Safety First
- **Paper trading only** - No real money at risk
- **Test environment** - Isolated from production
- **Learn first** - Master strategies before live trading

### Prerequisites
- Python 3.11+
- Git
- Docker (optional, but recommended)

### Step 1: Clone Repository
```bash
git clone https://github.com/yourusername/ai-trading-bot.git
cd ai-trading-bot
```

### Step 2: Set Up Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment
```bash
cp config/deploy.env.example config/deploy.env
# Edit config/deploy.env with your settings
```

### Step 5: Set Up Database
```bash
# Using Docker (recommended)
docker run -d --name postgres-trading \
  -e POSTGRES_DB=trading_bot \
  -e POSTGRES_USER=trading_user \
  -e POSTGRES_PASSWORD=your_password \
  -p 5432:5432 postgres:15

# Or install PostgreSQL locally
```

### Step 6: Initialize Database
```bash
python -c "from app import create_app; app = create_app(); app.app_context().push(); from app.extensions import db; db.create_all()"
```

### Step 7: Configure Binance Testnet
```bash
# Get testnet API keys from https://testnet.binance.vision/
# Add to config/deploy.env:
BINANCE_API_KEY=your_testnet_api_key
BINANCE_SECRET_KEY=your_testnet_secret_key
PAPER_TRADING=true
```

### Step 8: Run Health Check
```bash
python -m flask run
# Visit http://localhost:5000/health
```

### Step 9: Start Paper Trading
```bash
python ai_ml_auto_bot_final.py --paper-trading --testnet
```

### Step 10: Monitor Dashboard
- Open http://localhost:5000
- Watch real-time performance
- Review trade history
- Adjust strategies

## 🎯 Next Steps
1. **Learn the Interface** - Explore all dashboard features
2. **Backtest Strategies** - Test on historical data
3. **Customize Parameters** - Tune for your risk tolerance
4. **Add Real Money** - Only after extensive paper trading

## 🆘 Getting Help
- Check `/health` endpoint for system status
- Review logs in `logs/` directory
- Join our Discord community
- Read the full documentation

## ⚡ Quick Commands
```bash
# Start development server
python -m flask run

# Run with Docker
docker-compose up

# Run tests
pytest

# Check code quality
ruff check .
```

Happy trading! 📈
