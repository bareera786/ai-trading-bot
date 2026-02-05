#!/bin/bash
# Start Bot Locally for Testing

# 1. Set Environment (Development)
export FLASK_ENV=development
export FLASK_APP=wsgi.py
export FLASK_DEBUG=1

# 2. Check dependencies
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo "⚠️  No virtual environment found. Make sure you have dependencies installed."
fi

# 3. Quick DB Migration (if needed)
echo "🔄 Checking Database Migrations..."
# Apply the manual migration we created if needed, or just upgrade head
python3 -m flask db upgrade || echo "⚠️  Migration command failed (DB might be up to date or not init)"

# 4. Start Bot
echo " Starting Bot..."
export FLASK_APP=wsgi.py
flask run --host=0.0.0.0 --port=5000
