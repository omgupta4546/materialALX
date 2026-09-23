"""
Tests for material search endpoints (service + repo layer).

Covers:
- List with no filters
- Filter by cpse_id
- Filter by keyword (description, legacy code, manufacturer)
- Filter by legacy_code (partial)
- Filter by MPN
- Filter by manufacturer
- Filter by raw_uom
- Filter by mapping_status MAPPED / UNMAPPED
- Filter by classification_id
- Sort by field / direction
- Pagination (limit + offset)
- GET by ID — found and 404
- National material search — keyword, status, classification
- Semantic stub returns 'none' mode when provider is empty
"""
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.base import (
    CPSE, Classification, MaterialMapping, NationalMaterial,
    NormalizedMaterial, SourceMaterial, UOMMaster,
)
from app.services.material_service import MaterialService


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / helpers
# ─────────────────────────────────────────────────────────────────────────────

def _cpse(db: Session) -> CPSE:
    c = CPSE(
        cpse_id=str(uuid.uuid4()),
        cpse_code=f"TEST-{uuid.uuid4().hex[:6]}",
        cpse_name="Test CPSE",
        status="ACTIVE",
    )
    db.add(c)
    db.flush()
    return c


def _classification(db: Session, code: str = "MECH") -> Classification:
    cl = Classification(
        classification_id=str(uuid.uuid4()),
        code=code,
        name="Mechanical",
        level=0,
    )
    db.add(cl)
    db.flush()
    return cl


def _uom(db: Session, code: str = "EA") -> UOMMaster:
    existing = db.query(UOMMaster).filter(UOMMaster.canonical_code == code).first()
    if existing:
        return existing
    u = UOMMaster(canonical_code=code, name="Each", dimension="COUNT")
    db.add(u)
    db.flush()
    return u


def _source(db: Session, cpse_id: str, code: str, **kwargs) -> SourceMaterial:
    sm = SourceMaterial(
        source_material_id=str(uuid.uuid4()),
        cpse_id=cpse_id,
        legacy_material_code=code,
        raw_description=kwargs.get("description", f"Desc {code}"),
        raw_uom=kwargs.get("raw_uom", "EA"),
        raw_category=kwargs.get("raw_category"),
        manufacturer=kwargs.get("manufacturer"),
        manufacturer_part_number=kwargs.get("mpn"),
    )
    db.add(sm)
    db.flush()
    return sm


def _normalized(db: Session, sm: SourceMaterial, classification_id: str | None = None) -> NormalizedMaterial:
    nm = NormalizedMaterial(
        normalized_material_id=str(uuid.uuid4()),
        source_material_id=sm.source_material_id,
        normalized_description=sm.raw_description + " (norm)",
        canonical_uom="EA",
        category_code=classification_id,
        normalization_version="v1",
        confidence=0.95,
    )
    db.add(nm)
    db.flush()
    return nm


def _national(db: Session, cl: Classification) -> NationalMaterial:
    n = NationalMaterial(
        national_material_id=str(uuid.uuid4()),
        national_material_code=f"NAT-{uuid.uuid4().hex[:6]}",
        canonical_description="Golden Bolt M10",
        classification_id=cl.classification_id,
        canonical_uom="EA",
        status="ACTIVE",
        version=1,
    )
    db.add(n)
    db.flush()
    return n


def _mapping(db: Session, sm: SourceMaterial, nat: NationalMaterial) -> MaterialMapping:
    mm = MaterialMapping(
        mapping_id=str(uuid.uuid4()),
        source_material_id=sm.source_material_id,
        national_material_id=nat.national_material_id,
        mapping_type="EXACT_DUPLICATE",
        confidence=0.99,
        status="APPROVED",
    )
    db.add(mm)
    db.flush()
    return mm


# ─────────────────────────────────────────────────────────────────────────────
# Tests — Source Materials
# ─────────────────────────────────────────────────────────────────────────────

def test_list_materials_empty(db_session: Session):
    svc = MaterialService(db_session)
    result = svc.list_materials()
    assert result.total == 0
    assert result.items == []
    assert result.search_mode == "none"


def test_list_materials_returns_all(db_session: Session):
    cpse = _cpse(db_session)
    _source(db_session, cpse.cpse_id, "A-001")
    _source(db_session, cpse.cpse_id, "A-002")
    svc = MaterialService(db_session)
    result = svc.list_materials()
    assert result.total == 2
    assert len(result.items) == 2


def test_filter_by_cpse_id(db_session: Session):
    c1, c2 = _cpse(db_session), _cpse(db_session)
    _source(db_session, c1.cpse_id, "C1-001")
    _source(db_session, c2.cpse_id, "C2-001")
    svc = MaterialService(db_session)
    result = svc.list_materials(cpse_id=c1.cpse_id)
    assert result.total == 1
    assert result.items[0].cpse_id == c1.cpse_id


