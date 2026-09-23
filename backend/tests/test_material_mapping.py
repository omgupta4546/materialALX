import pytest
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.base import SourceMaterial, NationalMaterial, MaterialMapping
from app.repositories.base import SourceMaterialRepo, NationalMaterialRepo, MaterialMappingRepo

def test_material_mapping_creation_and_conflicts(db_session: Session):
    sm_repo = SourceMaterialRepo(db_session)
    nm_repo = NationalMaterialRepo(db_session)
    mapping_repo = MaterialMappingRepo(db_session)

    # 1. Setup Source Material
    source_material_id = str(uuid.uuid4())
    sm_repo.create(
        source_material_id=source_material_id,
        cpse_id="test_cpse",
        legacy_material_code="TEST-MM-001",
        raw_description="Test MM Source"
    )

    # 2. Setup National Material
    national_material_id = str(uuid.uuid4())
    nm_repo.create(
        national_material_id=national_material_id,
        national_material_code=f"NM-{uuid.uuid4().hex[:8]}",
        canonical_description="Test MM National"
    )

    # 3. Create a PENDING mapping
    mapping1 = mapping_repo.create(
        mapping_id=str(uuid.uuid4()),
        source_material_id=source_material_id,
        national_material_id=national_material_id,
        mapping_type="EXACT_DUPLICATE",
        confidence=0.99,
        status="PENDING"
    )
    
    assert mapping1.status == "PENDING"

    # 4. Attempt to create another mapping for the same source, should conflict
    with pytest.raises(ValueError, match="Conflicting mapping exists"):
        mapping_repo.create(
            mapping_id=str(uuid.uuid4()),
            source_material_id=source_material_id,
            national_material_id=national_material_id,
            mapping_type="NEAR_DUPLICATE",
            confidence=0.85,
            status="APPROVED"
        )
