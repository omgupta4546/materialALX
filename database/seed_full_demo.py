"""
seed_full_demo.py - Comprehensive demo data seeder.

Populates ALL pipeline tables with realistic synthetic data so every
feature in the platform lights up: matches, national materials, mappings,
approvals, feedback, jobs, data quality, procurement, etc.

Run from the backend directory:
    .venv\\Scripts\\python.exe ..\\database\\seed_full_demo.py
"""

import os, sys, json, csv, uuid, hashlib, random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

from sqlalchemy.orm import Session, sessionmaker
from app.core.connection import engine
from app.models.base import (
    Base, SourceMaterial, NormalizedMaterial, NationalMaterial,
    MatchResult, MaterialMapping, Approval, AuditLog, FeedbackEvent,
    ProcessingJob, FileUpload, DataQualityMetrics, ProcurementRecord,
    GlobalMatchingConfig, Notification, Classification,
)

random.seed(42)

# ──────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────

def uid(text: str) -> str:
    return str(uuid.UUID(hashlib.md5(text.encode()).hexdigest()))

def rand_id() -> str:
    return str(uuid.uuid4())

def rand_dt(days_back=90) -> datetime:
    return datetime.utcnow() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )

def rand_score(low=0.5, high=1.0) -> float:
    return round(random.uniform(low, high), 4)

# ──────────────────────────────────────────────────────────────────────────
# MATERIAL GROUPING (simulate what AI would do)
# ──────────────────────────────────────────────────────────────────────────

