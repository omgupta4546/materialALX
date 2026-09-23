"""
seed_sqlite.py — SQLite-compatible database seeder.

Uses ORM merge() instead of PostgreSQL-specific INSERT...ON CONFLICT.
Loads the same reference data and demo data as seed_database.py.
"""

import os
import sys
import json
import csv
import uuid
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from sqlalchemy.orm import Session
from app.core.connection import engine, DATABASE_URL
from app.models.base import (
    Base, CPSE, Classification, UOMMaster, Synonym, CriticalRule, User, Role, SourceMaterial
)


def generate_uuid(text: str) -> str:
    return str(uuid.UUID(hashlib.md5(text.encode()).hexdigest()))


def load_json(path: str):
    if not os.path.exists(path):
        print(f"  WARNING: File not found: {path}")
        return None
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_csv(path: str):
    if not os.path.exists(path):
        print(f"  WARNING: File not found: {path}")
        return []
    rows = []
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def seed_roles(session: Session):
    print("  Seeding roles...")
    roles = [
        Role(id="ADMIN", description="Full platform administrator"),
        Role(id="CPSE_USER", description="CPSE standard user"),
        Role(id="DATA_STEWARD", description="Data steward with approval authority"),
        Role(id="ENGINEER", description="Materials engineer"),
        Role(id="AUDITOR", description="Read-only audit role"),
    ]
    for r in roles:
        existing = session.get(Role, r.id)
        if not existing:
            session.add(r)
    session.flush()
    print(f"    Roles: {len(roles)} processed")


def seed_users(session: Session):
    import bcrypt
    print("  Seeding users...")
    users_data = [
        {
            "user_id": "demo_admin",
            "name": "Demo Administrator",
            "email": "admin@platform.local",
            "password": "admin123",
            "role_id": "ADMIN",
            "cpse_code": None,
            "permissions": ["admin", "read", "write"]
        },
        {
            "user_id": "demo_engineer",
            "name": "Demo Engineer",
            "email": "engineer@platform.local",
            "password": "engineer123",
            "role_id": "ENGINEER",
            "cpse_code": "NTPC",
            "permissions": ["read", "write"]
        },
        {
            "user_id": "demo_steward",
            "name": "Demo Data Steward",
            "email": "steward@platform.local",
            "password": "steward123",
            "role_id": "DATA_STEWARD",
            "cpse_code": None,
            "permissions": ["read", "write", "approve"]
        },
        {
            "user_id": "demo_auditor",
            "name": "Demo Auditor",
            "email": "auditor@platform.local",
            "password": "auditor123",
            "role_id": "AUDITOR",
            "cpse_code": None,
            "permissions": ["read"]
        },
    ]

    for udata in users_data:
        existing = session.get(User, udata["user_id"])
        if not existing:
            pw_hash = bcrypt.hashpw(udata["password"].encode(), bcrypt.gensalt()).decode()
            user = User(
                user_id=udata["user_id"],
                name=udata["name"],
                email=udata["email"],
                password_hash=pw_hash,
                role_id=udata["role_id"],
                cpse_code=udata["cpse_code"],
                permissions=udata["permissions"],
            )
            session.add(user)
    session.flush()
    print(f"    Users: {len(users_data)} processed")


def seed_cpses(session: Session):
    print("  Seeding CPSEs...")
    data = load_json(os.path.join(os.path.dirname(__file__), '..', 'data', 'reference', 'cpse.json'))
    if not data:
        return
    count = 0
    for org in data.get('organizations', []):
        cpse_id = generate_uuid(org['cpse_code'])
        existing = session.get(CPSE, cpse_id)
        if not existing:
            cpse = CPSE(
                cpse_id=cpse_id,
                cpse_code=org['cpse_code'],
                cpse_name=org['cpse_name'],
                sector=org.get('sector'),
                description=org.get('description'),
                status='ACTIVE'
            )
            session.add(cpse)
            count += 1
    session.flush()
    print(f"    CPSEs: {count} added")


