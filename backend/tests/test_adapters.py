import pytest
import os
import json
from app.adapters import CSVAdapter, MockERPAdapter, SAPAdapter

def test_csv_adapter_flow(tmp_path):
    # Create a mock CSV
    csv_file = tmp_path / "materials.csv"
    csv_file.write_text("legacy_code,description,uom\nL001,Test Material,KG\nL002,Another Material,EA\n")
    
    adapter = CSVAdapter(str(csv_file))
    
    assert adapter.health_check() is True
    
    # Test fetch_materials
    materials = adapter.fetch_materials()
    assert len(materials) == 2
    assert materials[0].legacy_code == "L001"
    assert materials[0].description == "Test Material"
    
    # Test get_material
    mat = adapter.get_material("L002")
    assert mat is not None
    assert mat.legacy_code == "L002"
    
    # Test missing material
    mat = adapter.get_material("L003")
    assert mat is None
    
    # Test mappings
    assert adapter.create_mapping("L001", "NAT001") is True
    assert adapter.update_mapping("L001", "NAT002") is True
    
    status = adapter.sync_status()
    assert status["type"] == "CSV"
    assert status["file_exists"] is True
    assert status["mappings_synced"] == 1


def test_sap_adapter_stub():
    adapter = SAPAdapter({"host": "sap.local"})
    
    assert adapter.health_check() is False
    
    with pytest.raises(NotImplementedError):
        adapter.fetch_materials()
        
    with pytest.raises(NotImplementedError):
        adapter.get_material("123")
        
    with pytest.raises(NotImplementedError):
        adapter.create_mapping("123", "NAT123")
        
    with pytest.raises(NotImplementedError):
        adapter.update_mapping("123", "NAT124")

    status = adapter.sync_status()
    assert status["type"] == "SAP"
    assert status["connected"] is False


def test_mock_erp_adapter_flow(requests_mock):
    adapter = MockERPAdapter("http://erp.local")
    
    # Mock health check
    requests_mock.get("http://erp.local/health", status_code=200)
    assert adapter.health_check() is True
    
    # Mock fetch_materials
    requests_mock.get("http://erp.local/api/materials", json={
        "items": [
            {"legacy_code": "M1", "description": "Desc 1"},
            {"legacy_code": "M2", "description": "Desc 2", "uom": "L"}
        ]
    })
    materials = adapter.fetch_materials()
    assert len(materials) == 2
    assert materials[1].uom == "L"
    
    # Mock get_material
    requests_mock.get("http://erp.local/api/materials/M1", json={"legacy_code": "M1", "description": "Desc 1"})
    mat = adapter.get_material("M1")
    assert mat is not None
    assert mat.legacy_code == "M1"
    
    # Mock get_material 404
    requests_mock.get("http://erp.local/api/materials/M3", status_code=404)
    assert adapter.get_material("M3") is None
    
    # Mock create mapping
    requests_mock.post("http://erp.local/api/mappings", status_code=201)
    assert adapter.create_mapping("M1", "NAT1") is True
    
    # Mock update mapping
    requests_mock.put("http://erp.local/api/mappings/M1", status_code=200)
    assert adapter.update_mapping("M1", "NAT2") is True
