"""Fix users in Neon PostgreSQL DB."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.core.connection import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Check current users
    result = conn.execute(text("SELECT user_id, name, role_id, cpse_code FROM user_account LIMIT 10"))
    rows = result.fetchall()
    print("Current users:")
    for row in rows:
        print(f"  user_id={row[0]}, name={row[1]}, role_id={row[2]}, cpse_code={row[3]}")
    
    # Check roles table
    result2 = conn.execute(text("SELECT id FROM role"))
    roles = [r[0] for r in result2.fetchall()]
    print(f"\nExisting roles: {roles}")
