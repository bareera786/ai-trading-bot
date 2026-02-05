#!/usr/bin/env python3
"""
Entry point for the AI Trading Bot.
Delegates to app/main_bot.py.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.main_bot import main

if __name__ == "__main__":
    main()