# Map demo materials into groups by description similarity
MATERIAL_GROUPS = {
    "GATE VALVE": {"code": "NM-VLV-001", "desc": "GATE VALVE FLANGED CARBON STEEL", "cat": "CAT-VLV", "uom": "EACH"},
    "BALL BEARING 6205": {"code": "NM-BRG-001", "desc": "DEEP GROOVE BALL BEARING 6205-2RS", "cat": "CAT-BRG", "uom": "EACH"},
    "CARBON STEEL PIPE": {"code": "NM-PIP-001", "desc": "CARBON STEEL PIPE SEAMLESS", "cat": "CAT-PIP", "uom": "EACH"},
    "AC MOTOR 1.5KW": {"code": "NM-MTR-001", "desc": "AC MOTOR 1.5KW 415V 50HZ TEFC", "cat": "CAT-MTR", "uom": "EACH"},
    "HEX BOLT": {"code": "NM-FST-001", "desc": "HEX BOLT STAINLESS STEEL 304", "cat": "CAT-FST", "uom": "EACH"},
    "CENTRIFUGAL PUMP": {"code": "NM-PMP-001", "desc": "CENTRIFUGAL PUMP HORIZONTAL", "cat": "CAT-PMP", "uom": "EACH"},
    "CHECK VALVE": {"code": "NM-VLV-002", "desc": "CHECK VALVE SWING TYPE", "cat": "CAT-VLV", "uom": "EACH"},
    "BALL VALVE": {"code": "NM-VLV-003", "desc": "BALL VALVE FULL BORE FLANGED", "cat": "CAT-VLV", "uom": "EACH"},
    "BUTTERFLY VALVE": {"code": "NM-VLV-004", "desc": "BUTTERFLY VALVE WAFER TYPE", "cat": "CAT-VLV", "uom": "EACH"},
    "GASKET": {"code": "NM-GSK-001", "desc": "SPIRAL WOUND GASKET SS304", "cat": "CAT-GSK", "uom": "EACH"},
    "FLANGE": {"code": "NM-FLG-001", "desc": "WELD NECK FLANGE CARBON STEEL", "cat": "CAT-FLG", "uom": "EACH"},
    "BEARING ROLLER": {"code": "NM-BRG-002", "desc": "TAPERED ROLLER BEARING", "cat": "CAT-BRG", "uom": "EACH"},
    "COUPLING": {"code": "NM-CPL-001", "desc": "FLEXIBLE COUPLING JAW TYPE", "cat": "CAT-CPL", "uom": "EACH"},
    "TRANSFORMER": {"code": "NM-TRF-001", "desc": "POWER TRANSFORMER 3-PHASE", "cat": "CAT-ELC", "uom": "EACH"},
    "CABLE": {"code": "NM-CBL-001", "desc": "POWER CABLE XLPE ARMOURED", "cat": "CAT-ELC", "uom": "MTR"},
    "FILTER ELEMENT": {"code": "NM-FLT-001", "desc": "HYDRAULIC FILTER ELEMENT", "cat": "CAT-FLT", "uom": "EACH"},
    "O-RING": {"code": "NM-SEL-001", "desc": "O-RING VITON", "cat": "CAT-SEL", "uom": "EACH"},
    "STUD BOLT": {"code": "NM-FST-002", "desc": "STUD BOLT B7 WITH HEAVY HEX NUT", "cat": "CAT-FST", "uom": "EACH"},
    "WELDING ROD": {"code": "NM-WLD-001", "desc": "WELDING ELECTRODE E7018", "cat": "CAT-WLD", "uom": "KG"},
    "PUMP SEAL": {"code": "NM-SEL-002", "desc": "MECHANICAL SEAL SINGLE SPRING", "cat": "CAT-SEL", "uom": "EACH"},
    "SAFETY VALVE": {"code": "NM-VLV-005", "desc": "PRESSURE SAFETY VALVE SPRING LOADED", "cat": "CAT-VLV", "uom": "EACH"},
    "EXPANSION JOINT": {"code": "NM-PIP-002", "desc": "EXPANSION JOINT BELLOWS TYPE SS", "cat": "CAT-PIP", "uom": "EACH"},
    "PRESSURE GAUGE": {"code": "NM-INS-001", "desc": "PRESSURE GAUGE BOURDON TUBE SS", "cat": "CAT-INS", "uom": "EACH"},
    "TEMPERATURE SENSOR": {"code": "NM-INS-002", "desc": "RTD PT100 TEMPERATURE SENSOR", "cat": "CAT-INS", "uom": "EACH"},
    "GEARBOX": {"code": "NM-GBX-001", "desc": "HELICAL GEARBOX SPEED REDUCER", "cat": "CAT-GBX", "uom": "EACH"},
    "NUT": {"code": "NM-FST-003", "desc": "HEAVY HEX NUT GRADE 2H", "cat": "CAT-FST", "uom": "EACH"},
    "WASHER": {"code": "NM-FST-004", "desc": "FLAT WASHER STAINLESS STEEL", "cat": "CAT-FST", "uom": "EACH"},
    "CONVEYOR BELT": {"code": "NM-CVR-001", "desc": "RUBBER CONVEYOR BELT EP300", "cat": "CAT-CVR", "uom": "MTR"},
    "PIPE FITTING": {"code": "NM-PIP-003", "desc": "PIPE ELBOW 90 DEG CS BUTT WELD", "cat": "CAT-PIP", "uom": "EACH"},
    "MOTOR 5KW": {"code": "NM-MTR-002", "desc": "AC MOTOR 5KW 415V 50HZ IP55", "cat": "CAT-MTR", "uom": "EACH"},
}

def classify_material(desc: str) -> tuple:
    """Classify a source material description into a national material group."""
    desc_upper = desc.upper()
    for keyword, info in MATERIAL_GROUPS.items():
        if keyword in desc_upper:
            return keyword, info
    # Fallback: pick a random group
    keyword = random.choice(list(MATERIAL_GROUPS.keys()))
    return keyword, MATERIAL_GROUPS[keyword]

# ──────────────────────────────────────────────────────────────────────────
# SEEDERS
# ──────────────────────────────────────────────────────────────────────────

def seed_global_config(session: Session):
    print("  Seeding global matching config...")
    existing = session.query(GlobalMatchingConfig).filter_by(is_latest=True).first()
    if existing:
        print("    Already exists, skipping")
        return
    config = GlobalMatchingConfig(
        config_id=rand_id(),
        version=1, is_latest=True,
        weight_semantic=0.30, weight_attribute=0.40,
        weight_manufacturer=0.10, weight_mpn=0.20,
        threshold_exact_duplicate=0.95, threshold_near_duplicate=0.85,
        threshold_functionally_equivalent=0.65, threshold_related=0.50,
        auto_approve_enabled=True, auto_approve_threshold=0.95,
        auto_approve_max_risk_level="LOW",
        created_by="demo_admin", change_note="Initial configuration"
    )
    session.add(config)
    session.flush()
    print("    Config created")


