"""
tests/test_analytics_endpoints.py

Tests for the 11 dynamic analytics endpoints.
"""
import pytest
from datetime import datetime, date
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def test_data(db_session):
    from app.models.base import CPSE, SourceMaterial, NormalizedMaterial, MatchResult, DataQualityMetrics, ProcessingJob, FileUpload, MaterialMapping
    import uuid

    # Create CPSE
    cpse = CPSE(cpse_id="cpse-1", cpse_code="TEST_CPSE", cpse_name="Test CPSE", sector="POWER")
    db_session.add(cpse)
    
    # Create Source Material
    src1 = SourceMaterial(source_material_id="src-1", cpse_id="cpse-1", legacy_material_code="M1", raw_description="Test")
    src2 = SourceMaterial(source_material_id="src-2", cpse_id="cpse-1", legacy_material_code="M2", raw_description="Test 2")
    db_session.add_all([src1, src2])

    # Create Normalized Material
    norm1 = NormalizedMaterial(normalized_material_id="norm-1", source_material_id="src-1", category_code="CAT1", raw_description="Test")
    db_session.add(norm1)

    # Create DataQualityMetrics
    dq = DataQualityMetrics(material_id="norm-1", completeness_score=100.0, uniqueness_score=90.0, validity_score=80.0, consistency_score=70.0)
    db_session.add(dq)

    # Create MatchResult
    mr1 = MatchResult(match_id="m-1", material_a_id="norm-1", match_type="NEAR_DUPLICATE", risk_level="LOW", created_at=datetime.utcnow())
    mr2 = MatchResult(match_id="m-2", material_a_id="norm-1", match_type="REQUIRES_ENGINEERING_REVIEW", risk_level="HIGH", created_at=datetime.utcnow())
    db_session.add_all([mr1, mr2])

    # Create ProcessingJob
    job = ProcessingJob(job_id=str(uuid.uuid4()), status="COMPLETED", records_processed=10, started_at=datetime.utcnow(), completed_at=datetime.utcnow())
    db_session.add(job)

    db_session.commit()
    return cpse


def test_get_overview(db_session, test_data):
    res = client.get("/api/v1/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_source_materials" in data
    assert data["total_source_materials"] >= 2
    assert "total_matches" in data
    assert data["total_matches"] >= 2


def test_get_materials_by_cpse(db_session, test_data):
    res = client.get("/api/v1/analytics/materials-by-cpse")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(item["cpse"] == "TEST_CPSE" for item in data)


def test_get_upload_categories(db_session, test_data):
    res = client.get("/api/v1/analytics/upload-categories")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(item["status"] == "COMPLETED" for item in data)


def test_get_confidence_distribution(db_session, test_data):
    res = client.get("/api/v1/analytics/confidence-distribution")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_get_pending_approvals(db_session, test_data):
    res = client.get("/api/v1/analytics/pending-approvals")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_get_redundant_groups(db_session, test_data):
    res = client.get("/api/v1/analytics/redundant-material-groups")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_get_procurement_opportunities(db_session, test_data):
    res = client.get("/api/v1/analytics/procurement-opportunities")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_get_classification_coverage(db_session, test_data):
    res = client.get("/api/v1/analytics/classification-coverage")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(item["category"] == "CAT1" for item in data)


def test_get_data_quality(db_session, test_data):
    res = client.get("/api/v1/analytics/data-quality")
    assert res.status_code == 200
    data = res.json()
    assert "avg_completeness" in data


def test_get_processing_health(db_session, test_data):
    res = client.get("/api/v1/analytics/processing-health")
    assert res.status_code == 200
    data = res.json()
    assert "total_jobs" in data


def test_get_risk_distribution(db_session, test_data):
    res = client.get("/api/v1/analytics/risk-distribution")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    risk_levels = [item["risk_level"] for item in data]
    assert "High Risk" in risk_levels or "Medium Risk" in risk_levels or "Low Risk" in risk_levels

def test_filtering_params(db_session, test_data):
    # Test filters
    res = client.get("/api/v1/analytics/overview?sector=POWER&cpse_code=TEST_CPSE&category_code=CAT1")
    assert res.status_code == 200
    data = res.json()
    assert data["total_source_materials"] >= 1
