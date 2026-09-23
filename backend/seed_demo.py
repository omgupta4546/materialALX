"""
seed_demo.py — Seed rich demo data for the National Material Intelligence Platform.

Run from the backend/ directory AFTER init_db.py:
    python seed_demo.py

Seeded data:
  - 5 CPSEs (Power, Steel, Oil & Gas, Mining, Heavy Engineering)
  - 5 Users: admin, engineer1, steward1, auditor1, cpse_user1
  - 3 Roles: ADMIN, ENGINEER, DATA_STEWARD, AUDITOR, CPSE_USER
  - 12 Classifications (hierarchical taxonomy)
  - 8 UOMs
  - 6 Critical Rules (per category)
  - 1 Global Matching Config
  - 40 National Materials (golden catalog with attributes)
  - 120 Source Materials (raw CPSE data — duplicates + equivalents + unique)
  - 80 Normalized Materials + embeddings (768d random for demo)
  - 60 Match Results (with realistic scores)
  - 20 Material Mappings (APPROVED / PENDING / REJECTED)
  - 10 Procurement Records
  - 5 Processing Jobs
  - Sample Audit Logs, Notifications
"""
import os
import sys
import uuid
import random
import logging
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
# Load backend .env explicitly (takes priority over root .env)
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path, override=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

from sqlalchemy.orm import Session
from app.core.connection import engine, SessionLocal
from app.auth.security import get_password_hash
from app.models.base import (
    CPSE, Role, User, Classification, UOMMaster, CriticalRule,
    GlobalMatchingConfig, NationalMaterial, SourceMaterial, NormalizedMaterial,
    MatchResult, MaterialMapping, ProcessingJob, FileUpload,
    Notification, AuditLog, Approval, FeedbackEvent,
    ModelRegistry, PromptRegistry,
)

rng = random.Random(42)  # deterministic seed for reproducible demo data


# ─────────────────────────────────────────────────────────────────────────────
# HELPER UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def uid(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def rand_embedding(dim=768):
    """Deterministic-ish random unit vector for demo embeddings."""
    vec = [rng.gauss(0, 1) for _ in range(dim)]
    norm = sum(x * x for x in vec) ** 0.5
    return [x / norm for x in vec] if norm > 0 else [0.0] * dim


def ago(days=0, hours=0):
    return datetime.utcnow() - timedelta(days=days, hours=hours)


def exists(db: Session, model, **kwargs):
    return db.query(model).filter_by(**kwargs).first()


# ─────────────────────────────────────────────────────────────────────────────
# ROLES
# ─────────────────────────────────────────────────────────────────────────────

ROLES = [
    {"id": "ADMIN",       "description": "Platform administrator with full access"},
    {"id": "ENGINEER",    "description": "Material engineer — match review & data quality"},
    {"id": "DATA_STEWARD","description": "Data steward — governance & approval"},
    {"id": "AUDITOR",     "description": "Read-only audit access"},
    {"id": "CPSE_USER",   "description": "CPSE-scoped read-only user"},
]


def seed_roles(db: Session):
    for r in ROLES:
        if not exists(db, Role, id=r["id"]):
            db.add(Role(**r))
    db.commit()
    log.info(f"✅ Roles: {len(ROLES)}")


# ─────────────────────────────────────────────────────────────────────────────
# CPSEs
# ─────────────────────────────────────────────────────────────────────────────

CPSE_DATA = [
    {"cpse_code": "BHEL",  "cpse_name": "Bharat Heavy Electricals Limited", "sector": "Heavy Engineering", "description": "India's largest engineering & manufacturing enterprise", "status": "ACTIVE"},
    {"cpse_code": "ONGC",  "cpse_name": "Oil and Natural Gas Corporation",  "sector": "Oil & Gas",         "description": "India's largest crude oil and natural gas producer", "status": "ACTIVE"},
    {"cpse_code": "NTPC",  "cpse_name": "NTPC Limited",                     "sector": "Power",             "description": "India's largest power generation company", "status": "ACTIVE"},
    {"cpse_code": "SAIL",  "cpse_name": "Steel Authority of India Limited", "sector": "Steel",             "description": "India's largest steel making company", "status": "ACTIVE"},
    {"cpse_code": "GAIL",  "cpse_name": "GAIL (India) Limited",             "sector": "Oil & Gas",         "description": "India's leading natural gas company", "status": "ACTIVE"},
]

CPSE_IDS = {}  # code → cpse_id


def seed_cpses(db: Session):
    for c in CPSE_DATA:
        obj = exists(db, CPSE, cpse_code=c["cpse_code"])
        if not obj:
            obj = CPSE(cpse_id=uid("CPSE-"), **c)
            db.add(obj)
            db.flush()
        CPSE_IDS[c["cpse_code"]] = obj.cpse_id
    db.commit()
    log.info(f"✅ CPSEs: {len(CPSE_DATA)}")


# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────

def seed_users(db: Session):
    users = [
        {"user_id": "admin",    "name": "System Administrator", "email": "admin@platform.gov.in",   "password": "admin123",  "role_id": "ADMIN",        "cpse_code": None},
        {"user_id": "engineer1","name": "Arjun Sharma",         "email": "arjun@bhel.gov.in",        "password": "demo123",   "role_id": "ENGINEER",     "cpse_code": "BHEL"},
        {"user_id": "steward1", "name": "Priya Mehta",          "email": "priya@ntpc.gov.in",         "password": "demo123",   "role_id": "DATA_STEWARD", "cpse_code": "NTPC"},
        {"user_id": "auditor1", "name": "Raj Kumar",            "email": "raj.kumar@audit.gov.in",    "password": "demo123",   "role_id": "AUDITOR",      "cpse_code": None},
        {"user_id": "cpse1",    "name": "Sunita Rao",           "email": "sunita@ongc.gov.in",        "password": "demo123",   "role_id": "CPSE_USER",    "cpse_code": "ONGC"},
    ]
    for u in users:
        if not exists(db, User, user_id=u["user_id"]):
            db.add(User(
                user_id=u["user_id"],
                name=u["name"],
                email=u["email"],
                password_hash=get_password_hash(u["password"]),
                role_id=u["role_id"],
                cpse_code=u["cpse_code"],
                permissions=[],
            ))
    db.commit()
    log.info(f"✅ Users: {len(users)}")


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────

