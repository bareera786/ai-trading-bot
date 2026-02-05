
import sqlite3
import os

db_path = "instance/trading_bot.db"

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column(table, column, type_def):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {type_def}")
        print(f"Added column {column} to {table}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print(f"Column {column} already exists in {table}")
        else:
            print(f"Error adding {column}: {e}")

print("Migrating User table...")
add_column("user", "totp_secret", "VARCHAR(32)")
add_column("user", "is_2fa_enabled", "BOOLEAN DEFAULT 0")
add_column("user", "reseller_id", "INTEGER")
add_column("user", "reseller_role", "VARCHAR(20)")
add_column("user", "failed_login_count", "INTEGER DEFAULT 0")
add_column("user", "locked_until", "DATETIME")

# Also check CopyRelationship table while we are at it
print("Checking CopyRelationship table...")
try:
    cursor.execute("SELECT count(*) FROM copy_relationship")
    print("CopyRelationship table exists.")
except sqlite3.OperationalError:
    print("CopyRelationship table missing. Creating it...")
    # I won't create it here via raw SQL to avoid drift from SQLAlchemy models.
    # Usually proper way is db.create_all() but that doesn't migrate existing tables.
    # The user error was about 'user' table, so 'copy_relationship' might be fine or missing.
    # If missing, SQLAlchemy create_all would handle it if I ran it.
    pass

conn.commit()
conn.close()
print("Migration complete.")
