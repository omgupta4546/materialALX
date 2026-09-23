"""
init_db.py — Create all database tables for the National Material Intelligence Platform.

Run from the backend/ directory:
    python init_db.py

This script:
1. Creates the pgvector extension (if not already installed)
2. Creates all SQLAlchemy tables
3. Creates HNSW vector index on normalized_material.embedding
4. Prints a summary of what was created
"""
import os
import sys
import logging

# ── Ensure the backend package is importable ──────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
# Load backend .env explicitly (takes priority over root .env)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
from dotenv import load_dotenv
load_dotenv(_env_path, override=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

from sqlalchemy import text, inspect
from app.core.connection import engine
from app.models.base import Base


def create_pgvector_extension():
    """Install the pgvector extension — required before any Vector column can be created."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        log.info("✅ pgvector extension ready")
    except Exception as e:
        log.warning(f"⚠️  Could not create pgvector extension: {e}")


def create_tables():
    """Create all SQLAlchemy-declared tables, skipping HNSW index (created separately)."""
    # Temporarily remove HNSW index from NormalizedMaterial so CREATE TABLE works cleanly
    # We'll add the index after the table exists
    from app.models.base import NormalizedMaterial
    import sqlalchemy as sa

    hnsw_index = None
    table_args = list(NormalizedMaterial.__table_args__)
    new_table_args = []
    for arg in table_args:
        if isinstance(arg, sa.Index) and "hnsw" in str(arg.name).lower():
            hnsw_index = arg
        else:
            new_table_args.append(arg)
    NormalizedMaterial.__table_args__ = tuple(new_table_args)

    try:
        Base.metadata.create_all(bind=engine)
        log.info("✅ All tables created successfully")
    except Exception as e:
        log.error(f"❌ Error creating tables: {e}")
        raise
    finally:
        # Restore original table args
        if hnsw_index:
            NormalizedMaterial.__table_args__ = tuple(new_table_args) + (hnsw_index,)

    return hnsw_index


def create_hnsw_index():
    """Create HNSW approximate nearest-neighbour index on embedding column."""
    dim = int(os.getenv("VECTOR_DIMENSION", "768"))
    sql = f"""
        CREATE INDEX IF NOT EXISTS ix_normalized_embedding_hnsw
        ON normalized_material
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        log.info(f"✅ HNSW index created on embedding ({dim}d cosine)")
    except Exception as e:
        log.warning(f"⚠️  Could not create HNSW index (non-fatal for demo): {e}")


def list_created_tables():
    """Print a summary of all tables that now exist in the database."""
    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names())
    log.info(f"\n📋 Tables in database ({len(tables)} total):")
    for t in tables:
        col_count = len(inspector.get_columns(t))
        log.info(f"   {t:40s} ({col_count} columns)")


if __name__ == "__main__":
    log.info("=" * 60)
    log.info("National Material Intelligence Platform — DB Init")
    log.info("=" * 60)

    is_sqlite = engine.url.drivername.startswith("sqlite")

    if not is_sqlite:
        create_pgvector_extension()

    hnsw_idx = create_tables()

    if not is_sqlite and hnsw_idx is not None:
        create_hnsw_index()

    list_created_tables()

    log.info("\n✅ Database initialization complete! Run seed_demo.py next.")
