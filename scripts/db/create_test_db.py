#!/usr/bin/env python3
"""Simple script to create the database tables for testing auth."""

import os
import sys
from pathlib import Path

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables
os.environ['DATABASE_URL'] = 'sqlite:///test_auth.db'
os.environ['SKIP_RUNTIME_BOOTSTRAP'] = '1'
os.environ['AI_BOT_TEST_MODE'] = '1'

from app import create_app
from app.extensions import db

def main():
    app = create_app()
    with app.app_context():
        # Drop all tables if they exist
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    main()