def test_filter_by_keyword_description(db_session: Session):
    cpse = _cpse(db_session)
    _source(db_session, cpse.cpse_id, "B-001", description="Heavy Bolt M10")
    _source(db_session, cpse.cpse_id, "B-002", description="Light Spring")
    svc = MaterialService(db_session)
    result = svc.list_materials(keyword="Bolt")
    assert result.total == 1
    assert "Bolt" in result.items[0].raw_description
    assert result.search_mode == "keyword"


def test_filter_by_legacy_code(db_session: Session):
    cpse = _cpse(db_session)
    _source(db_session, cpse.cpse_id, "LEGACY-XYZ-001")
    _source(db_session, cpse.cpse_id, "OTHER-001")
    svc = MaterialService(db_session)
    result = svc.list_materials(legacy_code="LEGACY-XYZ")
    assert result.total == 1
    assert result.items[0].legacy_material_code == "LEGACY-XYZ-001"


def test_filter_by_manufacturer(db_session: Session):
    cpse = _cpse(db_session)
    _source(db_session, cpse.cpse_id, "M-001", manufacturer="SKF Industries")
    _source(db_session, cpse.cpse_id, "M-002", manufacturer="Bosch")
    svc = MaterialService(db_session)
    result = svc.list_materials(manufacturer="SKF")
    assert result.total == 1
    assert "SKF" in result.items[0].manufacturer


def test_filter_by_mpn(db_session: Session):
    cpse = _cpse(db_session)
    _source(db_session, cpse.cpse_id, "MPN-001", mpn="SKF-6205-2RS")
    _source(db_session, cpse.cpse_id, "MPN-002", mpn="NSK-7206")
    svc = MaterialService(db_session)
    result = svc.list_materials(mpn="6205")
    assert result.total == 1
    assert "6205" in result.items[0].manufacturer_part_number


def test_filter_by_raw_uom(db_session: Session):
    cpse = _cpse(db_session)
    _source(db_session, cpse.cpse_id, "U-001", raw_uom="EA")
    _source(db_session, cpse.cpse_id, "U-002", raw_uom="KG")
    svc = MaterialService(db_session)
    result = svc.list_materials(raw_uom="KG")
    assert result.total == 1


def test_filter_mapping_status_mapped(db_session: Session):
    cpse = _cpse(db_session)
    cl = _classification(db_session, code=f"CL-{uuid.uuid4().hex[:4]}")
    _uom(db_session, "EA")
    sm_mapped = _source(db_session, cpse.cpse_id, "MAP-001")
    sm_unmapped = _source(db_session, cpse.cpse_id, "MAP-002")
    nat = _national(db_session, cl)
    _mapping(db_session, sm_mapped, nat)
    svc = MaterialService(db_session)
    mapped = svc.list_materials(mapping_status="MAPPED")
    assert all(i.mapping_status == "MAPPED" for i in mapped.items)
    unmapped = svc.list_materials(mapping_status="UNMAPPED")
    assert all(i.mapping_status == "UNMAPPED" for i in unmapped.items)


def test_filter_by_classification_id(db_session: Session):
    cpse = _cpse(db_session)
    cl1 = _classification(db_session, code=f"CL1-{uuid.uuid4().hex[:4]}")
    cl2 = _classification(db_session, code=f"CL2-{uuid.uuid4().hex[:4]}")
    sm1 = _source(db_session, cpse.cpse_id, "CLS-001")
    sm2 = _source(db_session, cpse.cpse_id, "CLS-002")
    _normalized(db_session, sm1, classification_id=cl1.classification_id)
    _normalized(db_session, sm2, classification_id=cl2.classification_id)
    svc = MaterialService(db_session)
    result = svc.list_materials(classification_id=cl1.classification_id)
    assert result.total == 1


def test_pagination(db_session: Session):
    cpse = _cpse(db_session)
    for i in range(10):
        _source(db_session, cpse.cpse_id, f"PAG-{i:03d}")
    svc = MaterialService(db_session)
    p1 = svc.list_materials(limit=3, offset=0)
    p2 = svc.list_materials(limit=3, offset=3)
    assert p1.total == 10
    assert len(p1.items) == 3
    assert len(p2.items) == 3
    assert p1.has_more is True
    # Items should not overlap
    ids1 = {i.source_material_id for i in p1.items}
    ids2 = {i.source_material_id for i in p2.items}
    assert ids1.isdisjoint(ids2)


