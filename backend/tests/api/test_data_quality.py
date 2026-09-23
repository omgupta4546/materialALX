import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_data_quality_overview():
    # In a real test, we would hit the DB. Since we are testing endpoints structure, we expect 401 Unauthorized without auth
    # For now we just verify the route exists. If auth is disabled for tests, we should get 200.
    response = client.get("/api/v1/data-quality/overview")
    # Our dependencies require RBAC, so it should return 401 Unauthorized or 403 unless we mock
    assert response.status_code in [200, 401, 403]
    
def test_get_data_quality_materials():
    response = client.get("/api/v1/data-quality/materials?flag=missing_pressure_class")
    assert response.status_code in [200, 401, 403]
    
def test_get_data_quality_categories():
    response = client.get("/api/v1/data-quality/categories")
    assert response.status_code in [200, 401, 403]

from app.models.base import NormalizedMaterial
from app.ai.modules.quality_engine import DataQualityEngine

def test_engine_missing_manufacturer():
    material = NormalizedMaterial(
        normalized_material_id="mat-1",
        category_code="BEARING",
        normalized_description="Ball bearing 6204",
        canonical_uom="EA",
        normalization_method="deterministic"
    )
    
    engine = DataQualityEngine()
    indicator = engine.evaluate_material(material, has_classification=False, attributes={})
    
    assert "missing_manufacturer" in indicator.flags
    assert "missing_classification" in indicator.flags
    assert indicator.attribute_coverage == 0.0
    
def test_engine_missing_pressure_class():
    material = NormalizedMaterial(
        normalized_material_id="mat-2",
        category_code="VALVE",
        normalized_manufacturer="Crane",
        canonical_uom="EA",
        normalization_method="deterministic"
    )
    
    engine = DataQualityEngine()
    indicator = engine.evaluate_material(material, has_classification=True, attributes={"size": "2 inch"})
    
    assert "missing_pressure_class" in indicator.flags
    assert indicator.attribute_coverage == 0.5
