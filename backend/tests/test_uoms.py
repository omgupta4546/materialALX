import pytest
from sqlalchemy.orm import Session
from app.services.uom_service import UOMService
from app.models.base import UOMMaster

def test_uom_normalization(db_session: Session):
    svc = UOMService(db_session)
    
    # Needs some seeded data in the test DB for aliases
    svc.create(canonical_code="EA", name="Each", dimension="COUNT", aliases=["PCS", "PIECES"], is_base_unit=True)
    
    assert svc.normalize("EA") == "EA"
    assert svc.normalize("ea") == "EA"
    assert svc.normalize("PCS") == "EA"
    assert svc.normalize("pieces") == "EA"
    assert svc.normalize("UNKNOWN") is None

def test_uom_conversion_safe(db_session: Session):
    svc = UOMService(db_session)
    
    svc.create(canonical_code="KG", name="Kilogram", dimension="MASS", aliases=[], base_multiplier=1.0, is_base_unit=True)
    svc.create(canonical_code="MT", name="Metric Ton", dimension="MASS", aliases=["TON"], base_multiplier=1000.0, is_base_unit=False)
    
    # 1 MT = 1000 KG
    assert svc.convert(1, "MT", "KG") == 1000.0
    # 500 KG = 0.5 MT
    assert svc.convert(500, "KG", "MT") == 0.5

def test_uom_conversion_incompatible_dimensions(db_session: Session):
    svc = UOMService(db_session)
    
    svc.create(canonical_code="KG", name="Kilogram", dimension="MASS", aliases=[], base_multiplier=1.0)
    svc.create(canonical_code="MM", name="Millimeter", dimension="LENGTH", aliases=[], base_multiplier=1.0)
    
    with pytest.raises(ValueError, match="Incompatible dimensions"):
        svc.convert(1, "KG", "MM")

def test_uom_create_duplicate(db_session: Session):
    svc = UOMService(db_session)
    svc.create(canonical_code="KG", name="Kilogram", dimension="MASS", aliases=[], base_multiplier=1.0)
    
    with pytest.raises(ValueError, match="already exists"):
        svc.create(canonical_code="KG", name="Kilogram 2", dimension="MASS", aliases=[])