def seed_processing_jobs(session: Session):
    print("  Seeding processing jobs...")
    if session.query(ProcessingJob).count() > 0:
        print("    Already seeded, skipping")
        return
    jobs = [
        ProcessingJob(job_id=rand_id(), job_type="UPLOAD_PROCESSING", status="COMPLETED",
                      records_processed=82, total_records=82, successful=80, failed=2,
                      started_at=rand_dt(60), completed_at=rand_dt(59)),
        ProcessingJob(job_id=rand_id(), job_type="UPLOAD_PROCESSING", status="COMPLETED",
                      records_processed=92, total_records=92, successful=91, failed=1,
                      started_at=rand_dt(55), completed_at=rand_dt(54)),
        ProcessingJob(job_id=rand_id(), job_type="UPLOAD_PROCESSING", status="COMPLETED",
                      records_processed=83, total_records=83, successful=83, failed=0,
                      started_at=rand_dt(50), completed_at=rand_dt(49)),
        ProcessingJob(job_id=rand_id(), job_type="UPLOAD_PROCESSING", status="COMPLETED",
                      records_processed=72, total_records=72, successful=70, failed=2,
                      started_at=rand_dt(45), completed_at=rand_dt(44)),
        ProcessingJob(job_id=rand_id(), job_type="UPLOAD_PROCESSING", status="COMPLETED",
                      records_processed=71, total_records=71, successful=71, failed=0,
                      started_at=rand_dt(40), completed_at=rand_dt(39)),
        ProcessingJob(job_id=rand_id(), job_type="NORMALIZATION", status="COMPLETED",
                      records_processed=400, total_records=400, successful=395, failed=5,
                      started_at=rand_dt(30), completed_at=rand_dt(29)),
        ProcessingJob(job_id=rand_id(), job_type="MATCHING", status="COMPLETED",
                      records_processed=395, total_records=395, successful=390, failed=5,
                      started_at=rand_dt(20), completed_at=rand_dt(19)),
        ProcessingJob(job_id=rand_id(), job_type="MATCHING", status="FAILED",
                      records_processed=50, total_records=100, successful=48, failed=2,
                      errors={"message": "Embedding service timeout after 300s"},
                      started_at=rand_dt(10), completed_at=rand_dt(9)),
    ]
    for j in jobs:
        session.add(j)
    session.flush()
    print(f"    {len(jobs)} jobs created")


def seed_file_uploads(session: Session):
    print("  Seeding file uploads...")
    if session.query(FileUpload).count() > 0:
        print("    Already seeded, skipping")
        return
    cpse_codes = ["NTPC", "ONGC", "SAIL", "IOCL", "BHEL"]
    for i, code in enumerate(cpse_codes):
        fu = FileUpload(
            id=rand_id(), cpse_code=code,
            filename=f"{code.lower()}_material_catalog_2025.csv",
            file_size=random.randint(50000, 500000),
            uploaded_by="demo_admin",
            status="COMPLETED",
            timestamp=rand_dt(60 - i * 5)
        )
        session.add(fu)
    session.flush()
    print("    5 file uploads created")