def seed_classifications(session: Session):
    print("  Seeding classifications...")
    data = load_json(os.path.join(os.path.dirname(__file__), '..', 'data', 'reference', 'classification.json'))
    if not data:
        return
    count = 0

    def unroll(node, parent_id=None):
        nonlocal count
        cat_id = generate_uuid(node['id'])
        existing = session.get(Classification, cat_id)
        if not existing:
            cat = Classification(
                classification_id=cat_id,
                code=node['id'],
                name=node['name'],
                parent_id=parent_id
            )
            session.add(cat)
            count += 1
        for sub in node.get('subcategories', []):
            unroll(sub, cat_id)

    for cat in data.get('categories', []):
        unroll(cat, None)
    session.flush()
    print(f"    Classifications: {count} added")


def seed_uom(session: Session):
    print("  Seeding UOMs...")
    data = load_json(os.path.join(os.path.dirname(__file__), '..', 'data', 'reference', 'uom_master.json'))
    if not data:
        return
    count = 0
    for dim, info in data.get('dimensions', {}).items():
        for u in info.get('units', []):
            existing = session.get(UOMMaster, u['code'])
            if not existing:
                uom = UOMMaster(
                    canonical_code=u['code'],
                    name=u['name'],
                    dimension=dim
                )
                session.add(uom)
                count += 1
    session.flush()
    print(f"    UOMs: {count} added")


def seed_synonyms(session: Session):
    print("  Seeding synonyms...")
    data = load_json(os.path.join(os.path.dirname(__file__), '..', 'data', 'reference', 'synonyms.json'))
    if not data:
        return
    count = 0
    for i, s in enumerate(data.get('synonyms', [])):
        syn_id = i + 1
        existing = session.get(Synonym, syn_id)
        if not existing:
            syn = Synonym(
                id=syn_id,
                term=s['term'],
                expansion=s['expansion'],
                is_ambiguous=s.get('is_ambiguous', False)
            )
            session.add(syn)
            count += 1
    session.flush()
    print(f"    Synonyms: {count} added")


def seed_critical_rules(session: Session):
    print("  Seeding critical rules...")
    data = load_json(os.path.join(os.path.dirname(__file__), '..', 'data', 'reference', 'critical_rules.json'))
    if not data:
        return
    count = 0
    for i, r in enumerate(data.get('rules', [])):
        rule_id = str(uuid.UUID(int=i + 1))
        existing = session.get(CriticalRule, rule_id)
        if not existing:
            severity = r.get('severity', 'MEDIUM').upper()
            if severity not in ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'):
                severity = 'MEDIUM'
            behavior = r.get('conflict_behavior', 'FLAG_ONLY').upper()
            if behavior not in ('BLOCK_EQUIVALENCE', 'REQUIRE_REVIEW', 'FLAG_ONLY'):
                behavior = 'FLAG_ONLY'

            rule = CriticalRule(
                id=rule_id,
                classification_code=r['category'],
                attribute=r['attribute'],
                severity=severity,
                conflict_behavior=behavior
            )
            session.add(rule)
            count += 1
    session.flush()
    print(f"    Critical Rules: {count} added")


def seed_source_materials(session: Session):
    print("  Seeding source materials...")
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'demo', 'demo_materials.csv')
    rows = load_csv(path)
    count = 0
    for r in rows:
        source_id = generate_uuid(f"{r['cpse_code']}_{r['material_code']}")
        existing = session.get(SourceMaterial, source_id)
        if not existing:
            mat = SourceMaterial(
                source_material_id=source_id,
                cpse_id=generate_uuid(r['cpse_code']),
                legacy_material_code=r['material_code'],
                raw_description=r['description'],
                raw_uom=r.get('uom'),
                plant=r.get('plant'),
            )
            session.add(mat)
            count += 1
            if count % 100 == 0:
                session.flush()
    session.flush()
    print(f"    Source Materials: {count} added")


def main():
    print(f"Database URL: {DATABASE_URL}")
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        print("\nSeeding database...\n")
        seed_roles(session)
        seed_cpses(session)
        seed_users(session)
        seed_classifications(session)
        seed_uom(session)
        seed_synonyms(session)
        seed_critical_rules(session)
        seed_source_materials(session)
        session.commit()
        print("\n[OK] Database seeded successfully!")
    except Exception as e:
        session.rollback()
        print(f"\n[FAIL] Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
