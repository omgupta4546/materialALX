import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.models.base import (
    CPSE, SourceMaterial, NationalMaterial, MaterialMapping,
    ProcurementRecord, MatchResult, DataQualityMetrics, AuditLog, ProcessingJob
)

client = TestClient(app)

@pytest.fixture
def mock_export_data(db_session):
    import uuid
    
    cpse = CPSE(cpse_id="cpse-1", cpse_code="TEST_CPSE", cpse_name="Test", sector="POWER")
    db_session.add(cpse)
    
    src = SourceMaterial(source_material_id="src-1", cpse_id="cpse-1", legacy_material_code="L1", raw_description="Raw")
    db_session.add(src)
    
    nat = NationalMaterial(national_material_id="nat-1", national_material_code="N1", canonical_description="Canonical", status="ACTIVE")
    db_session.add(nat)
    
    mapping = MaterialMapping(mapping_id="map-1", source_material_id="src-1", national_material_id="nat-1", status="APPROVED")
    db_session.add(mapping)
    
    proc = ProcurementRecord(procurement_id="proc-1", source_material_id="src-1", supplier="Supplier A", quantity=100.0, total_spend=500000.0)
    db_session.add(proc)
    
    match = MatchResult(match_id="m-1", material_a_id="nat-1", match_type="NEAR_DUPLICATE", risk_level="LOW", created_at=datetime.utcnow())
    db_session.add(match)
    
    job = ProcessingJob(job_id=str(uuid.uuid4()), status="COMPLETED", records_processed=10, started_at=datetime.utcnow(), completed_at=datetime.utcnow())
    db_session.add(job)
    
    audit = AuditLog(audit_id="a-1", actor_id="user1", action="TEST", entity_type="TEST", entity_id="TEST", timestamp=datetime.utcnow())
    db_session.add(audit)
    
    dq = DataQualityMetrics(metric_id="dq-1", material_id="nat-1", completeness_score=100.0, uniqueness_score=100.0, validity_score=100.0, consistency_score=100.0)
    db_session.add(dq)
    
    db_session.commit()
    return db_session


def test_procurement_intelligence_api(mock_export_data):
    response = client.get("/api/v1/analytics/procurement/intelligence", headers={"X-User-Roles": "ADMIN"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    item = data[0]
    assert item["national_material_code"] == "N1"
    assert item["cpse_count"] == 1
    assert item["historical_spend"] == 500000.0
    assert item["opportunity_priority"] == "MEDIUM"


def test_export_cpse_mapping_csv(mock_export_data):
    response = client.get("/api/v1/exports/cpse-mapping?format=csv", headers={"X-User-Roles": "ADMIN"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    content = response.content.decode("utf-8")
    assert "map-1" in content
    assert "APPROVED" in content


def test_export_material_master_xlsx(mock_export_data):
    response = client.get("/api/v1/exports/material-master?format=xlsx", headers={"X-User-Roles": "ADMIN"})
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    assert response.content is not None
    assert len(response.content) > 0


def test_export_invalid_report_type():
    response = client.get("/api/v1/exports/fake-report?format=csv", headers={"X-User-Roles": "ADMIN"})
    assert response.status_code == 404