def seed_normalized_and_national(session: Session):
    """
    For each source material:
    1. Create a NormalizedMaterial
    2. Assign it to a NationalMaterial group
    """
    print("  Seeding normalized materials + national materials...")

    if session.query(NormalizedMaterial).count() > 0:
        print("    Already seeded, skipping")
        return

    # Get all source materials
    sources = session.query(SourceMaterial).all()
    if not sources:
        print("    No source materials found!")
        return

    # Get classification map
    classifications = {c.code: c.classification_id for c in session.query(Classification).all()}

    # First pass: create all NationalMaterial records
    national_map = {}  # group_key -> national_material_id
    for keyword, info in MATERIAL_GROUPS.items():
        nm_id = uid(f"national_{info['code']}")
        cls_id = classifications.get(info['cat'])
        nm = NationalMaterial(
            national_material_id=nm_id,
            national_material_code=info['code'],
            canonical_description=info['desc'],
            classification_id=cls_id,
            canonical_uom=info['uom'],
            status="ACTIVE",
            version=1,
            attributes={"source": "demo_seed", "group_key": keyword},
            created_by="demo_admin",
        )
        session.add(nm)
        national_map[keyword] = nm_id

    session.flush()
    print(f"    {len(national_map)} national materials created")

    # Second pass: create NormalizedMaterial for each source
    norm_count = 0
    category_keywords = {
        "CAT-VLV": ["VALVE", "GATE", "BALL", "CHECK", "BUTTERFLY", "SAFETY", "GLOBE"],
        "CAT-BRG": ["BEARING", "BRG"],
        "CAT-PIP": ["PIPE", "TUBE", "ELBOW", "TEE", "REDUCER", "FITTING", "EXPANSION"],
        "CAT-MTR": ["MOTOR", "DRIVE"],
        "CAT-FST": ["BOLT", "NUT", "WASHER", "SCREW", "STUD"],
        "CAT-PMP": ["PUMP", "CENTRIFUGAL"],
        "CAT-GSK": ["GASKET"],
        "CAT-FLG": ["FLANGE"],
        "CAT-ELC": ["CABLE", "TRANSFORMER", "SWITCH", "BREAKER"],
        "CAT-FLT": ["FILTER"],
        "CAT-SEL": ["SEAL", "O-RING", "RING"],
        "CAT-WLD": ["WELDING", "ELECTRODE", "WELD"],
        "CAT-INS": ["GAUGE", "SENSOR", "TRANSMITTER", "INSTRUMENT"],
        "CAT-GBX": ["GEARBOX", "GEAR"],
        "CAT-CVR": ["CONVEYOR", "BELT"],
        "CAT-CPL": ["COUPLING"],
    }

    def detect_category(desc: str) -> str:
        desc_upper = desc.upper()
        for cat, keywords in category_keywords.items():
            for kw in keywords:
                if kw in desc_upper:
                    return cat
        return "CAT-VLV"  # fallback

    for src in sources:
        desc = src.raw_description or ""
        group_key, group_info = classify_material(desc)
        cat_code = detect_category(desc)
        cls_id = classifications.get(cat_code)

        # Simulate normalized description
        norm_desc = desc.upper().strip()
        for word in ["THE", "A", "AN", "FOR", "OF", "WITH"]:
            norm_desc = norm_desc.replace(f" {word} ", " ")

        confidence = rand_score(0.65, 0.98)
        nm = NormalizedMaterial(
            normalized_material_id=uid(f"norm_{src.source_material_id}"),
            source_material_id=src.source_material_id,
            raw_description=desc,
            normalized_description=norm_desc,
            canonical_uom=src.raw_uom or group_info['uom'],
            category_code=cat_code if cls_id else None,
            normalized_manufacturer=random.choice(["KITZ", "SKF", "ABB", "Siemens", "KSB", "Jindal", "Bossard", "Parker", "Emerson", "Honeywell"]),
            normalized_mpn=f"MPN-{random.randint(1000,9999)}",
            attributes={"material_grade": random.choice(["WCB", "SS304", "SS316", "CS", "A105"]),
                        "size": random.choice(["2 inch", "4 inch", "6 inch", "8 inch", "10 inch", "DN50", "DN100"]),
                        "pressure_class": random.choice(["150#", "300#", "600#", "900#", ""])},
            normalization_version="v1.0",
            normalization_method="llm_gpt4",
            confidence=confidence,
            processing_time_ms=random.randint(200, 3000),
        )
        session.add(nm)
        norm_count += 1
        if norm_count % 100 == 0:
            session.flush()

    session.flush()
    print(f"    {norm_count} normalized materials created")
    return national_map


