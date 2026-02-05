
import sqlite3
import os

db_path = "instance/trading_bot.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("Creating copy_relationship table if not exists...")
sql = """
CREATE TABLE IF NOT EXISTS copy_relationship (
    id INTEGER PRIMARY KEY,
    follower_id CHAR(32) NOT NULL,
    leader_id CHAR(32) NOT NULL,
    allocation_amount NUMERIC(20, 8) DEFAULT 0.0,
    stop_loss_percent INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT 1,
    total_copied_pnl NUMERIC(20, 8) DEFAULT 0.0,
    created_at DATETIME,
    FOREIGN KEY(follower_id) REFERENCES user(id),
    FOREIGN KEY(leader_id) REFERENCES user(id)
);
"""
try:
    cursor.execute(sql)
    print("Table copy_relationship created successfully.")
except Exception as e:
    print(f"Error creating table: {e}")

conn.commit()
conn.close()
