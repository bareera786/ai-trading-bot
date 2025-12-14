# 🚀 Quick Start Guide - AI Trading Bot

## ⚠️ IMPORTANT SAFETY NOTICE
**This bot can lose money!** Start with paper trading only. Never risk money you can't afford to lose.

---

## 🎯 5-Minute Setup for Beginners

### Step 1: Get the Code
```bash
git clone https://github.com/bareera786/ai-trading-bot.git
cd ai-trading-bot
```

### Step 2: Install Everything
```bash
# Install Python (if needed) and create environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Quick Configuration
```bash
# Copy example config
cp config/deploy.env.example config/deploy.env

# Edit the config file (open in any text editor)
# Add your Binance testnet API keys (get free ones at https://testnet.binance.vision)
```

### Step 4: Start Safe Trading
```bash
# Start the bot in safe mode
python start_server.py
```

### Step 5: Open Dashboard
- Visit: http://localhost:5000
- Check health: http://localhost:5000/health
- Start paper trading from the dashboard

---

## 🔧 Detailed Setup (For Advanced Users)

### Database Setup
```bash
# Quick Docker database (recommended)
docker run -d --name trading-db \
  -e POSTGRES_PASSWORD=mypassword \
  -p 5432:5432 postgres:15

# Or use the full docker-compose setup
docker-compose up -d
```

### Environment Configuration
Edit `config/deploy.env`:
```bash
# Required for trading
BINANCE_API_KEY=your_testnet_key_here
BINANCE_SECRET_KEY=your_testnet_secret_here

# Safety settings (start with these)
USE_TESTNET=1
ENABLE_AUTO_TRADING=0
ENABLE_FUTURES_TRADING=0
PAPER_TRADING=1
```

### Verify Installation
```bash
# Check everything works
python -c "import ai_ml_auto_bot_final; print('✅ Bot ready!')"

# Start web interface
python start_server.py

# Visit http://localhost:5000/health for status
```

---

## 🎮 Using the Dashboard

1. **Health Check**: Visit `/health` to see system status
2. **Paper Trading**: Enable safe trading mode first
3. **Backtesting**: Test strategies on historical data
4. **Monitoring**: Watch real-time performance
5. **Configuration**: Adjust settings safely

---

## 🆘 Need Help?

- **Health Check**: `http://localhost:5000/health`
- **Logs**: Check `logs/` directory
- **Configuration**: See `config/deploy.env.example`
- **Documentation**: Read `README.md` and `docs/`

---

## ⚡ Quick Commands Reference

```bash
# Start development
python start_server.py

# Start with Docker
docker-compose up

# Run tests
pytest

# Check code quality
ruff check .

# View logs
tail -f logs/ai_trading_bot.log
```

**Happy Safe Trading! 📈** (Remember: Paper trade first!)