def seed_matches_and_mappings(session: Session, national_map: dict):
    """Create match results and mappings between normalized and national materials."""
    print("  Seeding match results + mappings...")

    if session.query(MatchResult).count() > 0:
        print("    Already seeded, skipping")
        return

    norms = session.query(NormalizedMaterial).all()
    match_count = 0
    mapping_count = 0

    match_types = ["EXACT_DUPLICATE", "NEAR_DUPLICATE", "FUNCTIONALLY_EQUIVALENT"]
    risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    recommendations = ["AUTO_APPROVE", "APPROVE", "REVIEW", "ENGINEERING_REVIEW", "REJECT"]
    mapping_statuses = ["APPROVED", "APPROVED", "APPROVED", "PENDING", "PENDING", "REJECTED", "ENGINEERING_REVIEW"]

    for norm in norms:
        desc = norm.raw_description or ""
        group_key, group_info = classify_material(desc)
        nat_id = national_map.get(group_key)
        if not nat_id:
            continue

        # Generate match scores
        semantic = rand_score(0.55, 0.99)
        attribute = rand_score(0.40, 0.99)
        rule = rand_score(0.60, 1.0)
        final = round(0.3 * semantic + 0.4 * attribute + 0.2 * rule + 0.1 * random.uniform(0.5, 1.0), 4)
        final = min(final, 1.0)

        # Determine match type based on score
        if final >= 0.95:
            m_type = "EXACT_DUPLICATE"
            risk = "LOW"
            rec = "AUTO_APPROVE"
        elif final >= 0.85:
            m_type = "NEAR_DUPLICATE"
            risk = random.choice(["LOW", "MEDIUM"])
            rec = "APPROVE"
        elif final >= 0.65:
            m_type = "FUNCTIONALLY_EQUIVALENT"
            risk = random.choice(["MEDIUM", "HIGH"])
            rec = random.choice(["REVIEW", "ENGINEERING_REVIEW"])
        else:
            m_type = "FUNCTIONALLY_EQUIVALENT"
            risk = random.choice(["HIGH", "CRITICAL"])
            rec = "REJECT"

        match_id = rand_id()
        match = MatchResult(
            match_id=match_id,
            material_a_id=norm.normalized_material_id,
            material_b_id=nat_id,
            semantic_score=semantic,
            attribute_score=attribute,
            rule_score=rule,
            final_score=final,
            match_type=m_type,
            positive_evidence={"description_overlap": round(semantic, 2),
                              "manufacturer_match": random.choice([True, False]),
                              "uom_match": True},
            negative_evidence={"missing_attributes": random.randint(0, 3)} if risk in ("HIGH", "CRITICAL") else {},
            conflicts={"critical_attribute_mismatch": True} if risk == "CRITICAL" else {},
            recommendation=rec,
            risk_level=risk,
            requires_human_review=(rec not in ("AUTO_APPROVE",)),
            model_version="gpt-4-turbo-2024-04-09",
            prompt_version="v2.1",
            rules_version="v1.0",
        )
        session.add(match)
        match_count += 1

        # Create mapping
        m_status = random.choice(mapping_statuses)
        if final >= 0.95 and risk == "LOW":
            m_status = "APPROVED"  # Auto-approved
        approved_by = "demo_steward" if m_status == "APPROVED" else None
        approved_at = rand_dt(15) if m_status == "APPROVED" else None

        mapping = MaterialMapping(
            mapping_id=rand_id(),
            source_material_id=norm.source_material_id,
            national_material_id=nat_id,
            mapping_type=m_type,
            confidence=final,
            status=m_status,
            created_by="demo_admin",
            approved_by=approved_by,
            approved_at=approved_at,
            is_ai_suggested=True,
            notes=f"AI-matched with {final:.0%} confidence" if m_status != "REJECTED" else "Rejected: insufficient attribute match"
        )
        session.add(mapping)
        mapping_count += 1

        if match_count % 100 == 0:
            session.flush()

    session.flush()
    print(f"    {match_count} matches, {mapping_count} mappings created")


def seed_approvals_and_feedback(session: Session):
    """Create approval records and feedback events for approved/rejected matches."""
    print("  Seeding approvals + feedback...")

    if session.query(Approval).count() > 0:
        print("    Already seeded, skipping")
        return

    matches = session.query(MatchResult).all()
    approval_count = 0
    feedback_count = 0
    reviewers = ["demo_admin", "demo_steward", "demo_engineer"]

    for match in matches:
        # Only create approval/feedback for ~60% of matches
        if random.random() > 0.6:
            continue

        decision = random.choices(
            ["APPROVED", "REJECTED", "ESCALATED"],
            weights=[0.70, 0.20, 0.10]
        )[0]

        approval = Approval(
            approval_id=rand_id(),
            match_id=match.match_id,
            reviewer_id=random.choice(reviewers),
            decision=decision,
            comment=random.choice([
                "Confirmed - identical material",
                "Attributes match within tolerance",
                "Critical mismatch in pressure rating",
                "Needs engineering verification",
                "Manufacturer part number confirmed",
                "UOM discrepancy - requires review",
                None
            ]),
            review_type=random.choice(["STANDARD", "EXPEDITED", "ENGINEERING"]),
        )
        session.add(approval)
        approval_count += 1

        # Create feedback event
        is_disagree = (decision == "REJECTED" and match.recommendation in ("APPROVE", "AUTO_APPROVE")) or \
                      (decision == "APPROVED" and match.recommendation == "REJECT")

        human_decision = "APPROVED" if decision == "APPROVED" else ("REJECTED" if decision == "REJECTED" else "ENGINEERING_REVIEW")

        feedback = FeedbackEvent(
            event_id=rand_id(),
            reviewer_id=approval.reviewer_id,
            match_id=match.match_id,
            target_id=match.match_id,
            target_type="MATCH",
            ai_match_type=match.match_type,
            ai_final_score=match.final_score,
            ai_risk_level=match.risk_level,
            ai_recommendation=match.recommendation,
            ai_model_version=match.model_version,
            ai_prompt_version=match.prompt_version,
            ai_rules_version=match.rules_version,
            event_type=human_decision,
            human_decision=human_decision,
            reason=approval.comment,
            is_disagreement=is_disagree,
            category_code=random.choice(["CAT-VLV", "CAT-BRG", "CAT-PMP", "CAT-MTR", "CAT-FST", "CAT-PIP"]),
        )
        session.add(feedback)
        feedback_count += 1

    session.flush()
    print(f"    {approval_count} approvals, {feedback_count} feedback events created")


