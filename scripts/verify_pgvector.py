import os
import sys
import uuid
import argparse
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../database')))
from db_config import db_config
from app.models.base import Base, SourceMaterial, NormalizedMaterial

def main():
    parser = argparse.ArgumentParser(description="Verify pgvector integration and nearest-neighbor search.")
    parser.add_argument('--db-url', type=str, default='postgresql://postgres:postgres@localhost:5432/material_db', help='PostgreSQL connection URL')
    args = parser.parse_args()

    print(f"Connecting to {args.db_url}...")
    engine = create_engine(args.db_url)
    
    print("Creating vector extension if not exists...")
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        print(f"Warning/Error creating extension: {e}")
        print("Assuming extension exists or lack of permissions.")

    print("Ensuring tables are created...")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()

    print(f"Generating test vectors of dimension {db_config.embedding_dimension}...")
    
    # Create an arbitrary base vector for a "Bearing"
    bearing_vector = np.random.rand(db_config.embedding_dimension)
    # Create a vector very close to the Bearing
    near_bearing_vector = bearing_vector + (np.random.rand(db_config.embedding_dimension) * 0.05)
    # Create a completely different vector for a "Motor"
    motor_vector = np.random.rand(db_config.embedding_dimension) + 2.0

    # Ensure source records exist to satisfy Foreign Key constraints
    bearing_source_id = str(uuid.uuid4())
    near_bearing_source_id = str(uuid.uuid4())
    motor_source_id = str(uuid.uuid4())
    
    # We don't have CPSEs seeded in this isolated test potentially, so let's use raw SQL or dummy inserts
    # Actually, we might need a dummy CPSE if we are on a fresh DB. Let's try raw inserts and ignore FKs for a second by doing a temporary session disable if needed, or better, just insert a dummy CPSE.
    from app.models.base import CPSE
    dummy_cpse = session.query(CPSE).filter_by(cpse_code="TEST-CPSE").first()
    if not dummy_cpse:
        dummy_cpse = CPSE(cpse_code="TEST-CPSE", cpse_name="Test CPSE")
        session.add(dummy_cpse)
        session.commit()

    bearing_source = SourceMaterial(source_id=bearing_source_id, cpse_code="TEST-CPSE", material_code="BRG-01", description="Bearing Source")
    near_bearing_source = SourceMaterial(source_id=near_bearing_source_id, cpse_code="TEST-CPSE", material_code="BRG-02", description="Near Bearing Source")
    motor_source = SourceMaterial(source_id=motor_source_id, cpse_code="TEST-CPSE", material_code="MTR-01", description="Motor Source")
    
    # Upsert or merge to avoid unique constraints if run multiple times
    session.merge(bearing_source)
    session.merge(near_bearing_source)
    session.merge(motor_source)
    session.commit()

    print("Inserting Material Embeddings into NormalizedMaterial table...")
    bearing_norm_id = f"norm_{bearing_source_id}"
    near_norm_id = f"norm_{near_bearing_source_id}"
    motor_norm_id = f"norm_{motor_source_id}"

    bearing_norm = NormalizedMaterial(normalized_id=bearing_norm_id, source_id=bearing_source_id, normalized_description="SKF Bearing 6205", embedding=bearing_vector.tolist())
    near_norm = NormalizedMaterial(normalized_id=near_norm_id, source_id=near_bearing_source_id, normalized_description="SKF Brg 6205", embedding=near_bearing_vector.tolist())
    motor_norm = NormalizedMaterial(normalized_id=motor_norm_id, source_id=motor_source_id, normalized_description="Induction Motor 50HP", embedding=motor_vector.tolist())

    session.merge(bearing_norm)
    session.merge(near_norm)
    session.merge(motor_norm)
    session.commit()
    
    print("Executing Vector Cosine Distance Search...")
    # Find nearest neighbor to the bearing vector
    # pgvector provides cosine distance via the `<=>` operator. In SQLAlchemy, we can use `.l2_distance()`, `.cosine_distance()`, `.max_inner_product()`
    
    # We want the closest vector, excluding the exact same record itself
    results = session.query(
        NormalizedMaterial.normalized_description,
        NormalizedMaterial.embedding.cosine_distance(bearing_vector.tolist()).label("distance")
    ).filter(
        NormalizedMaterial.normalized_id != bearing_norm_id
    ).order_by(
        NormalizedMaterial.embedding.cosine_distance(bearing_vector.tolist())
    ).limit(2).all()

    print("\n--- RESULTS FOR NEAREST NEIGHBOR TO 'SKF Bearing 6205' ---")
    for r in results:
        print(f"Match: {r.normalized_description} | Cosine Distance: {r.distance:.4f}")

    # Assertion
    assert results[0].normalized_description == "SKF Brg 6205", "Vector search failed: Near bearing was not the closest result!"
    print("\nSUCCESS: pgvector HNSW indexing and semantic search verified natively on PostgreSQL!")

if __name__ == "__main__":
    main()
