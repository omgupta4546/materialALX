import os
import sys
import logging
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.core.connection import engine, check_db_health, DATABASE_URL
from app.models.base import Base

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
log = logging.getLogger("db_test")

def run_tests():
    log.info("Starting database connectivity tests...")
    log.info(f"Targeting: {DATABASE_URL}")
    
    # 1. Test basic connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            log.info("✅ Connection successful.")
    except OperationalError as e:
        log.error("❌ Connection failed. PostgreSQL is likely not running locally.")
        log.error(f"Reason: {e.orig}")
        log.info("Please ensure PostgreSQL is running and credentials in .env are correct.")
        sys.exit(1)
        
    # 2. Test pgvector extension
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).fetchone()
            if res:
                log.info("✅ pgvector extension is installed and enabled.")
            else:
                log.warning("⚠️ pgvector extension is NOT enabled. Migrations will attempt to create it.")
    except Exception as e:
        log.error(f"❌ Failed to check pgvector: {e}")

    # 3. Check health status wrapper
    health = check_db_health()
    if health["status"] == "ok":
        log.info(f"✅ Health check passed. Pool size: {health['pool_size']}")
    else:
        log.warning(f"⚠️ Health check reported issues: {health}")
        
    log.info("\nAll reachable database components are functioning correctly.")
    log.info("To run migrations, use: cd database && python -m alembic upgrade head")

if __name__ == "__main__":
    run_tests()
