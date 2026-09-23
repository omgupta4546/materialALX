import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.schemas.cpse import CPSECreate, CPSEUpdate
from app.services.cpse_service import CPSEService

client = TestClient(app)

def test_create_cpse(db_session: Session):
    service = CPSEService(db_session)
    cpse_code = f"TEST-{uuid.uuid4().hex[:6]}"
    cpse_in = CPSECreate(
        cpse_code=cpse_code,
        cpse_name="Test CPSE 1",
        sector="Power",
        description="A test CPSE",
        status="ACTIVE"
    )
    
    cpse = service.create_cpse(cpse_in)
    assert cpse.cpse_id is not None
    assert cpse.cpse_code == cpse_code
    assert cpse.cpse_name == "Test CPSE 1"

def test_get_cpse_by_code(db_session: Session):
    service = CPSEService(db_session)
    cpse_code = f"TEST-{uuid.uuid4().hex[:6]}"
    service.create_cpse(CPSECreate(cpse_code=cpse_code, cpse_name="Test CPSE 1", status="ACTIVE"))
    
    cpse = service.get_cpse_by_code(cpse_code)
    assert cpse is not None
    assert cpse.cpse_name == "Test CPSE 1"

def test_update_cpse(db_session: Session):
    service = CPSEService(db_session)
    cpse_code = f"TEST-{uuid.uuid4().hex[:6]}"
    cpse = service.create_cpse(CPSECreate(cpse_code=cpse_code, cpse_name="Test CPSE 1", status="ACTIVE"))
    
    update_in = CPSEUpdate(cpse_name="Updated Test CPSE")
    updated = service.update_cpse(cpse.cpse_id, update_in)
    
    assert updated.cpse_name == "Updated Test CPSE"

def test_api_list_cpses(db_session: Session):
    service = CPSEService(db_session)
    cpse_code = f"TEST-{uuid.uuid4().hex[:6]}"
    service.create_cpse(CPSECreate(cpse_code=cpse_code, cpse_name="Test CPSE 1", status="ACTIVE"))
    db_session.commit()
    
    response = client.get("/api/v1/cpses")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(c["cpse_code"] == cpse_code for c in data)

def test_api_create_duplicate(db_session: Session):
    service = CPSEService(db_session)
    cpse_code = f"TEST-{uuid.uuid4().hex[:6]}"
    service.create_cpse(CPSECreate(cpse_code=cpse_code, cpse_name="Duplicate CPSE", status="ACTIVE"))
    db_session.commit()
    
    payload = {
        "cpse_code": cpse_code,
        "cpse_name": "Duplicate CPSE",
        "status": "ACTIVE"
    }
    response = client.post("/api/v1/cpses", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]