CLASSIFICATION_TREE = [
    # (code, name, level, parent_code)
    ("MECH",     "Mechanical Components",     0, None),
    ("MECH-BRG", "Bearings",                 1, "MECH"),
    ("MECH-VLV", "Valves",                   1, "MECH"),
    ("MECH-PIP", "Pipes & Fittings",         1, "MECH"),
    ("MECH-PMP", "Pumps",                    1, "MECH"),
    ("MECH-GSK", "Gaskets & Seals",          1, "MECH"),
    ("ELEC",     "Electrical Equipment",     0, None),
    ("ELEC-MTR", "Electric Motors",          1, "ELEC"),
    ("ELEC-TRF", "Transformers",             1, "ELEC"),
    ("ELEC-CBL", "Cables & Wires",           1, "ELEC"),
    ("INSTR",    "Instrumentation",          0, None),
    ("INSTR-SEN","Sensors & Transmitters",   1, "INSTR"),
]

CLASS_IDS = {}  # code → classification_id


def seed_classifications(db: Session):
    code_to_obj = {}
    for code, name, level, parent_code in CLASSIFICATION_TREE:
        obj = exists(db, Classification, code=code)
        if not obj:
            parent_id = CLASS_IDS.get(parent_code) if parent_code else None
            obj = Classification(
                classification_id=uid("CLS-"),
                code=code, name=name, level=level,
                parent_id=parent_id,
                status="ACTIVE", version=1, is_latest=True
            )
            db.add(obj)
            db.flush()
        CLASS_IDS[code] = obj.classification_id
        code_to_obj[code] = obj
    db.commit()
    log.info(f"✅ Classifications: {len(CLASSIFICATION_TREE)}")


# ─────────────────────────────────────────────────────────────────────────────
# UOMs
# ─────────────────────────────────────────────────────────────────────────────

def seed_uoms(db: Session):
    uoms = [
        {"canonical_code": "EA",  "name": "Each",       "dimension": "COUNT",  "aliases": ["NO", "NOS", "PCS", "PIECE", "EACH"], "is_base_unit": True},
        {"canonical_code": "KG",  "name": "Kilogram",   "dimension": "MASS",   "aliases": ["KGS", "KILOGRAM"],                   "is_base_unit": True},
        {"canonical_code": "MTR", "name": "Metre",      "dimension": "LENGTH", "aliases": ["M", "METER", "MTS"],                 "is_base_unit": True},
        {"canonical_code": "LTR", "name": "Litre",      "dimension": "VOLUME", "aliases": ["L", "LT", "LITRE"],                  "is_base_unit": True},
        {"canonical_code": "SET", "name": "Set",        "dimension": "COUNT",  "aliases": ["KIT"],                               "is_base_unit": False},
        {"canonical_code": "BOX", "name": "Box",        "dimension": "COUNT",  "aliases": ["PKT", "PACK"],                       "is_base_unit": False},
        {"canonical_code": "MM",  "name": "Millimetre", "dimension": "LENGTH", "aliases": ["MILLIMETER"],                        "is_base_unit": False, "base_multiplier": 0.001},
        {"canonical_code": "TON", "name": "Tonne",      "dimension": "MASS",   "aliases": ["MT", "METRIC TON"],                  "is_base_unit": False, "base_multiplier": 1000},
    ]
    for u in uoms:
        if not exists(db, UOMMaster, canonical_code=u["canonical_code"]):
            db.add(UOMMaster(**u))
    db.commit()
    log.info(f"✅ UOMs: {len(uoms)}")


# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL RULES
# ─────────────────────────────────────────────────────────────────────────────

def seed_critical_rules(db: Session):
    rules = [
        {"classification_code": "MECH-VLV", "attribute": "pressure_class",  "severity": "CRITICAL", "conflict_behavior": "BLOCK_EQUIVALENCE", "notes": "Pressure class mismatch in valves is a safety-critical incompatibility"},
        {"classification_code": "MECH-VLV", "attribute": "size",            "severity": "CRITICAL", "conflict_behavior": "BLOCK_EQUIVALENCE", "notes": "Valve size mismatch blocks installation"},
        {"classification_code": "ELEC-MTR", "attribute": "voltage",         "severity": "CRITICAL", "conflict_behavior": "BLOCK_EQUIVALENCE", "notes": "Motor voltage must match electrical supply"},
        {"classification_code": "ELEC-MTR", "attribute": "power",           "severity": "HIGH",     "conflict_behavior": "REQUIRE_REVIEW",    "notes": "Power rating affects drive sizing"},
        {"classification_code": "MECH-BRG", "attribute": "bore",            "severity": "CRITICAL", "conflict_behavior": "BLOCK_EQUIVALENCE", "notes": "Bearing bore must match shaft diameter exactly"},
        {"classification_code": "MECH-PIP", "attribute": "schedule",        "severity": "HIGH",     "conflict_behavior": "REQUIRE_REVIEW",    "notes": "Wall thickness affects pressure rating"},
    ]
    for r in rules:
        if not exists(db, CriticalRule, classification_code=r["classification_code"], attribute=r["attribute"], is_latest=True):
            db.add(CriticalRule(
                id=uid("RULE-"),
                version=1, is_latest=True, status="ACTIVE",
                created_by="admin",
                **r
            ))
    db.commit()
    log.info(f"✅ Critical Rules: {len(rules)}")


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL MATCHING CONFIG
# ─────────────────────────────────────────────────────────────────────────────

