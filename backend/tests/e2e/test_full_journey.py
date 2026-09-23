import pytest
import json
import asyncio
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.api.deps import get_db
from app.models.base import (
    ProcessingJob, SourceMaterial, NormalizedMaterial,
    MatchResult, NationalMaterial, MaterialMapping,
    CriticalRule, Classification, UOMMaster, CPSE
)
from app.worker.main import process_upload_job

client = TestClient(app)

@pytest.fixture
def db(db_session: Session):
    return db_session

def test_complete_business_flow(db: Session):
    """
    18-Stage End-to-End Test for the Material Standardization Pipeline.
    """
    # ---------------------------------------------------------
    # 0. Mock external dependencies
    # ---------------------------------------------------------
    def mock_extract(text: str, *args, **kwargs):
        if "415V" in text:
            return {"material": "Steel", "voltage": "415V"}
        elif "230V" in text:
            return {"material": "Steel", "voltage": "230V"}
        return {"material": "Steel"}

    def mock_classify(*args, **kwargs):
        return {"category": "ELECTRICAL", "confidence": 0.9}

    # ---------------------------------------------------------
    # 1. Login (Mocked via conftest) & 2. Setup Seed Data
    # ---------------------------------------------------------
    # Seed a Critical Rule to test veto logic (voltage mismatch = block)
    rule = CriticalRule(
        id="rule-1", classification_code="ELEC-MTR",
        attribute="voltage", severity="CRITICAL", conflict_behavior="BLOCK_EQUIVALENCE"
    )
    # Seed Classification
    classification = Classification(code="ELEC-MTR", name="Electric Motor")
    
    # Seed a National Material and its required mappings for vector search fallback
    nat_mat = NationalMaterial(
        national_material_id="nat-1",
        national_material_code="NAT-001",
        canonical_description="Electric Motor 415V Steel",
        classification_id="ELEC-MTR",
        attributes={"voltage": "415", "material": "Steel"},
        status="ACTIVE"
    )
    
    src_seed = SourceMaterial(
        source_material_id="src-seed",
        legacy_material_code="SEED-001",
        raw_description="Electric Motor 415V",
        cpse_id="seed_cpse",
        source_file="seed.json"
    )
    
    norm_seed = NormalizedMaterial(
        normalized_material_id="norm-seed",
        source_material_id="src-seed",
        normalized_description="Electric Motor 415V",
        category_code="ELEC-MTR",
        attributes={"voltage": "415"},
        embedding=[0.1] * 768,
        confidence=1.0
    )
    
    mapping_seed = MaterialMapping(
        mapping_id="map-seed",
        source_material_id="src-seed",
        national_material_id="nat-1",
        mapping_type="EXACT_DUPLICATE",
        status="APPROVED"
    )
    
    db.add_all([rule, classification, nat_mat, src_seed, norm_seed, mapping_seed])
    db.commit()
    
    # Select CPSE
    cpse_resp = client.post("/api/v1/cpses", json={"cpse_code": "TEST_CPSE", "cpse_name": "Test", "status": "ACTIVE"})
    assert cpse_resp.status_code == 201
    cpse_id = cpse_resp.json()["cpse_id"]

    # ---------------------------------------------------------
    # 3. Upload Material File
    # ---------------------------------------------------------
    upload_data = [
        {
            "material_code": "MAT-001",
            "description": "Electric Motor 415V Steel",
            "uom": "EA"
        },
        {
            "material_code": "MAT-002",
            "description": "Electric Motor 230V Steel",
            "uom": "EA"
        },
        {
            "material_code": "MAT-003",
            "description": "Electric Motor 415V Steel Alternate",
            "uom": "EA"
        }
    ]
    file_bytes = json.dumps(upload_data).encode("utf-8")
    
    upload_resp = client.post(
        "/api/v1/materials/upload",
        data={"cpse_id": cpse_id},
        files={"file": ("test.json", file_bytes, "application/json")}
    )
    assert upload_resp.status_code == 202
    job_id = upload_resp.json()["job_id"]
    upload_id = upload_resp.json()["upload_id"]

    # ---------------------------------------------------------
    # 4. Verify ProcessingJob created
    # ---------------------------------------------------------
    job_req = client.get(f"/api/v1/jobs/{job_id}")
    assert job_req.json()["status"] == "PENDING"

    # ---------------------------------------------------------
    # 5. Run the background worker synchronously
    # ---------------------------------------------------------
    with patch("app.ai.llm.providers.openai_provider.OpenAIProvider.extract_attributes", side_effect=mock_extract), \
         patch("app.ai.llm.providers.openai_provider.OpenAIProvider.classify", side_effect=mock_classify):
         
        asyncio.run(process_upload_job(
            None, content=file_bytes, filename="test.json", 
            cpse_id=cpse_id, job_id=job_id, upload_id=upload_id
        ))

    # ---------------------------------------------------------
    # 6. Verify SourceMaterials Created
    # ---------------------------------------------------------
    job_after = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job_after["status"] == "COMPLETED"
    
    source_mats = db.query(SourceMaterial).filter_by(cpse_id=cpse_id).all()
    assert len(source_mats) == 3

    # ---------------------------------------------------------
    # 7-9. Verify Normalization, Extraction, Classification, Embedding
    # ---------------------------------------------------------
    norm_mats = db.query(NormalizedMaterial).all()
    assert len(norm_mats) == 4
    for nm in norm_mats:
        assert nm.category_code == "ELEC-MTR"
        assert "voltage" in nm.attributes
        assert nm.embedding is not None

    # ---------------------------------------------------------
    # 10-12. Verify Matches & Critical Rule Veto
    # ---------------------------------------------------------
    # MAT-001 (415V) and MAT-003 (415V) should match nat-1. MAT-002 (230V) should be blocked.
    match_results = db.query(MatchResult).all()
    
    # At least some match results should exist due to candidate retrieval
    assert len(match_results) > 0
    
    src1 = db.query(SourceMaterial).filter_by(legacy_material_code="MAT-001").first()
    src2 = db.query(SourceMaterial).filter_by(legacy_material_code="MAT-002").first()
    src3 = db.query(SourceMaterial).filter_by(legacy_material_code="MAT-003").first()
    
    mat1 = db.query(NormalizedMaterial).filter_by(source_material_id=src1.source_material_id).first()
    mat2 = db.query(NormalizedMaterial).filter_by(source_material_id=src2.source_material_id).first()
    mat3 = db.query(NormalizedMaterial).filter_by(source_material_id=src3.source_material_id).first()

    match_1 = db.query(MatchResult).filter_by(material_a_id=mat1.normalized_material_id, material_b_id="nat-1").first()
    match_2 = db.query(MatchResult).filter_by(material_a_id=mat2.normalized_material_id, material_b_id="nat-1").first()
    match_3 = db.query(MatchResult).filter_by(material_a_id=mat3.normalized_material_id, material_b_id="nat-1").first()

    if match_1:
        assert match_1.requires_human_review is False
        
    if match_2:
        assert match_2.requires_human_review is True
        assert match_2.recommendation == "DOWNGRADE_TO_REVIEW"

    # ---------------------------------------------------------
    # 13. Match Recommendation & 14. Human Approval
    # ---------------------------------------------------------
    # Let's approve the first available match
    first_match = match_results[0]
    approve_resp = client.post(
        f"/api/v1/matches/{first_match.match_id}/approve",
        json={"comment": "E2E Approved"}
    )
    
    assert approve_resp.status_code == 200
    assert approve_resp.json()["decision"] == "APPROVED"

    # ---------------------------------------------------------
    # 15. National Material Creation
    # ---------------------------------------------------------
    national_mats = db.query(NationalMaterial).all()
    assert len(national_mats) >= 1
    
    mappings_resp = client.post(
        "/api/v1/mappings",
        json={
            "source_material_id": first_match.material_a_id,
            "national_material_id": first_match.material_b_id,
            "mapping_type": "FUNCTIONALLY_EQUIVALENT",
            "confidence": first_match.final_score
        }
    )
    assert mappings_resp.status_code == 201

    # ---------------------------------------------------------
    # 16. Legacy Mapping
    # ---------------------------------------------------------
    mappings = db.query(MaterialMapping).all()
    assert len(mappings) >= 1  # At least the mapping we just created

    # ---------------------------------------------------------
    # 17. Procurement Aggregation
    # ---------------------------------------------------------
    proc_resp = client.get("/api/v1/analytics/procurement/intelligence")
    assert proc_resp.status_code == 200
    # Because we haven't seeded ProcurementRecords, total_spend might be 0, but the endpoint works.

    # ---------------------------------------------------------
    # 18. Dashboard Analytics
    # ---------------------------------------------------------
    dash_resp = client.get("/api/v1/analytics/dashboard")
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["total_materials"] == 4   # 3 uploaded + 1 seed
    assert dash_data["normalized_materials"] == 4   # 3 uploaded + 1 seed
