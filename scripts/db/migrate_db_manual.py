
import sys
import os
from sqlalchemy import text, create_engine

# Use the database URL directly (app.db in root)
env_url = os.environ.get("DATABASE_URL")
if env_url and env_url.startswith("sqlite"):
    # generic naive parsing
    # verify if it's relative or absolute
    if "///" in env_url:
        path = env_url.split("///")[1]
        if not os.path.isabs(path):
            db_url = f"sqlite:///{os.path.join(os.getcwd(), path)}"
        else:
            db_url = env_url
    else:
        db_url = env_url
else:
    db_url = f"sqlite:///{os.path.join(os.getcwd(), 'app.db')}"

print(f"Migrating DB at: {db_url}")
engine = create_engine(db_url)

def migrate_schema():
    with engine.connect() as conn:
        print("Connected to DB.")
        
        # 1. Check is_admin
        try:
            conn.execute(text("SELECT is_admin FROM user LIMIT 1"))
            print("is_admin column already exists.")
        except Exception:
            print("Column is_admin missing. Adding it...")
            conn.execute(text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
            
            # Backfill based on role
            print("Backfilling is_admin from role...")
            try:
                conn.execute(text("UPDATE user SET is_admin = 1 WHERE role = 'admin'"))
                conn.execute(text("UPDATE user SET is_admin = 0 WHERE role != 'admin' OR role IS NULL"))
            except Exception as e:
                print(f"Warning during backfill: {e}")

        # 2. Check last_login_at
        try:
            conn.execute(text("SELECT last_login_at FROM user LIMIT 1"))
            print("last_login_at column already exists.")
        except Exception:
            print("Column last_login_at missing. Adding it...")
            conn.execute(text("ALTER TABLE user ADD COLUMN last_login_at DATETIME"))

        # 3. Check selected_symbols
        try:
            conn.execute(text("SELECT selected_symbols FROM user LIMIT 1"))
            print("selected_symbols column already exists.")
        except Exception:
            print("Column selected_symbols missing. Adding it...")
            conn.execute(text("ALTER TABLE user ADD COLUMN selected_symbols TEXT DEFAULT '[]'"))

        # 4. Check custom_symbols
        try:
            conn.execute(text("SELECT custom_symbols FROM user LIMIT 1"))
            print("custom_symbols column already exists.")
        except Exception:
            print("Column custom_symbols missing. Adding it...")
            conn.execute(text("ALTER TABLE user ADD COLUMN custom_symbols TEXT DEFAULT '[]'"))

        # 5. Check failed_login_count
        try:
            conn.execute(text("SELECT failed_login_count FROM user LIMIT 1"))
            print("failed_login_count column already exists.")
        except Exception:
            print("Column failed_login_count missing. Adding it...")
            conn.execute(text("ALTER TABLE user ADD COLUMN failed_login_count INTEGER DEFAULT 0"))
            
        # 6. Check locked_until
        try:
            conn.execute(text("SELECT locked_until FROM user LIMIT 1"))
            print("locked_until column already exists.")
        except Exception:
            print("Column locked_until missing. Adding it...")
            conn.execute(text("ALTER TABLE user ADD COLUMN locked_until DATETIME"))

        conn.commit()
        print("✅ Migration complete.")

if __name__ == "__main__":
    migrate_schema()
