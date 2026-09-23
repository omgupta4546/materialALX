"""
database/db_config.py — Centralised configuration for the database layer.
"""

from dataclasses import dataclass, field
from typing import List
import os


@dataclass
class DbConfig:
    # pgvector
    embedding_dimension: int = int(os.getenv("VECTOR_DIMENSION", "768"))
    hnsw_m: int = 16                    # HNSW graph edges per node (8-64)
    hnsw_ef_construction: int = 64      # build-time recall/speed trade-off

    # Pool
    pool_size: int    = int(os.getenv("DB_POOL_SIZE", "10"))
    max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # seconds

    # Pagination defaults
    default_page_size: int = 50
    max_page_size: int     = 200

    # Matching thresholds
    min_match_score: float     = float(os.getenv("MIN_MATCH_SCORE", "0.50"))
    exact_match_threshold: float = float(os.getenv("EXACT_MATCH_THRESHOLD", "0.98"))


db_config = DbConfig()
