import os
import json
import csv
import argparse
import sys
import uuid
import hashlib
from typing import Dict, Any, List
from datetime import datetime

# Add backend to path for importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

from app.models.base import (
    Base, CPSE, Classification, UOMMaster, Synonym, CriticalRule, AttributeDefinition,
    User, Role, SourceMaterial, ProcurementRecord, GroundTruth
)
from seed_config import SeedConfig
from seed_validators import CPSEValidator, SourceMaterialValidator, validate_dict

def load_json(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def generate_uuid(text: str) -> str:
    return str(uuid.UUID(hashlib.md5(text.encode()).hexdigest()))

class SeedEngine:
    def __init__(self, db_url: str, config: SeedConfig):
        self.engine = create_engine(db_url)
        try:
            with self.engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            print(f"Warning: Could not create pgvector extension: {e}")
            
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.config = config
        self.stats = {
            'CPSE': {'upserted': 0, 'rejected': 0},
            'Classification': {'upserted': 0, 'rejected': 0},
            'UOM': {'upserted': 0, 'rejected': 0},
            'Synonym': {'upserted': 0, 'rejected': 0},
            'CriticalRule': {'upserted': 0, 'rejected': 0},
            'AttributeDefinition': {'upserted': 0, 'rejected': 0},
            'User': {'upserted': 0, 'rejected': 0},
            'SourceMaterial': {'upserted': 0, 'rejected': 0},
            'ProcurementRecord': {'upserted': 0, 'rejected': 0},
            'GroundTruth': {'upserted': 0, 'rejected': 0},
        }

    def _pg_upsert(self, session, model_class, records: List[dict], index_elements: List[str]):
        if not records:
            return 0
        stmt = insert(model_class).values(records)
        update_dict = {c.name: c for c in stmt.excluded if c.name not in index_elements and c.name != 'created_at'}
        
        if update_dict:
            stmt = stmt.on_conflict_do_update(
                index_elements=index_elements,
                set_=update_dict
            )
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
            
        session.execute(stmt)
        return len(records)

    def seed_cpses(self, session):
        data = load_json(self.config.get_ref_path(self.config.cpse_file))
        if not data: return
        records = []
        for org in data.get('organizations', []):
            if validate_dict(CPSEValidator, org):
                records.append({
                    'cpse_id': generate_uuid(org['cpse_code']),
                    'cpse_code': org['cpse_code'],
                    'cpse_name': org['cpse_name'],
                    'sector': org.get('sector'),
                    'description': org.get('description'),
                    'status': 'ACTIVE'
                })
            else:
                self.stats['CPSE']['rejected'] += 1
        count = self._pg_upsert(session, CPSE, records, ['cpse_code'])
        self.stats['CPSE']['upserted'] += count

    def seed_classifications(self, session):
        data = load_json(self.config.get_ref_path(self.config.classification_file))
        if not data: return
        records = []
        def unroll(node, parent_id=None):
            cat_id = generate_uuid(node['id'])
            records.append({
                'classification_id': cat_id,
                'code': node['id'],
                'name': node['name'],
                'parent_id': parent_id
            })
            for sub in node.get('subcategories', []):
                unroll(sub, cat_id)
                
        for cat in data.get('categories', []):
            unroll(cat, None)
            
        count = self._pg_upsert(session, Classification, records, ['code'])
        self.stats['Classification']['upserted'] += count

    def seed_uom(self, session):
        data = load_json(self.config.get_ref_path(self.config.uom_file))
        if not data: return
        records = []
        for dim, info in data.get('dimensions', {}).items():
            for u in info.get('units', []):
                records.append({
                    'canonical_code': u['code'],
                    'name': u['name'],
                    'dimension': dim
                })
        count = self._pg_upsert(session, UOMMaster, records, ['canonical_code'])
        self.stats['UOM']['upserted'] += count

    def seed_synonyms(self, session):
        data = load_json(self.config.get_ref_path(self.config.synonym_file))
        if not data: return
        records = [{'id': i+1, 'term': s['term'], 'expansion': s['expansion'], 'is_ambiguous': s.get('is_ambiguous', False)} 
                   for i, s in enumerate(data.get('synonyms', []))]
        count = self._pg_upsert(session, Synonym, records, ['id'])
        self.stats['Synonym']['upserted'] += count

    def seed_critical_rules(self, session):
        data = load_json(self.config.get_ref_path(self.config.critical_rules_file))
        if not data: return
        records = []
        for i, r in enumerate(data.get('rules', [])):
            # Normalize enum values
            severity = r.get('severity', 'MEDIUM').upper()
            if severity not in ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'):
                severity = 'MEDIUM'
            behavior = r.get('conflict_behavior', 'FLAG_ONLY').upper()
            if behavior not in ('BLOCK_EQUIVALENCE', 'REQUIRE_REVIEW', 'FLAG_ONLY'):
                behavior = 'FLAG_ONLY'

            records.append({
                'id': str(uuid.UUID(int=i+1)),
                'classification_code': r['category'],
                'attribute': r['attribute'],
                'severity': severity,
                'conflict_behavior': behavior
            })
        count = self._pg_upsert(session, CriticalRule, records, ['id'])
        self.stats['CriticalRule']['upserted'] += count
        
    def seed_users(self, session):
        import bcrypt
        DEMO_USERS = {
            "demo_admin": {
                "name": "Demo Administrator",
                "password": os.getenv("DEMO_ADMIN_PASSWORD", "admin123").encode(),
                "cpse": "ALL",
                "permissions": ["admin", "read", "write"]
            },
            "demo_engineer": {
                "name": "Demo Engineer",
                "password": os.getenv("DEMO_ENGINEER_PASSWORD", "engineer123").encode(),
                "cpse": "NTPC",
                "permissions": ["read", "write"]
            }
        }
        records = []
        for uid, udata in DEMO_USERS.items():
            records.append({
                'user_id': uid,
                'name': udata['name'],
                'password_hash': bcrypt.hashpw(udata['password'], bcrypt.gensalt()).decode(),
                'role_id': None, 
                'cpse_code': udata['cpse'] if udata['cpse'] != 'ALL' else None,
                'permissions': udata['permissions']
            })
        count = self._pg_upsert(session, User, records, ['user_id'])
        self.stats['User']['upserted'] += count

    def seed_source_materials(self, session, is_demo: bool):
        path = self.config.get_data_path('source_materials.csv' if not is_demo else 'demo_materials.csv', is_demo)
        rows = load_csv(path)
        base_keys = {'cpse_code', 'material_code', 'description', 'uom', 'plant'}
        records = []
        for r in rows:
            if not validate_dict(SourceMaterialValidator, r):
                self.stats['SourceMaterial']['rejected'] += 1
                continue
                
            raw_json = {k: v for k, v in r.items() if k not in base_keys and v and str(v).strip()}
            source_id = generate_uuid(f"{r['cpse_code']}_{r['material_code']}")
            
            records.append({
                'source_material_id': source_id,
                'cpse_id': generate_uuid(r['cpse_code']),
                'legacy_material_code': r['material_code'],
                'raw_description': r['description'],
                'raw_uom': r.get('uom'),
                'plant': r.get('plant')
            })
            
            if len(records) >= 1000:
                count = self._pg_upsert(session, SourceMaterial, records, ['source_material_id'])
                self.stats['SourceMaterial']['upserted'] += count
                records = []
                
        if records:
            count = self._pg_upsert(session, SourceMaterial, records, ['source_material_id'])
            self.stats['SourceMaterial']['upserted'] += count

    def print_stats(self):
        print("\n" + "="*40)
        print("SEEDING SUMMARY STATISTICS")
        print("="*40)
        for entity, stat in self.stats.items():
            print(f"{entity:<20} | Upserted: {stat['upserted']:<6} | Rejected: {stat['rejected']:<6}")
        print("="*40 + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true', help='Seed curated demo dataset')
    parser.add_argument('--reference-only', action='store_true', help='Seed only reference master data')
    parser.add_argument('--clear', action='store_true', help='Clear tables before seeding')
    parser.add_argument('--validate', action='store_true', help='Validate inputs without modifying database')
    parser.add_argument('--db-url', type=str, default=os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/platform'), help='PostgreSQL connection URL')
    args = parser.parse_args()

    config = SeedConfig()
    
    if args.validate:
        print("Running in validation mode. No database modifications will be made.")
        return

    engine = SeedEngine(args.db_url, config)
    session = engine.Session()

    try:
        print("Starting Database Seeding Transaction...")
        
        if args.clear:
            print("Clearing tables...")
            for table in reversed(Base.metadata.sorted_tables):
                session.execute(table.delete())

        engine.seed_cpses(session)
        engine.seed_classifications(session)
        engine.seed_uom(session)
        engine.seed_synonyms(session)
        engine.seed_critical_rules(session)
        engine.seed_users(session)
        
        if not args.reference_only:
            print(f"Seeding Source Materials (Demo Mode: {args.demo})...")
            engine.seed_source_materials(session, args.demo)
            
        session.commit()
        print("Transaction committed successfully.")
        engine.print_stats()

    except Exception as e:
        session.rollback()
        print(f"CRITICAL FAILURE: Rolling back transaction. Error: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == "__main__":
    main()
