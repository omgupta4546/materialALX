import pytest
import datetime
import numpy as np

# We import the models directly
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../backend')))
from app.models.base import (
    CPSE, SourceMaterial, NormalizedMaterial, MaterialAttribute,
    Classification, NationalMaterial, MaterialMapping, MatchResult,
    Approval, AuditLog, ProcurementRecord, ProcessingJob
)
from app.core.db_config import db_config

# Deterministic constants
MOCK_DATE = datetime.datetime(2026, 1, 1, 12, 0, 0)
MOCK_EMBEDDING = np.full(db_config.embedding_dimension, 0.1).tolist()

@pytest.fixture
def fixture_cpse():
    return CPSE(
        cpse_code="CPSE-TEST",
        cpse_name="Test Enterprise",
        sector="Energy",
        description="A deterministic test CPSE"
    )

@pytest.fixture
def fixture_classification():
    return Classification(
        code="CAT-VALVE",
        name="Valves",
        parent_code=None
    )

@pytest.fixture
def fixture_source_material():
    return SourceMaterial(
        source_id="src-1001",
        cpse_code="CPSE-TEST",
        material_code="MAT-001",
        description="GATE VALVE 6IN CL150",
        uom="EA",
        plant="PLANT-A",
        raw_json={"color": "blue"},
        created_at=MOCK_DATE
    )

@pytest.fixture
def fixture_normalized_material():
    return NormalizedMaterial(
        normalized_id="norm-1001",
        source_id="src-1001",
        normalized_description="Valve, Gate, 6 inch, Class 150",
        category_code="CAT-VALVE",
        manufacturer="Acme Corp",
        manufacturer_part_number="GV-6-150",
        attributes={"size": "6in", "class": "150"},
        embedding=MOCK_EMBEDDING,
        updated_at=MOCK_DATE
    )

@pytest.fixture
def fixture_material_attribute():
    return MaterialAttribute(
        id=1,
        normalized_id="norm-1001",
        attribute_name="Pressure Class",
        attribute_value="150"
    )

@pytest.fixture
def fixture_national_material():
    return NationalMaterial(
        national_code="NAT-9999",
        primary_description="Standard Gate Valve 6in",
        category_code="CAT-VALVE",
        uom="EA",
        attributes={"type": "gate"},
        status="APPROVED",
        created_at=MOCK_DATE,
        updated_at=MOCK_DATE
    )

@pytest.fixture
def fixture_material_mapping():
    return MaterialMapping(
        id=1,
        source_id="src-1001",
        national_code="NAT-9999",
        mapping_type="EXACT",
        confidence_score=0.99,
        approved_by="admin-user",
        approved_at=MOCK_DATE
    )

@pytest.fixture
def fixture_match_result():
    return MatchResult(
        id="match-1001",
        source_id="src-1001",
        candidate_national_code="NAT-9999",
        score=0.98,
        ai_reasoning="High textual overlap and semantic similarity."
    )

@pytest.fixture
def fixture_approval():
    return Approval(
        id="appr-1001",
        target_id="NAT-9999",
        target_type="NationalMaterial",
        approver_id="admin-user",
        status="APPROVED",
        timestamp=MOCK_DATE
    )

@pytest.fixture
def fixture_audit_log():
    return AuditLog(
        id=1,
        action="CREATE_NATIONAL_MATERIAL",
        user_id="admin-user",
        target="NAT-9999",
        details={"reason": "Initial creation"},
        timestamp=MOCK_DATE
    )

@pytest.fixture
def fixture_procurement_record():
    return ProcurementRecord(
        procurement_id="proc-1001",
        source_id="src-1001",
        supplier="Global Supply Co",
        quantity=10.0,
        unit_price=150.0,
        total_spend=1500.0,
        procurement_date=MOCK_DATE,
        plant="PLANT-A"
    )

@pytest.fixture
def fixture_processing_job():
    return ProcessingJob(
        job_id="job-1001",
        status="COMPLETED",
        records_processed=1000,
        started_at=MOCK_DATE,
        completed_at=MOCK_DATE
    )
