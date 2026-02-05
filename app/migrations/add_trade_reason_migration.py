from sqlalchemy import text
from app import create_app
from app.extensions import db
from dotenv import load_dotenv
import os

load_dotenv()

def upgrade():
    app = create_app()
    with app.app_context():
        # Check if columns exist
        with db.engine.connect() as conn:
            # Check 'reason' column
            try:
                result = conn.execute(text("SELECT reason FROM user_trade LIMIT 1"))
                print("Column 'reason' already exists.")
            except Exception:
                print("Adding column 'reason'...")
                conn.execute(text("ALTER TABLE user_trade ADD COLUMN reason VARCHAR(255)"))
                conn.commit()

            # Check 'details' column
            try:
                result = conn.execute(text("SELECT details FROM user_trade LIMIT 1"))
                print("Column 'details' already exists.")
            except Exception:
                print("Adding column 'details'...")
                conn.execute(text("ALTER TABLE user_trade ADD COLUMN details JSONB DEFAULT '{}'")) # Use JSONB for Postgres, JSON for others? 
                # Flask-SQLAlchemy usually handles this but raw SQL needs care.
                # Assuming Postgres based on previous file views (psycopg2).
                # But to be safe, maybe just JSON? SQLite uses JSON. Postgres uses JSONB preferred.
                # Let's try flexible SQL.
                try: 
                     conn.execute(text("ALTER TABLE user_trade ADD COLUMN details JSONB DEFAULT '{}'"))
                except:
                     conn.execute(text("ALTER TABLE user_trade ADD COLUMN details JSON DEFAULT '{}'"))

                conn.commit()
                
        print("Migration complete.")

if __name__ == "__main__":
    upgrade()