def seed_global_config(db: Session):
    if not db.query(GlobalMatchingConfig).first():
        db.add(GlobalMatchingConfig(
            config_id=uid("CFG-"),
            version=1, is_latest=True,
            weight_semantic=0.30,
            weight_attribute=0.40,
            weight_manufacturer=0.10,
            weight_mpn=0.20,
            threshold_exact_duplicate=0.95,
            threshold_near_duplicate=0.85,
            threshold_functionally_equivalent=0.65,
            threshold_related=0.50,
            auto_approve_enabled=False,
            auto_approve_threshold=0.95,
            auto_approve_max_risk_level="LOW",
            created_by="admin",
            change_note="Initial platform configuration",
        ))
        db.commit()
    log.info("✅ Global Matching Config")


# ─────────────────────────────────────────────────────────────────────────────
# NATIONAL MATERIALS (Golden Catalog)
# ─────────────────────────────────────────────────────────────────────────────

NAT_MATERIALS = [
    # Bearings
    {"code": "NM-BRG-001", "desc": "DEEP GROOVE BALL BEARING 6205 2RS 25X52X15 MM",   "cls": "MECH-BRG", "uom": "EA", "attrs": {"series": "6205", "seal": "2RS", "bore": "25", "outer_diameter": "52", "width": "15", "unit": "MM"}},
    {"code": "NM-BRG-002", "desc": "DEEP GROOVE BALL BEARING 6309 ZZ 45X100X25 MM",  "cls": "MECH-BRG", "uom": "EA", "attrs": {"series": "6309", "seal": "ZZ",  "bore": "45", "outer_diameter": "100","width": "25", "unit": "MM"}},
    {"code": "NM-BRG-003", "desc": "CYLINDRICAL ROLLER BEARING NU310 50X110X27 MM",  "cls": "MECH-BRG", "uom": "EA", "attrs": {"series": "NU310","seal": None,  "bore": "50", "outer_diameter": "110","width": "27", "unit": "MM"}},
    {"code": "NM-BRG-004", "desc": "SELF ALIGNING BALL BEARING 1210 50X90X20 MM",    "cls": "MECH-BRG", "uom": "EA", "attrs": {"series": "1210", "bore": "50", "outer_diameter": "90", "width": "20"}},
    # Valves
    {"code": "NM-VLV-001", "desc": "GATE VALVE 2 IN CLASS 150 CARBON STEEL FLANGED", "cls": "MECH-VLV", "uom": "EA", "attrs": {"type": "GATE", "size": "2", "pressure_class": "CLASS 150", "body_material": "CARBON STEEL", "end_connection": "FLANGED"}},
    {"code": "NM-VLV-002", "desc": "BALL VALVE 1 IN PN40 STAINLESS STEEL THREADED",  "cls": "MECH-VLV", "uom": "EA", "attrs": {"type": "BALL", "size": "1", "pressure_class": "PN40",       "body_material": "STAINLESS STEEL","end_connection": "THREADED"}},
    {"code": "NM-VLV-003", "desc": "BUTTERFLY VALVE 6 IN CLASS 150 CAST IRON WAFER", "cls": "MECH-VLV", "uom": "EA", "attrs": {"type": "BUTTERFLY", "size": "6", "pressure_class": "CLASS 150", "body_material": "CAST IRON", "end_connection": "WAFER"}},
    {"code": "NM-VLV-004", "desc": "CHECK VALVE 3 IN CLASS 300 CARBON STEEL",        "cls": "MECH-VLV", "uom": "EA", "attrs": {"type": "CHECK", "size": "3", "pressure_class": "CLASS 300", "body_material": "CARBON STEEL"}},
    {"code": "NM-VLV-005", "desc": "GLOBE VALVE 4 IN CLASS 600 ALLOY STEEL BUTT WELDED", "cls": "MECH-VLV", "uom": "EA", "attrs": {"type": "GLOBE", "size": "4", "pressure_class": "CLASS 600", "body_material": "ALLOY STEEL"}},
    # Pipes
    {"code": "NM-PIP-001", "desc": "CARBON STEEL PIPE 2 IN SCH 40 SEAMLESS 6 MTR",  "cls": "MECH-PIP", "uom": "MTR","attrs": {"diameter": "2", "schedule": "SCH 40", "material_grade": "CARBON STEEL", "type": "SEAMLESS"}},
    {"code": "NM-PIP-002", "desc": "STAINLESS STEEL PIPE 1 IN SCH 80 SEAMLESS",      "cls": "MECH-PIP", "uom": "MTR","attrs": {"diameter": "1", "schedule": "SCH 80", "material_grade": "STAINLESS STEEL"}},
    {"code": "NM-PIP-003", "desc": "CARBON STEEL PIPE 4 IN SCH 40 ERW 6 MTR",       "cls": "MECH-PIP", "uom": "MTR","attrs": {"diameter": "4", "schedule": "SCH 40", "material_grade": "CARBON STEEL", "type": "ERW"}},
    # Electric Motors
    {"code": "NM-MTR-001", "desc": "INDUCTION MOTOR 15 KW 415V 50HZ 3PH TEFC 1450 RPM", "cls": "ELEC-MTR", "uom": "EA", "attrs": {"power": "15", "voltage": "415", "frequency": "50", "phase": "3", "enclosure": "TEFC", "rpm": "1450"}},
    {"code": "NM-MTR-002", "desc": "INDUCTION MOTOR 7.5 KW 415V 50HZ 3PH TEFC 960 RPM", "cls": "ELEC-MTR", "uom": "EA", "attrs": {"power": "7.5", "voltage": "415", "frequency": "50", "phase": "3", "enclosure": "TEFC", "rpm": "960"}},
    {"code": "NM-MTR-003", "desc": "INDUCTION MOTOR 37 KW 415V 50HZ 3PH ODP 1480 RPM",  "cls": "ELEC-MTR", "uom": "EA", "attrs": {"power": "37", "voltage": "415", "frequency": "50", "phase": "3", "enclosure": "ODP",  "rpm": "1480"}},
    {"code": "NM-MTR-004", "desc": "INDUCTION MOTOR 55 KW 6600V 50HZ 3PH TEFC 1485 RPM","cls": "ELEC-MTR", "uom": "EA", "attrs": {"power": "55", "voltage": "6600","frequency": "50", "phase": "3", "enclosure": "TEFC", "rpm": "1485"}},
    # Pumps
    {"code": "NM-PMP-001", "desc": "CENTRIFUGAL PUMP 50 LPM 30M HEAD 5.5 KW CAST IRON",  "cls": "MECH-PMP", "uom": "EA", "attrs": {"flow_rate": "50", "head": "30", "power": "5.5", "material": "CAST IRON"}},
    {"code": "NM-PMP-002", "desc": "CENTRIFUGAL PUMP 200 LPM 50M HEAD 15 KW SS IMPELLER", "cls": "MECH-PMP", "uom": "EA", "attrs": {"flow_rate": "200", "head": "50", "power": "15", "material": "SS IMPELLER"}},
    # Extra variety for analytics
    {"code": "NM-BRG-005", "desc": "TAPER ROLLER BEARING 30205 25X52X15 MM",          "cls": "MECH-BRG", "uom": "EA", "attrs": {"series": "30205", "bore": "25", "outer_diameter": "52"}},
    {"code": "NM-BRG-006", "desc": "ANGULAR CONTACT BALL BEARING 7210 50X90X20 MM",   "cls": "MECH-BRG", "uom": "EA", "attrs": {"series": "7210", "bore": "50", "outer_diameter": "90"}},
    {"code": "NM-VLV-006", "desc": "NEEDLE VALVE 0.5 IN PN160 SS INSTRUMENT",         "cls": "MECH-VLV", "uom": "EA", "attrs": {"type": "NEEDLE", "size": "0.5", "pressure_class": "PN160"}},
    {"code": "NM-MTR-005", "desc": "SERVO MOTOR 2.2 KW 220V ENCODER FEEDBACK",        "cls": "ELEC-MTR", "uom": "EA", "attrs": {"power": "2.2", "voltage": "220", "type": "SERVO"}},
    {"code": "NM-PIP-004", "desc": "GI PIPE 3 IN MEDIUM CLASS IS:1239",               "cls": "MECH-PIP", "uom": "MTR","attrs": {"diameter": "3", "material_grade": "GALVANIZED IRON"}},
    {"code": "NM-PMP-003", "desc": "SUBMERSIBLE PUMP 500 LPM 20M HEAD 7.5 KW",        "cls": "MECH-PMP", "uom": "EA", "attrs": {"flow_rate": "500", "head": "20", "power": "7.5", "type": "SUBMERSIBLE"}},
]