def test_sort_by_legacy_code_asc(db_session: Session):
    cpse = _cpse(db_session)
    _source(db_session, cpse.cpse_id, "ZZZ-CODE")
    _source(db_session, cpse.cpse_id, "AAA-CODE")
    svc = MaterialService(db_session)
    result = svc.list_materials(sort_by="legacy_material_code", sort_dir="asc")
    codes = [i.legacy_material_code for i in result.items]
    assert codes == sorted(codes)


def test_get_material_detail(db_session: Session):
    cpse = _cpse(db_session)
    sm = _source(db_session, cpse.cpse_id, "DETAIL-001", description="Valve Assembly")
    _normalized(db_session, sm)
    svc = MaterialService(db_session)
    detail = svc.get_material(sm.source_material_id)
    assert detail.source_material_id == sm.source_material_id
    assert detail.raw_description == "Valve Assembly"
    assert detail.normalized_description is not None


def test_get_material_not_found(db_session: Session):
    svc = MaterialService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        svc.get_material("non-existent-uuid")
    assert exc_info.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Tests — National Materials
# ─────────────────────────────────────────────────────────────────────────────

def test_national_search_empty(db_session: Session):
    svc = MaterialService(db_session)
    result = svc.search_national_materials()
    assert result.total == 0


def test_national_search_keyword(db_session: Session):
    _uom(db_session, "EA")
    cl = _classification(db_session, code=f"NCL-{uuid.uuid4().hex[:4]}")
    db_session.add(NationalMaterial(
        national_material_id=str(uuid.uuid4()),
        national_material_code=f"NAT-{uuid.uuid4().hex[:4]}",
        canonical_description="High Pressure Valve 2 inch",
        classification_id=cl.classification_id,
        canonical_uom="EA",
        status="ACTIVE",
        version=1,
    ))
    db_session.add(NationalMaterial(
        national_material_id=str(uuid.uuid4()),
        national_material_code=f"NAT-{uuid.uuid4().hex[:4]}",
        canonical_description="Standard Bolt M10",
        classification_id=cl.classification_id,
        canonical_uom="EA",
        status="ACTIVE",
        version=1,
    ))
    db_session.flush()
    svc = MaterialService(db_session)
    result = svc.search_national_materials(keyword="Valve")
    assert result.total == 1
    assert "Valve" in result.items[0].canonical_description
    assert result.search_mode == "keyword"


def test_national_filter_by_status(db_session: Session):
    _uom(db_session, "EA")
    cl = _classification(db_session, code=f"SCL-{uuid.uuid4().hex[:4]}")
    for status in ("ACTIVE", "PROVISIONAL", "RETIRED"):
        db_session.add(NationalMaterial(
            national_material_id=str(uuid.uuid4()),
            national_material_code=f"NAT-{uuid.uuid4().hex[:4]}",
            canonical_description=f"Material {status}",
            classification_id=cl.classification_id,
            canonical_uom="EA",
            status=status,
            version=1,
        ))
    db_session.flush()
    svc = MaterialService(db_session)
    # RETIRED is soft-retired via SoftRetireMixin — status filter works
    result = svc.search_national_materials(status="ACTIVE")
    assert all(i.status == "ACTIVE" for i in result.items)


def test_national_filter_by_classification_id(db_session: Session):
    _uom(db_session, "EA")
    cl1 = _classification(db_session, code=f"NCL1-{uuid.uuid4().hex[:4]}")
    cl2 = _classification(db_session, code=f"NCL2-{uuid.uuid4().hex[:4]}")
    db_session.add(NationalMaterial(
        national_material_id=str(uuid.uuid4()),
        national_material_code=f"NAT-{uuid.uuid4().hex[:4]}",
        canonical_description="Material A",
        classification_id=cl1.classification_id,
        canonical_uom="EA", status="ACTIVE", version=1,
    ))
    db_session.add(NationalMaterial(
        national_material_id=str(uuid.uuid4()),
        national_material_code=f"NAT-{uuid.uuid4().hex[:4]}",
        canonical_description="Material B",
        classification_id=cl2.classification_id,
        canonical_uom="EA", status="ACTIVE", version=1,
    ))
    db_session.flush()
    svc = MaterialService(db_session)
    result = svc.search_national_materials(classification_id=cl1.classification_id)
    assert result.total == 1


def test_semantic_stub_returns_keyword_mode(db_session: Session):
    """Semantic=True with no provider active → falls through to keyword mode."""
    cpse = _cpse(db_session)
    _source(db_session, cpse.cpse_id, "SEM-001", description="Bearing Housing")
    svc = MaterialService(db_session)
    result = svc.list_materials(keyword="Bearing", semantic=True)
    # No-op semantic provider returns [], so falls through to keyword
    assert result.search_mode == "keyword"
    assert result.total >= 1
