#!/usr/bin/env python3
import sqlite3

try:
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO user_portfolio (user_id, symbol, quantity) VALUES (1, "TEST", 1)')
    conn.commit()
    print('Write successful')
except Exception as e:
    print(f'Write failed: {e}')
finally:
    conn.close()