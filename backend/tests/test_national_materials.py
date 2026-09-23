"""
Integration tests for national material CRUD and lifecycle governance.

Covers:
    - Create: auto-generates code, starts PROVISIONAL, creates audit entry
    - Create: duplicate code → 409
    - Create: auto-increments version on content updates
    - Read: GET by id, 404 on missing
    - List: keyword, classification, uom, status filters
    - Update: mutable fields, version increments, RETIRED guard
    - Lifecycle: full happy-path PROVISIONAL → UNDER_REVIEW → ACTIVE → RETIRED
    - Lifecycle: RETIRED is terminal (no further transitions)
    - Lifecycle: illegal transitions → 422
    - Retire with superseded_by → SUPERSEDED status
    - Audit log created for every mutation
    - Breadcrumb populated from classification hierarchy
"""
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.base import AuditLog, Classification, NationalMaterial, UOMMaster
from app.schemas.national_material import (
    NationalMaterialCreate,
    NationalMaterialUpdate,
    RetireRequest,
    StatusTransitionRequest,
)
from app.services.national_material_service import NationalMaterialService


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / builders
# ─────────────────────────────────────────────────────────────────────────────

def _uom(db: Session, code: str = "EA") -> UOMMaster:
    u = db.query(UOMMaster).filter_by(canonical_code=code).first()
    if not u:
        u = UOMMaster(canonical_code=code, name="Each", dimension="COUNT")
        db.add(u)
        db.flush()
    return u


def _classification(db: Session, code: str = None, parent_id: str = None) -> Classification:
    code = code or f"CL-{uuid.uuid4().hex[:4]}"
    cl = Classification(
        classification_id=str(uuid.uuid4()),
        code=code,
        name=f"Class {code}",
        level=0 if not parent_id else 1,
        parent_id=parent_id,
    )
    db.add(cl)
    db.flush()
    return cl


def _create_nm(
    db: Session,
    *,
    description: str = "Standard Bolt M10",
    status_after_create: str = "PROVISIONAL",
    **kwargs,
) -> NationalMaterial:
    """Directly insert a NationalMaterial into the DB for test setup."""
    _uom(db, "EA")
    nm = NationalMaterial(
        national_material_id=str(uuid.uuid4()),
        national_material_code=kwargs.get("code", f"NAT-{uuid.uuid4().hex[:6]}"),
        canonical_description=description,
        canonical_uom="EA",
        status=status_after_create,
        version=1,
    )
    for k, v in kwargs.items():
        if k != "code":
            setattr(nm, k, v)
    db.add(nm)
    db.flush()
    return nm


def _svc(db: Session) -> NationalMaterialService:
    return NationalMaterialService(db)


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────

class TestCreate:
    def test_create_starts_provisional(self, db_session: Session):
        _uom(db_session)
        svc = _svc(db_session)
        result = svc.create(NationalMaterialCreate(
            canonical_description="High Pressure Valve 2in",
        ))
        assert result.status == "PROVISIONAL"
        assert result.version == 1
        assert result.national_material_code.startswith("NAT-")

    def test_create_custom_code(self, db_session: Session):
        _uom(db_session)
        code = f"CUSTOM-{uuid.uuid4().hex[:6]}"
        result = _svc(db_session).create(NationalMaterialCreate(
            national_material_code=code,
            canonical_description="Ball Bearing 6205",
        ))
        assert result.national_material_code == code

    def test_create_duplicate_code_raises_409(self, db_session: Session):
        _uom(db_session)
        code = f"DUP-{uuid.uuid4().hex[:6]}"
        _svc(db_session).create(NationalMaterialCreate(
            national_material_code=code,
            canonical_description="First",
        ))
        db_session.commit()
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).create(NationalMaterialCreate(
                national_material_code=code,
                canonical_description="Second",
            ))
        assert exc.value.status_code == 409

    def test_create_writes_audit_log(self, db_session: Session):
        _uom(db_session)
        result = _svc(db_session).create(NationalMaterialCreate(
            canonical_description="Gate Valve DN50",
            created_by="usr_steward",
        ))
        db_session.commit()
        audit = db_session.query(AuditLog).filter_by(
            entity_id=result.national_material_id,
            entity_type="NATIONAL_MATERIAL",
        ).first()
        assert audit is not None
        assert audit.action == "NATIONAL_MATERIAL_CREATED"
        assert audit.actor_id == "usr_steward"

    def test_create_with_classification(self, db_session: Session):
        _uom(db_session)
        cl = _classification(db_session)
        result = _svc(db_session).create(NationalMaterialCreate(
            canonical_description="AC Induction Motor 5HP",
            classification_id=cl.classification_id,
        ))
        assert result.classification_id == cl.classification_id


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────