NAT_MAT_IDS = {}  # code → national_material_id


def seed_national_materials(db: Session):
    for nm in NAT_MATERIALS:
        obj = exists(db, NationalMaterial, national_material_code=nm["code"])
        if not obj:
            cls_id = CLASS_IDS.get(nm["cls"])
            obj = NationalMaterial(
                national_material_id=uid("NM-"),
                national_material_code=nm["code"],
                canonical_description=nm["desc"],
                classification_id=cls_id,
                canonical_uom=nm["uom"],
                attributes=nm["attrs"],
                status="ACTIVE",
                version=1,
                created_by="admin",
            )
            db.add(obj)
            db.flush()
        NAT_MAT_IDS[nm["code"]] = obj.national_material_id
    db.commit()
    log.info(f"✅ National Materials: {len(NAT_MATERIALS)}")


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE MATERIALS (Raw CPSE data — with intentional duplicates + equivalents)
# ─────────────────────────────────────────────────────────────────────────────

# Raw source rows: (legacy_code, description, uom, category, manufacturer, mpn, cpse_code)
SOURCE_ROWS = [
    # === BHEL source materials ===
    # Exact duplicates of NM-BRG-001
    ("BHEL-BRG-001", "DEEP GROOVE BALL BRG 6205-2RS 25X52X15MM",          "NOS", "BEARING", "SKF",    "6205-2RS/C3", "BHEL"),
    ("BHEL-BRG-002", "DG BALL BEARING 6205 2RS SIZE 25X52X15 MM",          "EA",  "BEARING", "FAG",    "6205.2RSR",   "BHEL"),
    # Near-duplicate of NM-BRG-001 (different seal)
    ("BHEL-BRG-003", "BALL BRG 6205 ZZ 25X52X15MM SHIELDED",               "NOS", "BEARING", "NSK",    "6205ZZ",      "BHEL"),
    # Functionally equivalent to NM-BRG-002
    ("BHEL-BRG-004", "DEEP GROOVE BEARING 6309-ZZ 45X100X25MM",            "EA",  "BEARING", "TIMKEN", "6309ZZ",      "BHEL"),
    # Valve near-duplicate
    ("BHEL-VLV-001", "GATE VALVE 2\" CLASS 150 CS FLANGED END",            "NOS", "VALVE",   "L&T",    "GV-2-150-CS", "BHEL"),
    ("BHEL-VLV-002", "GATE VALVE DN50 CLASS 150 CARBON STEEL",             "EA",  "VALVE",   "AUDCO",  "GV-DN50-150", "BHEL"),
    # Motor exact match
    ("BHEL-MTR-001", "INDUCTION MOTOR 15KW 415V 50HZ 3PH TEFC 1450RPM",   "NOS", "MOTOR",   "BHEL",   "IE2-15KW",    "BHEL"),
    ("BHEL-MTR-002", "AC INDUCTION MOTOR 15 KW 415 VOLTS 1450 RPM TEFC",  "EA",  "MOTOR",   "ABB",    "M2AA160M4",   "BHEL"),
    # Pipe near-duplicate
    ("BHEL-PIP-001", "CS PIPE 2IN SCH40 SEAMLESS 6MTR IS:1239",            "MTR", "PIPE",    "ISMT",   None,          "BHEL"),
    ("BHEL-PIP-002", "CARBON STEEL PIPE 2\" SCHEDULE 40 SMLS 6M",          "MTR", "PIPE",    "MSL",    None,          "BHEL"),
    # Unique items
    ("BHEL-PMP-001", "CENTRIFUGAL PUMP 50LPM 30M HEAD 5.5KW CI BODY",     "NOS", "PUMP",    "KSB",    "MEGA-40-125", "BHEL"),
    ("BHEL-GSK-001", "SPIRAL WOUND GASKET 2IN CLASS 150 ASME B16.20",      "NOS", "GASKET",  "FLEXITALLIC", None,    "BHEL"),

    # === ONGC source materials ===
    ("ONGC-BRG-001", "BEARING 6205-2RS SKF 25MM BORE DEEP GROOVE",         "NOS", "BEARING", "SKF",    "6205-2RS1",   "ONGC"),
    ("ONGC-BRG-002", "CYLINDRICAL ROLLER BRG NU310 50X110X27",             "EA",  "BEARING", "FAG",    "NU310E.TVP2", "ONGC"),
    ("ONGC-VLV-001", "BALL VALVE 1INCH PN40 SS 316 THREADED END",          "NOS", "VALVE",   "FLOWSERVE","BV1-PN40-SS","ONGC"),
    ("ONGC-VLV-002", "BALL VALVE 1\" PN40 STAINLESS STEEL SCREWED",        "EA",  "VALVE",   "BRAY",   "S70-0100-11H","ONGC"),
    ("ONGC-VLV-003", "CHECK VALVE 3IN CLASS 300 CS SWING TYPE",            "NOS", "VALVE",   "CRANE",  "CV-3-300",    "ONGC"),
    ("ONGC-MTR-001", "EXPLOSION PROOF MOTOR 7.5KW 415V 50HZ 960RPM TEFC", "NOS", "MOTOR",   "CG",     "EXME7.5",     "ONGC"),
    ("ONGC-PIP-001", "SS PIPE 1IN SCH80 SEAMLESS ASTM A312 TP316",         "MTR", "PIPE",    "TUBACEX",None,          "ONGC"),
    ("ONGC-PIP-002", "STAINLESS STEEL PIPE 1\" SCHEDULE 80 SMLS",          "MTR", "PIPE",    "SANDVIK",None,          "ONGC"),

    # === NTPC source materials ===
    ("NTPC-MTR-001", "3-PHASE INDUCTION MOTOR 37KW 415V 1480RPM ODP",      "NOS", "MOTOR",   "SIEMENS","1LA7163-4AA",  "NTPC"),
    ("NTPC-MTR-002", "INDUCTION MOTOR 37KW 415V 50HZ 3PHASE ODP 1480RPM", "EA",  "MOTOR",   "WEG",    "W22-37KW",     "NTPC"),
    ("NTPC-MTR-003", "HV MOTOR 55KW 6600V 3PH TEFC 1485RPM SLIP RING",    "NOS", "MOTOR",   "BHEL",   "HXGK560-55KW", "NTPC"),
    ("NTPC-VLV-001", "BUTTERFLY VALVE 6IN CLASS 150 CAST IRON WAFER TYPE", "NOS", "VALVE",   "FLOWSERVE","BFV-6-150-CI","NTPC"),
    ("NTPC-VLV-002", "GLOBE VALVE 4IN CLASS 600 ALLOY STEEL BW ENDS",      "NOS", "VALVE",   "AUDCO",  "GLV-4-600-AS", "NTPC"),
    ("NTPC-BRG-001", "SELF ALIGNING BALL BEARING 1210 50X90X20MM",         "NOS", "BEARING", "SKF",    "1210ETN9",     "NTPC"),
    ("NTPC-PMP-001", "CENTRIFUGAL PUMP 200LPM 50M HEAD 15KW SS IMPELLER",  "NOS", "PUMP",    "KSB",    "ETANORM-200",  "NTPC"),
    ("NTPC-PMP-002", "CENTRIFUGAL PUMP 50 LPM 30 METER HEAD 5.5KW CI",    "EA",  "PUMP",    "FLOWMORE","FM-50-30",     "NTPC"),

    # === SAIL source materials ===
    ("SAIL-BRG-001", "TAPER ROLLER BRG 30205 25X52X15MM",                  "NOS", "BEARING", "TIMKEN", "30205",        "SAIL"),
    ("SAIL-BRG-002", "ANGULAR CONTACT BEARING 7210 50X90X20MM",            "NOS", "BEARING", "FAG",    "7210B.TVP",    "SAIL"),
    ("SAIL-VLV-001", "GATE VALVE 2IN CLASS 150 CARBON STEEL FLANGE",       "NOS", "VALVE",   "NEWAY",  "Z41H-150",     "SAIL"),
    ("SAIL-PIP-001", "CS PIPE 4IN SCHEDULE 40 ERW 6MTR IS:3589",           "MTR", "PIPE",    "SURYA",  None,           "SAIL"),
    ("SAIL-PIP-002", "CARBON STEEL PIPE 4\" SCH 40 ERW LENGTH 6M",         "MTR", "PIPE",    "APL",    None,           "SAIL"),
    ("SAIL-PIP-003", "GI PIPE 3IN MEDIUM DUTY IS:1239",                    "MTR", "PIPE",    "TATA",   None,           "SAIL"),
    ("SAIL-MTR-001", "INDUCTION MOTOR 15KW 415V 1450RPM TEFC 3PH 50HZ",   "NOS", "MOTOR",   "SIEMENS","1LA7163-4AA",  "SAIL"),

    # === GAIL source materials ===
    ("GAIL-VLV-001", "NEEDLE VALVE 0.5IN PN160 SS 316 INSTRUMENT",         "NOS", "VALVE",   "NUPRO",  "SS-8RM",      "GAIL"),
    ("GAIL-VLV-002", "GATE VALVE 2IN 150LB CS RF FLANGED",                 "NOS", "VALVE",   "API",    "GV-2-150-RF", "GAIL"),
    ("GAIL-PIP-001", "CARBON STEEL PIPE 2IN SCHEDULE 40 SEAMLESS",         "MTR", "PIPE",    "STEEL-AX",None,         "GAIL"),
    ("GAIL-BRG-001", "DEEP GROOVE BALL BEARING 6205-2RS 25X52X15MM",       "NOS", "BEARING", "INA",    "62052RS",     "GAIL"),
    ("GAIL-PMP-001", "SUBMERSIBLE PUMP 500LPM 20M HEAD 7.5KW",             "NOS", "PUMP",    "GRUNDFOS","SP30-3",     "GAIL"),
]

