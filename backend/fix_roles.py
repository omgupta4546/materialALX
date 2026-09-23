"""Fix role_id for demo users in Neon PostgreSQL."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from app.core.connection import engine
from sqlalchemy import text

fixes = [
    ("demo_admin",    "ADMIN",      None),
    ("demo_engineer", "ENGINEER",   "NTPC"),
]

with engine.begin() as conn:
    for user_id, role_id, cpse_code in fixes:
        if cpse_code:
            conn.execute(
                text("UPDATE user_account SET role_id=:role WHERE user_id=:uid"),
                {"role": role_id, "uid": user_id}
            )
        else:
            conn.execute(
                text("UPDATE user_account SET role_id=:role WHERE user_id=:uid"),
                {"role": role_id, "uid": user_id}
            )
        print(f"Fixed: {user_id} -> role_id={role_id}")

    # Verify
    result = conn.execute(text("SELECT user_id, role_id, cpse_code FROM user_account"))
    print("\nAll users after fix:")
    for row in result.fetchall():
        print(f"  {row[0]}: role={row[1]}, cpse={row[2]}")