class TestRead:
    def test_get_by_id(self, db_session: Session):
        nm = _create_nm(db_session)
        result = _svc(db_session).get(nm.national_material_id)
        assert result.national_material_id == nm.national_material_id
        assert result.canonical_description == nm.canonical_description

    def test_get_not_found(self, db_session: Session):
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).get("no-such-id")
        assert exc.value.status_code == 404

    def test_get_includes_audit_history(self, db_session: Session):
        _uom(db_session)
        created = _svc(db_session).create(NationalMaterialCreate(
            canonical_description="Test Motor 10kW",
            created_by="actor_1",
        ))
        db_session.commit()
        detail = _svc(db_session).get(created.national_material_id)
        assert len(detail.audit_history) >= 1
        assert detail.audit_history[0]["action"] == "NATIONAL_MATERIAL_CREATED"

    def test_get_includes_breadcrumb(self, db_session: Session):
        _uom(db_session)
        parent = _classification(db_session, code=f"P-{uuid.uuid4().hex[:4]}")
        child = _classification(db_session, code=f"C-{uuid.uuid4().hex[:4]}", parent_id=parent.classification_id)
        nm = _create_nm(db_session, classification_id=child.classification_id)
        detail = _svc(db_session).get(nm.national_material_id)
        codes = [b.code for b in detail.classification_breadcrumb]   # Pydantic model, not dict
        assert parent.code in codes
        assert child.code in codes
        # Parent comes before child
        assert codes.index(parent.code) < codes.index(child.code)


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────

class TestList:
    def test_list_filter_by_keyword(self, db_session: Session):
        _uom(db_session)
        svc = _svc(db_session)
        svc.create(NationalMaterialCreate(canonical_description="Deep Groove Ball Bearing 6205"))
        svc.create(NationalMaterialCreate(canonical_description="Gate Valve DN80"))
        db_session.commit()
        result = svc.list(keyword="Bearing")
        assert all("Bearing" in i.canonical_description for i in result.items)

    def test_list_filter_by_status(self, db_session: Session):
        _uom(db_session)
        svc = _svc(db_session)
        nm = _create_nm(db_session, status_after_create="ACTIVE")
        _create_nm(db_session, status_after_create="PROVISIONAL")
        db_session.flush()
        result = svc.list(status="ACTIVE")
        active_ids = {i.national_material_id for i in result.items}
        assert nm.national_material_id in active_ids
        assert all(i.status == "ACTIVE" for i in result.items)

    def test_list_filter_by_classification(self, db_session: Session):
        _uom(db_session)
        cl1 = _classification(db_session)
        cl2 = _classification(db_session)
        _create_nm(db_session, classification_id=cl1.classification_id)
        _create_nm(db_session, classification_id=cl2.classification_id)
        db_session.flush()
        svc = _svc(db_session)
        result = svc.list(classification_id=cl1.classification_id)
        assert all(i.classification_id == cl1.classification_id for i in result.items)

    def test_list_excludes_retired_by_default(self, db_session: Session):
        _uom(db_session)
        nm = _create_nm(db_session, status_after_create="RETIRED")
        nm.is_retired = True
        db_session.flush()
        svc = _svc(db_session)
        result = svc.list()
        ids = {i.national_material_id for i in result.items}
        assert nm.national_material_id not in ids

    def test_list_include_retired(self, db_session: Session):
        _uom(db_session)
        nm = _create_nm(db_session, status_after_create="RETIRED")
        nm.is_retired = True
        db_session.flush()
        svc = _svc(db_session)
        result = svc.list(include_retired=True, status="RETIRED")
        ids = {i.national_material_id for i in result.items}
        assert nm.national_material_id in ids


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdate:
    def test_update_description(self, db_session: Session):
        nm = _create_nm(db_session)
        result = _svc(db_session).update(
            nm.national_material_id,
            NationalMaterialUpdate(canonical_description="Updated Description", editor_id="usr_editor"),
        )
        assert result.canonical_description == "Updated Description"
        assert result.version == 2   # incremented

    def test_update_increments_version(self, db_session: Session):
        nm = _create_nm(db_session)
        assert nm.version == 1
        _svc(db_session).update(nm.national_material_id, NationalMaterialUpdate(canonical_description="Version 2"))
        _svc(db_session).update(nm.national_material_id, NationalMaterialUpdate(canonical_description="Version 3"))
        db_session.refresh(nm)
        assert nm.version == 3

    def test_update_creates_audit_log(self, db_session: Session):
        nm = _create_nm(db_session)
        _svc(db_session).update(
            nm.national_material_id,
            NationalMaterialUpdate(canonical_description="Changed", editor_id="usr_editor"),
        )
        db_session.commit()
        audit = db_session.query(AuditLog).filter_by(
            entity_id=nm.national_material_id,
            action="NATIONAL_MATERIAL_UPDATED",
        ).first()
        assert audit is not None
        assert audit.actor_id == "usr_editor"

    def test_update_retired_raises_422(self, db_session: Session):
        nm = _create_nm(db_session, status_after_create="RETIRED")
        nm.is_retired = True
        db_session.flush()
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).update(
                nm.national_material_id,
                NationalMaterialUpdate(canonical_description="Should fail"),
            )
        assert exc.value.status_code == 422

    def test_update_not_found(self, db_session: Session):
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).update("no-id", NationalMaterialUpdate(canonical_description="Not found test"))
        assert exc.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# LIFECYCLE TRANSITIONS
