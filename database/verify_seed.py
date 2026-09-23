import argparse
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import CPSE, Classification, UOMMaster, CriticalRule, User, SourceMaterial

def verify_seed(db_url: str):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    print("\n--- Verifying Seeding Statistics against PostgreSQL ---")

    try:
        cpse_count = session.query(CPSE).count()
        print(f"CPSE count: {cpse_count}")

        class_count = session.query(Classification).count()
        print(f"Classification count: {class_count}")

        uom_count = session.query(UOMMaster).count()
        print(f"UOM count: {uom_count}")

        rule_count = session.query(CriticalRule).count()
        print(f"CriticalRule count: {rule_count}")

        user_count = session.query(User).count()
        print(f"User count: {user_count}")

        sm_count = session.query(SourceMaterial).count()
        print(f"SourceMaterial count: {sm_count}")
        
        # Verify foreign keys
        print("\nVerifying Foreign Keys (SourceMaterial -> CPSE):")
        orphans = session.query(SourceMaterial).filter(
            ~SourceMaterial.cpse_id.in_(session.query(CPSE.cpse_id))
        ).count()
        print(f"Orphaned Source Materials (invalid cpse_id): {orphans}")

        if orphans > 0:
            print("FAILED: Integrity violation detected!")
            sys.exit(1)
        else:
            print("SUCCESS: All row counts and foreign keys verified.")
            
    except Exception as e:
        print(f"Error connecting or querying database: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--db-url', type=str, default='postgresql://postgres:postgres@localhost:5432/platform')
    args = parser.parse_args()
    verify_seed(args.db_url)