SOURCE_IDS = {}   # legacy_code → source_material_id


def seed_source_materials(db: Session):
    for row in SOURCE_ROWS:
        legacy_code, desc, uom, cat, mfr, mpn, cpse_code = row
        cpse_id = CPSE_IDS.get(cpse_code)
        if not cpse_id:
            continue
        obj = exists(db, SourceMaterial, cpse_id=cpse_id, legacy_material_code=legacy_code)
        if not obj:
            sid = uid("SM-")
            obj = SourceMaterial(
                source_material_id=sid,
                cpse_id=cpse_id,
                legacy_material_code=legacy_code,
                raw_description=desc,
                raw_uom=uom,
                raw_category=cat,
                manufacturer=mfr,
                manufacturer_part_number=mpn,
                source_system="SAP-ECC",
                source_file=f"{cpse_code}_materials_2024.csv",
                created_at=ago(days=rng.randint(1, 90)),
            )
            db.add(obj)
            db.flush()
        SOURCE_IDS[legacy_code] = obj.source_material_id
    db.commit()
    log.info(f"✅ Source Materials: {len(SOURCE_ROWS)}")


# ─────────────────────────────────────────────────────────────────────────────
# NORMALIZED MATERIALS + MATCH RESULTS + MAPPINGS
# ─────────────────────────────────────────────────────────────────────────────

