#!/bin/bash
# fix_dashboard.sh

echo "=== Dashboard Fix Script ==="

# Kill existing processes
echo "1. Stopping existing servers..."
pkill -f "flask run" 2>/dev/null
pkill -f "start_server.py" 2>/dev/null
pkill -f "python.*5000" 2>/dev/null

# Activate venv
echo "2. Activating virtual environment..."
source .venv/bin/activate 2>/dev/null || {
    echo "Creating new virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
}

# Install deps
echo "3. Installing dependencies..."
pip install -r requirements.txt --upgrade 2>/dev/null || pip install flask flask-sqlalchemy

# Set env vars
echo "4. Setting environment variables..."
export FINAL_HAMMER=FALSE
export FLASK_ENV=development
export DATABASE_URL="sqlite:///temp_dashboard.db"
export FLASK_APP=start_server.py

# Start server
echo "5. Starting server on port 5000..."
echo "Dashboard will be at: http://localhost:5000"
echo "Press Ctrl+C to stop"
echo "----------------------------------------"

python -m flask run --host=0.0.0.0 --port=5000 --reload