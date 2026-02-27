import sqlite3
import os

db_path = "data/livecalc.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Existing tables:")
    for table in tables:
        print(f"  - {table[0]}")
    conn.close()
else:
    print(f"Database {db_path} does not exist")