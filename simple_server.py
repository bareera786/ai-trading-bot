#!/usr/bin/env python3
"""
Simple Flask server runner for testing - without signal handlers
"""

import sys
import os
import signal

# Disable signal handlers to prevent shutdown
def signal_handler(signum, frame):
    pass

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

sys.path.insert(0, '.')

# Set minimal environment to avoid full initialization
os.environ['BOT_PROFILE'] = 'default'

# Import just the Flask app without running full initialization
from flask import Flask
from ai_ml_auto_bot_final import app

if __name__ == '__main__':
    print("Starting Flask server for testing (signal handlers disabled)...")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)