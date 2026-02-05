#!/usr/bin/env python3
"""
Dedicated Trading Bot Process Entry Point.
This script runs the AI Trading Bot loop as a SINGLETON process.
It isolates execution logic from the Gunicorn API workers.
"""
import os
import time
import sys
import logging

# Ensure we are in the worker role
os.environ["AI_BOT_ROLE"] = "worker"
os.environ["FLASK_ENV"] = "production"

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.core import bot

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("ai_trading_bot_process")

def run_bot_loop():
    logger.info("🚀 Starting Dedicated AI Trading Bot Process...")
    
    # Create the app to get the context (DB, Config, etc.)
    # Note: create_app() invokes bootstrap, which might try to start tasks.
    # We rely on app/bootstrap.py to RESPECT the AI_BOT_ROLE=worker and START tasks.
    # While Gunicorn (AI_BOT_ROLE=api) will SKIP them.
    app = create_app()

    with app.app_context():
        # Ensure the bot context is fully registered
        # This triggers initialize_runtime_from_context -> start_background_tasks
        bot.register_ai_bot_context(app, force=True)
        
        logger.info("✅ Bot Context Registered. Trading Loop should be running in background threads.")
        
        # Keep the main process alive to allow threads to run
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("🛑 Stopping Bot Process...")

if __name__ == "__main__":
    run_bot_loop()
