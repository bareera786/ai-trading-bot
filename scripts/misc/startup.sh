#!/bin/bash
# AI Trading Bot Startup Script
cd /home/aibot/ai-bot
source .venv/bin/activate
# Load configuration from deploy.env.production
if [ -f "config/deploy.env.production" ]; then
    export $(grep -v '^#' config/deploy.env.production | xargs)
fi
export PYTHONPATH=/home/aibot/ai-bot/.venv/lib/python3.11/site-packages
export FLASK_ENV=production
unset FLASK_APP
exec python ai_ml_auto_bot_final.py
