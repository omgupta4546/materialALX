import pytest
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.base import NationalMaterial
from app.repositories.base import NationalMaterialRepo

def test_national_material_creation(db_session: Session):
    repo = NationalMaterialRepo(db_session)
    code = f"NM-{uuid.uuid4().hex[:8]}"
    
    nm = repo.create(
        national_material_id=str(uuid.uuid4()),
        national_material_code=code,
        canonical_description="Test National Material",
        status="PROVISIONAL"
    )
    
    assert nm.national_material_code == code
    assert nm.status == "PROVISIONAL"
    assert nm.version == 1

def test_national_material_unique_code(db_session: Session):
    repo = NationalMaterialRepo(db_session)
    code = f"NM-{uuid.uuid4().hex[:8]}"
    
    repo.create(
        national_material_id=str(uuid.uuid4()),
        national_material_code=code,
        canonical_description="Test National Material 1"
    )
    
    with pytest.raises(IntegrityError):
        repo.create(
            national_material_id=str(uuid.uuid4()),
            national_material_code=code,
            canonical_description="Test National Material 2"
        )
        db_session.flush()
    
    db_session.rollback()

def test_national_material_invalid_status(db_session: Session):
    repo = NationalMaterialRepo(db_session)
    code = f"NM-{uuid.uuid4().hex[:8]}"
    
    # SQLAlchemy's CheckConstraint is enforced at the DB level,
    # so we need to flush to trigger the error.
    with pytest.raises(IntegrityError):
        repo.create(
            national_material_id=str(uuid.uuid4()),
            national_material_code=code,
            canonical_description="Test National Material 3",
            status="INVALID_STATUS"
        )
        db_session.flush()
        
    db_session.rollback()