def seed_data_quality(session: Session):
    """Create data quality metrics for each normalized material."""
    print("  Seeding data quality metrics...")

    if session.query(DataQualityMetrics).count() > 0:
        print("    Already seeded, skipping")
        return

    norms = session.query(NormalizedMaterial).all()
    count = 0
    for norm in norms:
        dq = DataQualityMetrics(
            metric_id=rand_id(),
            material_id=norm.normalized_material_id,
            completeness_score=rand_score(0.50, 1.0),
            uniqueness_score=rand_score(0.60, 1.0),
            validity_score=rand_score(0.55, 1.0),
            consistency_score=rand_score(0.50, 1.0),
            standardization_score=rand_score(0.45, 1.0),
            attribute_coverage=rand_score(0.30, 1.0),
            flags=random.choice([
                [],
                ["missing_pressure_class"],
                ["invalid_uom"],
                ["missing_manufacturer"],
                ["missing_pressure_class", "invalid_uom"],
                ["low_confidence_category"],
            ]),
        )
        session.add(dq)
        count += 1
        if count % 100 == 0:
            session.flush()

    session.flush()
    print(f"    {count} data quality records created")


def seed_procurement(session: Session):
    """Seed procurement records from demo_procurement.csv."""
    print("  Seeding procurement records...")

    if session.query(ProcurementRecord).count() > 0:
        print("    Already seeded, skipping")
        return

    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'demo', 'demo_procurement.csv')
    if not os.path.exists(csv_path):
        print("    demo_procurement.csv not found, skipping")
        return

    count = 0
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Find corresponding source material
            cpse_code = row['cpse_code']
            mat_code = row['material_code']
            src_id = uid(f"{cpse_code}_{mat_code}")

            # Verify source material exists
            src = session.get(SourceMaterial, src_id)
            if not src:
                continue

            pr = ProcurementRecord(
                procurement_id=row.get('procurement_id', rand_id()),
                source_material_id=src_id,
                supplier=row.get('supplier', f'Supplier_{random.choice("ABCDE")}'),
                quantity=float(row.get('quantity', 1)),
                unit_price=float(row.get('unit_price', 100)),
                total_spend=float(row.get('total_spend', 100)),
                currency="INR",
                procurement_date=datetime.strptime(row['procurement_date'], '%Y-%m-%d') if row.get('procurement_date') else rand_dt(180),
                plant=row.get('plant', f'PLANT-{random.randint(1,5)}'),
                purchase_order=f"PO-{random.randint(10000, 99999)}",
            )
            session.add(pr)
            count += 1
            if count % 100 == 0:
                session.flush()

    session.flush()
    print(f"    {count} procurement records created")


