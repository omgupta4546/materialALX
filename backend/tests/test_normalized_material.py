import pytest
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from app.models.base import SourceMaterial, NormalizedMaterial, UOMMaster
from app.repositories.base import SourceMaterialRepo, NormalizedMaterialRepo

def test_normalized_material_versioning(db_session: Session):
    # Setup test data
    sm_repo = SourceMaterialRepo(db_session)
    nm_repo = NormalizedMaterialRepo(db_session)
    
    source_material_id = str(uuid.uuid4())
    sm_repo.create(
        source_material_id=source_material_id,
        cpse_id="test_cpse",
        legacy_material_code="TEST-NM-001",
        raw_description="Test Source"
    )
    
    # Create v1 of normalized material
    nm_v1 = nm_repo.create(
        normalized_material_id=str(uuid.uuid4()),
        source_material_id=source_material_id,
        normalized_description="Normalized Description v1",
        normalization_version="v1.0",
        normalization_method="AI",
        confidence=0.85
    )
    
    # Create v2 of normalized material for the SAME source material
    nm_v2 = nm_repo.create(
        normalized_material_id=str(uuid.uuid4()),
        source_material_id=source_material_id,
        normalized_description="Normalized Description v2",
        normalization_version="v2.0",
        normalization_method="AI",
        confidence=0.95
    )
    
    # Verify both exist and are returned properly
    versions = nm_repo.by_source(source_material_id)
    assert len(versions) == 2
    
    # Verify latest
    latest = nm_repo.get_latest_by_source(source_material_id)
    assert latest.normalization_version == "v2.0"
    
    # Verify specific version
    v1_fetched = nm_repo.by_source_and_version(source_material_id, "v1.0")
    assert v1_fetched.normalized_description == "Normalized Description v1"

def test_normalized_material_duplicate_version(db_session: Session):
    nm_repo = NormalizedMaterialRepo(db_session)
    source_material_id = str(uuid.uuid4())
    
    # Mock source creation
    sm_repo = SourceMaterialRepo(db_session)
    sm_repo.create(
        source_material_id=source_material_id,
        cpse_id="test_cpse_dup",
        legacy_material_code="TEST-NM-002",
        raw_description="Test Source 2"
    )

    # Create v1
    nm_repo.create(
        normalized_material_id=str(uuid.uuid4()),
        source_material_id=source_material_id,
        normalization_version="v1.0"
    )
    
    # Attempting to create v1 again should fail
    with pytest.raises(IntegrityError):
        nm_repo.create(
            normalized_material_id=str(uuid.uuid4()),
            source_material_id=source_material_id,
            normalization_version="v1.0"
        )
        db_session.flush()

    db_session.rollback()