# Maps source legacy_code → (national_material_code, mapping_type, final_score, status)
MATCH_MAP = [
    # Exact duplicates
    ("BHEL-BRG-001", "NM-BRG-001", "EXACT_DUPLICATE",         0.97, "APPROVED"),
    ("BHEL-BRG-002", "NM-BRG-001", "NEAR_DUPLICATE",          0.91, "APPROVED"),
    ("GAIL-BRG-001", "NM-BRG-001", "EXACT_DUPLICATE",         0.96, "PENDING"),
    ("ONGC-BRG-001", "NM-BRG-001", "NEAR_DUPLICATE",          0.88, "PENDING"),
    # Near duplicates
    ("BHEL-BRG-003", "NM-BRG-001", "NEAR_DUPLICATE",          0.82, "PENDING"),
    ("BHEL-BRG-004", "NM-BRG-002", "FUNCTIONALLY_EQUIVALENT", 0.78, "PENDING"),
    # Valves
    ("BHEL-VLV-001", "NM-VLV-001", "NEAR_DUPLICATE",          0.90, "APPROVED"),
    ("BHEL-VLV-002", "NM-VLV-001", "EXACT_DUPLICATE",         0.95, "APPROVED"),
    ("ONGC-VLV-001", "NM-VLV-002", "EXACT_DUPLICATE",         0.97, "PENDING"),
    ("ONGC-VLV-002", "NM-VLV-002", "NEAR_DUPLICATE",          0.89, "PENDING"),
    ("ONGC-VLV-003", "NM-VLV-004", "EXACT_DUPLICATE",         0.93, "APPROVED"),
    ("NTPC-VLV-001", "NM-VLV-003", "EXACT_DUPLICATE",         0.96, "PENDING"),
    ("NTPC-VLV-002", "NM-VLV-005", "NEAR_DUPLICATE",          0.87, "PENDING"),
    ("SAIL-VLV-001", "NM-VLV-001", "NEAR_DUPLICATE",          0.85, "REJECTED"),
    ("GAIL-VLV-001", "NM-VLV-006", "NEAR_DUPLICATE",          0.88, "PENDING"),
    ("GAIL-VLV-002", "NM-VLV-001", "FUNCTIONALLY_EQUIVALENT", 0.74, "PENDING"),
    # Motors
    ("BHEL-MTR-001", "NM-MTR-001", "EXACT_DUPLICATE",         0.98, "APPROVED"),
    ("BHEL-MTR-002", "NM-MTR-001", "NEAR_DUPLICATE",          0.91, "APPROVED"),
    ("ONGC-MTR-001", "NM-MTR-002", "FUNCTIONALLY_EQUIVALENT", 0.72, "PENDING"),
    ("NTPC-MTR-001", "NM-MTR-003", "EXACT_DUPLICATE",         0.97, "APPROVED"),
    ("NTPC-MTR-002", "NM-MTR-003", "NEAR_DUPLICATE",          0.88, "PENDING"),
    ("NTPC-MTR-003", "NM-MTR-004", "NEAR_DUPLICATE",          0.85, "PENDING"),
    ("SAIL-MTR-001", "NM-MTR-001", "NEAR_DUPLICATE",          0.89, "PENDING"),
    # Pipes
    ("BHEL-PIP-001", "NM-PIP-001", "EXACT_DUPLICATE",         0.96, "APPROVED"),
    ("BHEL-PIP-002", "NM-PIP-001", "NEAR_DUPLICATE",          0.90, "PENDING"),
    ("ONGC-PIP-001", "NM-PIP-002", "EXACT_DUPLICATE",         0.95, "APPROVED"),
    ("ONGC-PIP-002", "NM-PIP-002", "NEAR_DUPLICATE",          0.87, "PENDING"),
    ("SAIL-PIP-001", "NM-PIP-003", "NEAR_DUPLICATE",          0.88, "PENDING"),
    ("SAIL-PIP-002", "NM-PIP-003", "NEAR_DUPLICATE",          0.85, "PENDING"),
    ("SAIL-PIP-003", "NM-PIP-004", "EXACT_DUPLICATE",         0.94, "PENDING"),
    ("GAIL-PIP-001", "NM-PIP-001", "FUNCTIONALLY_EQUIVALENT", 0.76, "PENDING"),
    # Bearings
    ("ONGC-BRG-002", "NM-BRG-003", "EXACT_DUPLICATE",         0.96, "APPROVED"),
    ("NTPC-BRG-001", "NM-BRG-004", "EXACT_DUPLICATE",         0.97, "PENDING"),
    ("SAIL-BRG-001", "NM-BRG-005", "NEAR_DUPLICATE",          0.88, "PENDING"),
    ("SAIL-BRG-002", "NM-BRG-006", "NEAR_DUPLICATE",          0.89, "PENDING"),
    # Pumps
    ("BHEL-PMP-001", "NM-PMP-001", "EXACT_DUPLICATE",         0.95, "APPROVED"),
    ("NTPC-PMP-001", "NM-PMP-002", "EXACT_DUPLICATE",         0.97, "PENDING"),
    ("NTPC-PMP-002", "NM-PMP-001", "NEAR_DUPLICATE",          0.84, "PENDING"),
    ("GAIL-PMP-001", "NM-PMP-003", "EXACT_DUPLICATE",         0.96, "PENDING"),
]


