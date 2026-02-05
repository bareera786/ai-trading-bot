import sys
import os
import sqlalchemy
from sqlalchemy import text

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.config import Config

app = create_app(Config)

def fix_schema():
    with app.app_context():
        print("🔧 connecting to database...")
        engine = db.engine
        
        # Ensure ALL tables exist (fixes missing 'candles' etc)
        print("📦 Running db.create_all()...")
        db.create_all()
        print("✅ db.create_all() complete.")
        
        with engine.connect() as conn:
            # 1. Handle RoleEnum (Safe creation)
            print("Checking RoleEnum...")
            try:
                # Postgres specific: Check if type exists
                result = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'roleenum'"))
                if not result.fetchone():
                    print("Creating roleenum type...")
                    conn.execute(text("CREATE TYPE roleenum AS ENUM ('admin', 'trader', 'viewer')"))
                    conn.commit()
                else:
                    print("Type 'roleenum' already exists.")
            except Exception as e:
                print(f"Warning checking enum: {e}")

            # 2. Add columns safely
            columns_to_add = [
                ("is_active", "BOOLEAN DEFAULT TRUE"),
                ("is_admin", "BOOLEAN DEFAULT FALSE"),
                ("created_at", "TIMESTAMP WITHOUT TIME ZONE DEFAULT now()"),
                ("last_login", "TIMESTAMP WITHOUT TIME ZONE"),
                ("failed_login_count", "INTEGER DEFAULT 0"),
                ("locked_until", "TIMESTAMP WITHOUT TIME ZONE"),
                ("selected_symbols", "TEXT DEFAULT '[]'"),
                ("custom_symbols", "TEXT DEFAULT '[]'")
            ]

            print("Checking columns...")
            for col_name, col_def in columns_to_add:
                try:
                    # Check if column exists
                    check_sql = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='user' AND column_name='{col_name}';
                    """)
                    if not conn.execute(check_sql).fetchone():
                        print(f"Adding missing column: {col_name}")
                        alter_sql = text(f"ALTER TABLE \"user\" ADD COLUMN {col_name} {col_def}")
                        conn.execute(alter_sql)
                        conn.commit()
                    else:
                        print(f"Column '{col_name}' already exists.")
                except Exception as e:
                    print(f"Error checking/adding {col_name}: {e}")
            
            print("✅ Schema fix complete.")

if __name__ == "__main__":
    try:
        fix_schema()
    except Exception as e:
        print(f"❌ Fatal error during schema fix: {e}")
        sys.exit(1)
