# 1. Kill any existing processes
pkill -f flask
pkill -f start_server
pkill -f python

# 2. Ensure virtual environment is activated
source .venv/bin/activate

# 3. Install all dependencies from requirements.txt
pip install -r requirements.txt --upgrade

# 4. Set required environment variables
export FINAL_HAMMER=FALSE
export FLASK_ENV=development
export DATABASE_URL="sqlite:///trading_bot.db"  # Use SQLite for quick test
export BOT_PROFILE=default
export SKIP_RUNTIME_BOOTSTRAP=1
export AI_BOT_TEST_MODE=1

# 5. Initialize database (if needed)
python -c "
from app import create_app, db
app = create_app()
with app.app_context():
    db.create_all()
    print('Database tables created')
"

# 6. Try the simple server first
python simple_server.py