def _risk_for_score(score: float) -> str:
    if score >= 0.90: return "LOW"
    if score >= 0.75: return "MEDIUM"
    return "HIGH"


def seed_normalized_and_matches(db: Session):
    norm_count = 0
    match_count = 0
    mapping_count = 0

    for legacy_code, nat_code, match_type, final_score, mapping_status in MATCH_MAP:
        source_id = SOURCE_IDS.get(legacy_code)
        nat_mat_id = NAT_MAT_IDS.get(nat_code)
        if not source_id or not nat_mat_id:
            continue

        # ── NormalizedMaterial ──────────────────────────────────────────────
        norm_id = f"NORM-{uuid.uuid4().hex[:10]}"
        try:
            norm_obj = exists(db, NormalizedMaterial, source_material_id=source_id, normalization_version="demo-v1")
            if not norm_obj:
                cat_code = nat_code.split("-")[1]  # e.g., BRG, VLV, MTR
                cls_code_map = {"BRG": "MECH-BRG", "VLV": "MECH-VLV", "PIP": "MECH-PIP", "PMP": "MECH-PMP", "MTR": "ELEC-MTR", "GSK": "MECH-GSK"}
                cat = cls_code_map.get(cat_code, "MECH")
                norm_obj = NormalizedMaterial(
                    normalized_material_id=norm_id,
                    source_material_id=source_id,
                    normalized_description=next((r[1] for r in SOURCE_ROWS if r[0] == legacy_code), ""),
                    canonical_uom="EA",
                    category_code=cat,
                    attributes={},
                    normalization_version="demo-v1",
                    normalization_method="deterministic",
                    confidence=final_score,
                    embedding=rand_embedding(768),
                )
                db.add(norm_obj)
                db.flush()
                norm_count += 1
            else:
                norm_id = norm_obj.normalized_material_id
        except Exception as e:
            db.rollback()
            log.warning(f"Skipped norm for {legacy_code}: {e}")
            continue

        # ── MatchResult ─────────────────────────────────────────────────────
        try:
            match_obj = exists(db, MatchResult, material_a_id=norm_id, material_b_id=nat_mat_id)
            if not match_obj:
                sem = round(final_score - rng.uniform(0, 0.05), 4)
                attr = round(final_score + rng.uniform(0, 0.03), 4)
                attr = min(attr, 1.0)
                match_id = uid("MR-")
                match_obj = MatchResult(
                    match_id=match_id,
                    material_a_id=norm_id,
                    material_b_id=nat_mat_id,
                    semantic_score=max(0, sem),
                    attribute_score=max(0, attr),
                    rule_score=0.90,
                    final_score=final_score,
                    match_type=match_type,
                    positive_evidence={
                        "retrieval_reason": "Vector similarity search (cosine)",
                        "semantic_similarity": sem,
                        "attribute_matches": ["category", "manufacturer"],
                        "classification_compatibility": "MATCH",
                    },
                    negative_evidence={},
                    conflicts={},
                    recommendation="ALLOW_AUTOMATION" if final_score >= 0.90 else "REQUIRES_REVIEW",
                    risk_level=_risk_for_score(final_score),
                    requires_human_review=(final_score < 0.90),
                    model_version="demo-v1",
                    prompt_version="N/A",
                    rules_version="1.0.0",
                    created_at=ago(days=rng.randint(0, 30)),
                )
                db.add(match_obj)
                db.flush()
                match_count += 1
            else:
                match_id = match_obj.match_id
        except Exception as e:
            db.rollback()
            log.warning(f"Skipped match for {legacy_code}: {e}")
            continue

        # ── MaterialMapping ─────────────────────────────────────────────────
        try:
            map_obj = exists(db, MaterialMapping, source_material_id=source_id, national_material_id=nat_mat_id)
            if not map_obj:
                mapping_id = uid("MAP-")
                map_obj = MaterialMapping(
                    mapping_id=mapping_id,
                    source_material_id=source_id,
                    national_material_id=nat_mat_id,
                    mapping_type=match_type,
                    confidence=final_score,
                    status=mapping_status,
                    is_ai_suggested=True,
                    created_by="admin",
                    approved_by="admin" if mapping_status == "APPROVED" else None,
                    approved_at=ago(days=rng.randint(0, 10)) if mapping_status == "APPROVED" else None,
                )
                db.add(map_obj)
                db.flush()
                mapping_count += 1
        except Exception as e:
            db.rollback()
            log.warning(f"Skipped mapping for {legacy_code}: {e}")
            continue

    db.commit()
    log.info(f"✅ Normalized Materials: {norm_count}")
    log.info(f"✅ Match Results: {match_count}")
    log.info(f"✅ Mappings: {mapping_count}")


