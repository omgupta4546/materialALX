"""Fix users in DB - set roles and passwords for demo users."""
import sqlite3
import sys
import os

# Try to find the right DB file
db_candidates = [
    os.path.join(os.path.dirname(__file__), 'platform.db'),
    os.path.join(os.path.dirname(__file__), 'antigravity.db'),
]

db_path = None
for candidate in db_candidates:
    if os.path.exists(candidate):
        db_path = candidate
        print(f"Found DB: {db_path}")
        break

if not db_path:
    print("ERROR: No DB found!")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# List tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print(f"Tables: {tables}")

# Find the users table
user_table = None
for t in tables:
    if 'user' in t.lower():
        user_table = t
        print(f"User table: {user_table}")
        break

if user_table:
    cur.execute(f"PRAGMA table_info({user_table})")
    cols = [r[1] for r in cur.fetchall()]
    print(f"Columns: {cols}")

    cur.execute(f"SELECT * FROM {user_table} LIMIT 5")
    rows = cur.fetchall()
    for row in rows:
        print(row)

conn.close()
