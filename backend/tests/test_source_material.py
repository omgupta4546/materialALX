import pytest
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi.exceptions import HTTPException

from app.schemas.source_material import SourceMaterialCreate
from app.services.source_material_service import SourceMaterialService
from app.models.base import SourceMaterial

def test_create_source_material(db_session: Session):
    # Setup test CPSE (mocked/dependent on CPSE table, but SQLite FKs might not be enforced unless PRAGMA foreign_keys=ON is explicitly set, which we didn't enable, so we can just use a string)
    service = SourceMaterialService(db_session)
    data = SourceMaterialCreate(
        cpse_id="test_cpse_123",
        legacy_material_code="MAT-001",
        raw_description="Test Material",
        manufacturer="Acme Corp"
    )
    record = service.create_material(data)
    
    assert record.source_material_id is not None
    assert record.cpse_id == "test_cpse_123"
    assert record.legacy_material_code == "MAT-001"
    assert record.raw_description == "Test Material"
    assert record.manufacturer == "Acme Corp"
    assert record.created_at is not None

def test_source_material_immutability(db_session: Session):
    service = SourceMaterialService(db_session)
    data = SourceMaterialCreate(
        cpse_id="test_cpse_123",
        legacy_material_code="MAT-002",
        raw_description="Immutable Material"
    )
    record = service.create_material(data)
    
    # Attempt to modify the record and commit
    with pytest.raises(ValueError, match="SourceMaterial records are strictly immutable"):
        record.raw_description = "Hacked Description"
        db_session.add(record)
        db_session.commit()
    
    # Rollback to clean state
    db_session.rollback()

def test_duplicate_legacy_code(db_session: Session):
    service = SourceMaterialService(db_session)
    data = SourceMaterialCreate(
        cpse_id="test_cpse_dup",
        legacy_material_code="DUP-001",
        raw_description="Dup 1"
    )
    service.create_material(data)
    
    with pytest.raises(HTTPException) as exc:
        service.create_material(data)
    
    assert exc.value.status_code == 400
    assert "already exists" in exc.value.detail