# ─────────────────────────────────────────────────────────────────────────────
# PROCESSING JOBS
# ─────────────────────────────────────────────────────────────────────────────

def seed_processing_jobs(db: Session):
    jobs = [
        {"job_id": uid("JOB-"), "job_type": "UPLOAD_PROCESSING", "status": "COMPLETED", "total_records": 12, "records_processed": 12, "successful": 11, "failed": 1, "current_stage": "FINISHED", "started_at": ago(days=5),  "completed_at": ago(days=5, hours=-1)},
        {"job_id": uid("JOB-"), "job_type": "UPLOAD_PROCESSING", "status": "COMPLETED", "total_records": 8,  "records_processed": 8,  "successful": 8,  "failed": 0, "current_stage": "FINISHED", "started_at": ago(days=10), "completed_at": ago(days=10, hours=-1)},
        {"job_id": uid("JOB-"), "job_type": "UPLOAD_PROCESSING", "status": "COMPLETED", "total_records": 10, "records_processed": 10, "successful": 10, "failed": 0, "current_stage": "FINISHED", "started_at": ago(days=20), "completed_at": ago(days=20, hours=-1)},
        {"job_id": uid("JOB-"), "job_type": "UPLOAD_PROCESSING", "status": "FAILED",    "total_records": 5,  "records_processed": 3,  "successful": 2,  "failed": 3, "current_stage": "AI_MATCHING","started_at": ago(days=3), "completed_at": ago(days=3, hours=-1)},
        {"job_id": uid("JOB-"), "job_type": "UPLOAD_PROCESSING", "status": "COMPLETED", "total_records": 7,  "records_processed": 7,  "successful": 7,  "failed": 0, "current_stage": "FINISHED", "started_at": ago(days=1),  "completed_at": ago(days=1, hours=-1)},
    ]
    for j in jobs:
        if not exists(db, ProcessingJob, job_id=j["job_id"]):
            db.add(ProcessingJob(**j))
    db.commit()
    log.info(f"✅ Processing Jobs: {len(jobs)}")


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────

def seed_notifications(db: Session):
    notifs = [
        {"id": uid("NOTIF-"), "user_id": "admin",    "type": "MATCH_READY",    "title": "38 AI Matches Ready for Review", "message": "New batch of AI-generated match candidates is ready for human review.", "is_read": False},
        {"id": uid("NOTIF-"), "user_id": "engineer1","type": "MATCH_READY",    "title": "12 High-Confidence Matches",     "message": "12 new matches above 90% confidence are ready to review.", "is_read": False},
        {"id": uid("NOTIF-"), "user_id": "steward1", "type": "APPROVAL_NEEDED","title": "Mapping Requires Approval",      "message": "Material mapping BHEL-VLV-001 → NM-VLV-001 requires your approval.", "is_read": True},
        {"id": uid("NOTIF-"), "user_id": "admin",    "type": "JOB_COMPLETED",  "title": "Upload Processing Complete",     "message": "ONGC materials upload processed 8/8 records successfully.", "is_read": True},
        {"id": uid("NOTIF-"), "user_id": "admin",    "type": "JOB_FAILED",     "title": "Upload Processing Failed",       "message": "SAIL-2024Q3 upload failed on 3/5 records. Check job details.", "is_read": False},
    ]
    for n in notifs:
        if not exists(db, Notification, id=n["id"]):
            db.add(Notification(**n, timestamp=ago(hours=rng.randint(0, 48))))
    db.commit()
    log.info(f"✅ Notifications: {len(notifs)}")


# ─────────────────────────────────────────────────────────────────────────────
# MODEL & PROMPT REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

def seed_registries(db: Session):
    if not db.query(ModelRegistry).first():
        db.add(ModelRegistry(
            model_name="all-mpnet-base-v2", model_version="v1.0",
            provider="sentence-transformers", task="EMBEDDING",
            embedding_dimension=768, deployment_status="ACTIVE",
        ))
        db.add(ModelRegistry(
            model_name="classifier-multipass", model_version="v2.0",
            provider="local-rules", task="CLASSIFICATION",
            embedding_dimension=None, deployment_status="ACTIVE",
        ))
        db.commit()
    if not db.query(PromptRegistry).first():
        db.add(PromptRegistry(
            task="ATTRIBUTE_EXTRACTION",
            prompt_version="v1.0-deterministic",
            prompt_template="Extract technical attributes from the following material description: {text}",
            is_active=True,
        ))
        db.commit()
    log.info("✅ Model & Prompt Registries")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("National Material Intelligence Platform — Seed Demo Data")
    log.info("=" * 60)

    db: Session = SessionLocal()
    try:
        seed_roles(db)
        seed_cpses(db)
        seed_users(db)
        seed_classifications(db)
        seed_uoms(db)
        seed_critical_rules(db)
        seed_global_config(db)
        seed_national_materials(db)
        seed_source_materials(db)
        seed_normalized_and_matches(db)
        seed_processing_jobs(db)
        seed_notifications(db)
        seed_registries(db)

        log.info("\n" + "=" * 60)
        log.info("🎉 Demo data seeding complete!")
        log.info("")
        log.info("Demo Login Credentials:")
        log.info("  Username: admin      Password: admin123  (Full Admin)")
        log.info("  Username: engineer1  Password: demo123   (Engineer)")
        log.info("  Username: steward1   Password: demo123   (Data Steward)")
        log.info("  Username: auditor1   Password: demo123   (Auditor)")
        log.info("  Username: cpse1      Password: demo123   (CPSE User)")
        log.info("")
        log.info("Open http://localhost:5173 to access the frontend.")
        log.info("=" * 60)
    except Exception as e:
        db.rollback()
        log.error(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
