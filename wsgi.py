#!/usr/bin/env python3
"""
WSGI application for the AI Trading Bot
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')

from ai_ml_auto_bot_final import app

# WSGI application object
application = app

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=5000, debug=False, threaded=False)