# ─────────────────────────────────────────────────────────────────────────────

class TestLifecycle:
    def _nm(self, db: Session, status: str = "PROVISIONAL") -> NationalMaterial:
        return _create_nm(db, status_after_create=status)

    def test_full_happy_path(self, db_session: Session):
        nm = self._nm(db_session, "PROVISIONAL")
        svc = _svc(db_session)

        r = svc.transition(nm.national_material_id, "UNDER_REVIEW", StatusTransitionRequest(actor_id="usr1"))
        assert r.status == "UNDER_REVIEW"
        assert r.version == 2

        r = svc.transition(nm.national_material_id, "ACTIVE", StatusTransitionRequest(actor_id="usr2"))
        assert r.status == "ACTIVE"
        assert r.version == 3

        r = svc.retire(nm.national_material_id, RetireRequest(actor_id="usr3", reason="EOL"))
        assert r.status == "RETIRED"
        assert r.is_retired is True

    def test_retired_is_terminal(self, db_session: Session):
        nm = self._nm(db_session, "RETIRED")
        nm.is_retired = True
        db_session.flush()
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).transition(
                nm.national_material_id, "ACTIVE", StatusTransitionRequest()
            )
        assert exc.value.status_code == 422

    def test_illegal_transition_raises_422(self, db_session: Session):
        nm = self._nm(db_session, "PROVISIONAL")
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).transition(
                nm.national_material_id, "ACTIVE",   # can't skip UNDER_REVIEW
                StatusTransitionRequest(actor_id="usr"),
            )
        assert exc.value.status_code == 422
        assert "ACTIVE" in exc.value.detail or "Cannot transition" in exc.value.detail

    def test_reject_from_provisional(self, db_session: Session):
        nm = self._nm(db_session, "PROVISIONAL")
        r = _svc(db_session).transition(
            nm.national_material_id, "REJECTED", StatusTransitionRequest(reason="Duplicate")
        )
        assert r.status == "REJECTED"

    def test_reject_from_under_review(self, db_session: Session):
        nm = self._nm(db_session, "UNDER_REVIEW")
        r = _svc(db_session).transition(
            nm.national_material_id, "REJECTED", StatusTransitionRequest()
        )
        assert r.status == "REJECTED"

    def test_resubmit_from_rejected(self, db_session: Session):
        nm = self._nm(db_session, "REJECTED")
        r = _svc(db_session).transition(
            nm.national_material_id, "PROVISIONAL", StatusTransitionRequest()
        )
        assert r.status == "PROVISIONAL"

    def test_supersede_active_material(self, db_session: Session):
        nm = self._nm(db_session, "ACTIVE")
        replacement_id = str(uuid.uuid4())   # real scenario: another NAT record
        r = _svc(db_session).retire(
            nm.national_material_id,
            RetireRequest(actor_id="usr", superseded_by=replacement_id),
        )
        assert r.status == "SUPERSEDED"

    def test_supersede_only_active_raises_422(self, db_session: Session):
        nm = self._nm(db_session, "PROVISIONAL")
        with pytest.raises(HTTPException) as exc:
            _svc(db_session).retire(
                nm.national_material_id,
                RetireRequest(superseded_by="some-other-id"),
            )
        assert exc.value.status_code == 422

    def test_transition_creates_audit_log(self, db_session: Session):
        nm = self._nm(db_session, "PROVISIONAL")
        _svc(db_session).transition(
            nm.national_material_id, "UNDER_REVIEW", StatusTransitionRequest(actor_id="reviewer")
        )
        db_session.commit()
        audit = db_session.query(AuditLog).filter_by(
            entity_id=nm.national_material_id,
            action="NATIONAL_MATERIAL_UNDER_REVIEW",
        ).first()
        assert audit is not None
        assert audit.actor_id == "reviewer"
        assert audit.new_value["status"] == "UNDER_REVIEW"

    def test_retire_creates_audit_log(self, db_session: Session):
        nm = self._nm(db_session, "ACTIVE")
        _svc(db_session).retire(
            nm.national_material_id,
            RetireRequest(actor_id="admin", reason="Obsolete"),
        )
        db_session.commit()
        audit = db_session.query(AuditLog).filter_by(
            entity_id=nm.national_material_id,
            action="NATIONAL_MATERIAL_RETIRED",
        ).first()
        assert audit is not None
        assert audit.new_value["reason"] == "Obsolete"
