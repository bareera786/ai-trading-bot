#!/bin/bash
# Debug: Log what we're doing
echo "Starting AI Trading Bot..." >&2
cd /home/aibot/ai-bot || exit 1
echo "Changed to directory: $(pwd)" >&2
source .venv/bin/activate || exit 1
echo "Activated virtual environment" >&2
exec python ai_ml_auto_bot_final.py