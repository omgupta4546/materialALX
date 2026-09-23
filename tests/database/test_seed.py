import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../database')))

from seed_database import SeedEngine
from seed_config import SeedConfig
from app.models.base import Base, CPSE, SourceMaterial

# We assume a test postgres instance is available at this URL
TEST_DB_URL = os.environ.get('TEST_DB_URL', 'postgresql://postgres:postgres@localhost:5432/test_material_db')

@pytest.fixture(scope="module")
def db_engine():
    engine = create_engine(TEST_DB_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="module")
def seed_engine():
    config = SeedConfig()
    # Ensure it looks at the correct paths from project root
    config.reference_dir = "data/reference"
    config.demo_dir = "data/demo"
    return SeedEngine(TEST_DB_URL, config)

def test_reference_data_seeding(seed_engine, db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    try:
        seed_engine.seed_cpses(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
        
    # Check CPSEs were inserted
    cpse_count = session.query(CPSE).count()
    assert cpse_count > 0, "CPSEs were not seeded"

def test_idempotency(seed_engine, db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    
    # Run full demo seed
    try:
        seed_engine.seed_cpses(session)
        seed_engine.seed_source_materials(session, is_demo=True)
        session.commit()
    except Exception:
        session.rollback()
        raise
        
    initial_material_count = session.query(SourceMaterial).count()
    assert initial_material_count > 0, "Materials were not seeded"
    
    # Run second time
    try:
        seed_engine.seed_source_materials(session, is_demo=True)
        session.commit()
    except Exception:
        session.rollback()
        raise
        
    second_material_count = session.query(SourceMaterial).count()
    
    # Assert idempotency
    assert initial_material_count == second_material_count, "Idempotency failed: counts diverged after second run"