def seed_audit_log(session: Session):
    """Create sample audit log entries."""
    print("  Seeding audit log...")

    if session.query(AuditLog).count() > 0:
        print("    Already seeded, skipping")
        return

    actions = [
        ("UPLOAD", "file_upload", "Uploaded material catalog"),
        ("NORMALIZE", "source_material", "AI normalization completed"),
        ("MATCH_CREATE", "match_result", "Match candidate generated"),
        ("APPROVE", "material_mapping", "Mapping approved by steward"),
        ("REJECT", "material_mapping", "Mapping rejected"),
        ("RULE_UPDATE", "critical_rule", "Critical rule updated"),
        ("CONFIG_UPDATE", "global_matching_config", "Matching config updated"),
        ("USER_LOGIN", "user_account", "User logged in"),
        ("NATIONAL_CREATE", "national_material", "National material created"),
        ("ENGINEERING_REVIEW", "match_result", "Escalated to engineering review"),
    ]

    count = 0
    for _ in range(50):
        action, entity_type, note = random.choice(actions)
        log = AuditLog(
            audit_id=rand_id(),
            entity_type=entity_type,
            entity_id=rand_id(),
            action=action,
            old_value=None,
            new_value={"note": note},
            actor_id=random.choice(["demo_admin", "demo_steward", "demo_engineer", "demo_auditor"]),
            timestamp=rand_dt(90),
            source="api",
            rules_version="v1.0",
        )
        session.add(log)
        count += 1

    session.flush()
    print(f"    {count} audit log entries created")


def seed_notifications(session: Session):
    """Create sample notifications."""
    print("  Seeding notifications...")

    if session.query(Notification).count() > 0:
        print("    Already seeded, skipping")
        return

    notifs = [
        ("MATCH_READY", "New Match Candidates", "15 new match candidates require your review", "demo_steward"),
        ("UPLOAD_COMPLETE", "Upload Complete", "NTPC material catalog (82 records) processed successfully", "demo_admin"),
        ("APPROVAL_PENDING", "Approvals Waiting", "8 mappings pending your approval", "demo_steward"),
        ("HIGH_RISK", "High Risk Match Detected", "Critical attribute mismatch in VALVE category - engineering review required", "demo_engineer"),
        ("QUALITY_ALERT", "Data Quality Alert", "3 materials flagged with low completeness scores", "demo_admin"),
        ("SYSTEM", "System Update", "Matching rules v1.0 activated by administrator", "demo_admin"),
        ("UPLOAD_COMPLETE", "Upload Complete", "ONGC catalog processing finished with 1 error", "demo_admin"),
        ("MATCH_READY", "Batch Matching Done", "Cross-CPSE matching completed: 42 functional equivalents found", "demo_steward"),
        ("APPROVAL_DONE", "Bulk Approval", "32 low-risk mappings auto-approved per policy", "demo_admin"),
        ("EXPORT_READY", "Export Ready", "CPSE mapping report generated and ready for download", "demo_auditor"),
    ]

    for ntype, title, msg, user in notifs:
        n = Notification(
            id=rand_id(),
            user_id=user,
            type=ntype,
            title=title,
            message=msg,
            is_read=random.choice([True, False]),
            timestamp=rand_dt(30),
        )
        session.add(n)

    session.flush()
    print(f"    {len(notifs)} notifications created")


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────

def main():
    from app.core.connection import DATABASE_URL
    print(f"Database: {DATABASE_URL}")
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        print("\n=== Phase 1: Seed Pipeline Data ===\n")
        seed_global_config(session)
        seed_processing_jobs(session)
        seed_file_uploads(session)
        national_map = seed_normalized_and_national(session)
        if national_map:
            seed_matches_and_mappings(session, national_map)
            seed_approvals_and_feedback(session)
        seed_data_quality(session)
        seed_procurement(session)
        seed_audit_log(session)
        seed_notifications(session)
        session.commit()

        # Print summary
        print("\n=== Seed Summary ===\n")
        tables = [
            ("global_matching_config", GlobalMatchingConfig),
            ("processing_job", ProcessingJob),
            ("file_upload", FileUpload),
            ("normalized_material", NormalizedMaterial),
            ("national_material", NationalMaterial),
            ("match_result", MatchResult),
            ("material_mapping", MaterialMapping),
            ("approval", Approval),
            ("feedback_event", FeedbackEvent),
            ("data_quality_metrics", DataQualityMetrics),
            ("procurement_record", ProcurementRecord),
            ("audit_log", AuditLog),
            ("notification", Notification),
        ]
        for name, model in tables:
            count = session.query(model).count()
            print(f"  {name:30s} {count:>6} rows")

        print("\n[OK] Full demo data seeded successfully!")

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
