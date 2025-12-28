#!/usr/bin/env python3
"""
Development server for the AI Trading Bot
"""
import os

# Set development environment
os.environ.setdefault("FLASK_ENV", "development")

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
