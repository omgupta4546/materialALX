"""
Integration tests for matches and mappings.

All tests use the service layer directly (not HTTP) so they exercise:
    - Repository SQL (via SQLite in-memory)
    - Service business logic (permissions, immutability, conflict detection)
    - Audit log creation

Rules verified:
    - AI output (MatchResult) is NEVER modified by human decisions
    - Approval is append-only
    - Every mutation creates an AuditLog entry
    - Conflicting mappings are rejected with 409
    - 404 on unknown match_id / mapping_id
    - Permission guard raises 403
    - Engineering-review creates ESCALATED decision
    - Approve and reject emit distinct decision types
    - Mapping list and get work correctly
"""
import uuid
import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.base import (
    AuditLog,
    Approval,
    CPSE,
    Classification,
    MaterialMapping,
    MatchResult,
    NationalMaterial,
    NormalizedMaterial,
    SourceMaterial,
    UOMMaster,
)
from app.schemas.match import MappingCreate
from app.services.match_service import MatchService


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures / builders
# ─────────────────────────────────────────────────────────────────────────────

def _cpse(db: Session) -> CPSE:
    c = CPSE(cpse_id=str(uuid.uuid4()), cpse_code=f"T-{uuid.uuid4().hex[:6]}", cpse_name="Test", status="ACTIVE")
    db.add(c); db.flush(); return c


def _uom(db: Session, code="EA") -> UOMMaster:
    u = db.query(UOMMaster).filter_by(canonical_code=code).first()
    if not u:
        u = UOMMaster(canonical_code=code, name="Each", dimension="COUNT")
        db.add(u); db.flush()
    return u


def _classification(db: Session) -> Classification:
    cl = Classification(
        classification_id=str(uuid.uuid4()),
        code=f"CL-{uuid.uuid4().hex[:4]}",
        name="Test Class", level=0,
    )
    db.add(cl); db.flush(); return cl


def _source(db: Session, cpse_id: str) -> SourceMaterial:
    sm = SourceMaterial(
        source_material_id=str(uuid.uuid4()),
        cpse_id=cpse_id,
        legacy_material_code=f"MAT-{uuid.uuid4().hex[:6]}",
        raw_description="Test Bolt",
    )
    db.add(sm); db.flush(); return sm


def _normalized(db: Session, sm: SourceMaterial) -> NormalizedMaterial:
    nm = NormalizedMaterial(
        normalized_material_id=str(uuid.uuid4()),
        source_material_id=sm.source_material_id,
        normalized_description="Test Bolt (norm)",
        canonical_uom="EA",
        normalization_version="v1",
        confidence=0.95,
    )
    db.add(nm); db.flush(); return nm


def _national(db: Session, cl: Classification) -> NationalMaterial:
    _uom(db)
    n = NationalMaterial(
        national_material_id=str(uuid.uuid4()),
        national_material_code=f"NAT-{uuid.uuid4().hex[:6]}",
        canonical_description="Golden Bolt",
        classification_id=cl.classification_id,
        canonical_uom="EA",
        status="ACTIVE",
        version=1,
    )
    db.add(n); db.flush(); return n


def _match_result(
    db: Session, norm: NormalizedMaterial, nat: NationalMaterial,
    score: float = 0.92, requires_review: bool = True,
) -> MatchResult:
    mr = MatchResult(
        match_id=str(uuid.uuid4()),
        material_a_id=norm.normalized_material_id,
        material_b_id=nat.national_material_id,
        semantic_score=score,
        attribute_score=score - 0.05,
        rule_score=score - 0.02,
        final_score=score,
        match_type="NEAR_DUPLICATE",
        recommendation="APPROVE",
        risk_level="LOW",
        requires_human_review=requires_review,
        model_version="v1.0",
        positive_evidence={"desc_match": True},
        negative_evidence={},
        conflicts={},
    )
    db.add(mr); db.flush(); return mr


def _setup(db: Session):
    """Convenience: returns (source, norm, nat, match, svc)."""
    cpse = _cpse(db)
    cl = _classification(db)
    sm = _source(db, cpse.cpse_id)
    nm = _normalized(db, sm)
    nat = _national(db, cl)
    mr = _match_result(db, nm, nat)
    svc = MatchService(db)
    return sm, nm, nat, mr, svc


# ─────────────────────────────────────────────────────────────────────────────
# MATCH TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestMatchList:
    def test_list_empty(self, db_session: Session):
        svc = MatchService(db_session)
        result = svc.list_matches()
        assert result.total == 0
        assert result.items == []

    def test_list_returns_matches(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        result = svc.list_matches()
        assert result.total == 1
        item = result.items[0]
        assert item.match_id == mr.match_id
        assert item.final_score == pytest.approx(0.92)

    def test_list_filter_by_match_type(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        result = svc.list_matches(match_type="NEAR_DUPLICATE")
        assert result.total == 1
        result2 = svc.list_matches(match_type="EXACT_DUPLICATE")
        assert result2.total == 0

    def test_list_filter_by_min_score(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        result = svc.list_matches(min_score=0.95)
        assert result.total == 0
        result2 = svc.list_matches(min_score=0.90)
        assert result2.total == 1

    def test_list_filter_decision_pending(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        # Pending = no approval yet
        result = svc.list_matches(decision="PENDING")
        assert result.total == 1

    def test_list_filter_decision_approved_filters_correctly(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        svc.approve_match(mr.match_id, reviewer_id="usr_test")
        db_session.commit()
        approved = svc.list_matches(decision="APPROVED")
        assert approved.total == 1
        pending = svc.list_matches(decision="PENDING")
        assert pending.total == 0

    def test_pagination(self, db_session: Session):
        cpse = _cpse(db_session)
        cl = _classification(db_session)
        nat = _national(db_session, cl)
        created_ids = []
        for i in range(5):
            sm = _source(db_session, cpse.cpse_id)
            nm = _normalized(db_session, sm)
            mr = _match_result(db_session, nm, nat, score=round(0.5 + i * 0.08, 2))
            created_ids.append(mr.match_id)
        db_session.flush()

        # Verify created IDs appear across pages using the single CPSE's nat to filter
        svc = MatchService(db_session)
        # Count all matches from our newly created nat (isolated via nat_id)
        from app.models.base import MatchResult as MR
        total_for_nat = db_session.query(MR).filter(
            MR.material_b_id == nat.national_material_id
        ).count()
        assert total_for_nat == 5
        p1 = svc.list_matches(limit=2, offset=0)
        p2 = svc.list_matches(limit=2, offset=2)
        assert p1.has_more is True
        ids1 = {i.match_id for i in p1.items}
        ids2 = {i.match_id for i in p2.items}
        assert ids1.isdisjoint(ids2)


class TestMatchDetail:
    def test_get_match_not_found(self, db_session: Session):
        svc = MatchService(db_session)
        with pytest.raises(HTTPException) as exc:
            svc.get_match("no-such-id")
        assert exc.value.status_code == 404

    def test_get_match_detail(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        detail = svc.get_match(mr.match_id)
        assert detail.match_id == mr.match_id
        assert detail.positive_evidence == {"desc_match": True}
        assert detail.review_history == []

    def test_ai_output_preserved_after_approval(self, db_session: Session):
        """Core invariant: MatchResult fields are identical before and after human decision."""
        sm, nm, nat, mr, svc = _setup(db_session)

        before_score = mr.final_score
        before_rec = mr.recommendation
        before_evidence = mr.positive_evidence

        svc.approve_match(mr.match_id, reviewer_id="usr_reviewer")
        db_session.commit()

        # Reload from DB
        fresh = db_session.query(MatchResult).filter_by(match_id=mr.match_id).first()
        assert fresh.final_score == before_score
        assert fresh.recommendation == before_rec
        assert fresh.positive_evidence == before_evidence
        assert fresh.match_type == mr.match_type
        assert fresh.model_version == mr.model_version


class TestMatchApprove:
    def test_approve_creates_approval(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        response = svc.approve_match(mr.match_id, reviewer_id="usr_reviewer", comment="Looks good")
        db_session.commit()
        assert response.decision == "APPROVED"
        assert response.match_id == mr.match_id
        approvals = db_session.query(Approval).filter_by(match_id=mr.match_id).all()
        assert len(approvals) == 1
        assert approvals[0].decision == "APPROVED"
        assert approvals[0].reviewer_id == "usr_reviewer"

    def test_approve_creates_audit_log(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        svc.approve_match(mr.match_id, reviewer_id="usr_reviewer")
        db_session.commit()
        audit = db_session.query(AuditLog).filter_by(entity_id=mr.match_id).first()
        assert audit is not None
        assert audit.action == "MATCH_APPROVED"
        assert audit.actor_id == "usr_reviewer"
        assert audit.entity_type == "MATCH"

    def test_approve_match_not_found(self, db_session: Session):
        svc = MatchService(db_session)
        with pytest.raises(HTTPException) as exc:
            svc.approve_match("no-such-id", reviewer_id="usr")
        assert exc.value.status_code == 404

    def test_multiple_approvals_are_all_preserved(self, db_session: Session):
        """Decisions are append-only — no overwrite."""
        sm, nm, nat, mr, svc = _setup(db_session)
        svc.approve_match(mr.match_id, reviewer_id="reviewer_1")
        db_session.commit()
        svc.reject_match(mr.match_id, reviewer_id="reviewer_2", comment="On second thought")
        db_session.commit()
        all_approvals = db_session.query(Approval).filter_by(match_id=mr.match_id).all()
        assert len(all_approvals) == 2
        decisions = {a.decision for a in all_approvals}
        assert "APPROVED" in decisions
        assert "REJECTED" in decisions


class TestMatchReject:
    def test_reject_creates_approval(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        response = svc.reject_match(mr.match_id, reviewer_id="usr_reviewer", comment="Wrong category")
        db_session.commit()
        assert response.decision == "REJECTED"
        approval = db_session.query(Approval).filter_by(match_id=mr.match_id).first()
        assert approval.decision == "REJECTED"
        assert approval.comment == "Wrong category"

    def test_reject_creates_audit_log(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        svc.reject_match(mr.match_id, reviewer_id="usr_reviewer")
        db_session.commit()
        audit = db_session.query(AuditLog).filter_by(entity_id=mr.match_id).first()
        assert audit.action == "MATCH_REJECTED"


class TestEngineeringReview:
    def test_engineering_review_creates_escalated(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        response = svc.engineering_review(mr.match_id, reviewer_id="engineer_1", comment="Needs SME")
        db_session.commit()
        assert response.decision == "ESCALATED"
        approval = db_session.query(Approval).filter_by(match_id=mr.match_id).first()
        assert approval.review_type == "ENGINEERING_REVIEW"
        assert approval.decision == "ESCALATED"

    def test_detail_includes_review_history(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        svc.engineering_review(mr.match_id, reviewer_id="eng1")
        db_session.commit()
        detail = svc.get_match(mr.match_id)
        assert len(detail.review_history) == 1
        assert detail.review_history[0].decision == "ESCALATED"


class TestPermissions:
    def test_approve_with_no_write_permission_raises_403(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        auditor_user = {
            "user_id": "usr_auditor",
            "permissions": ["read", "view_audit_logs"],
        }
        with pytest.raises(HTTPException) as exc:
            svc.approve_match(mr.match_id, reviewer_id="usr_auditor", user=auditor_user)
        assert exc.value.status_code == 403

    def test_approve_with_write_permission_succeeds(self, db_session: Session):
        sm, nm, nat, mr, svc = _setup(db_session)
        steward_user = {
            "user_id": "usr_steward",
            "permissions": ["read", "write", "merge_materials"],
        }
        response = svc.approve_match(mr.match_id, reviewer_id="usr_steward", user=steward_user)
        db_session.commit()
        assert response.decision == "APPROVED"

    def test_create_mapping_without_write_permission_raises_403(self, db_session: Session):
        cpse = _cpse(db_session)
        cl = _classification(db_session)
        sm = _source(db_session, cpse.cpse_id)
        nat = _national(db_session, cl)
        svc = MatchService(db_session)
        body = MappingCreate(
            source_material_id=sm.source_material_id,
            national_material_id=nat.national_material_id,
            mapping_type="EXACT_DUPLICATE",
        )
        with pytest.raises(HTTPException) as exc:
            svc.create_mapping(body, created_by="usr_auditor", user={"permissions": ["read"]})
        assert exc.value.status_code == 403


# ─────────────────────────────────────────────────────────────────────────────
# MAPPING TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestMappings:
    def _setup(self, db: Session):
        cpse = _cpse(db)
        cl = _classification(db)
        sm = _source(db, cpse.cpse_id)
        nat = _national(db, cl)
        svc = MatchService(db)
        return sm, nat, svc

    def test_create_mapping(self, db_session: Session):
        sm, nat, svc = self._setup(db_session)
        body = MappingCreate(
            source_material_id=sm.source_material_id,
            national_material_id=nat.national_material_id,
            mapping_type="EXACT_DUPLICATE",
            confidence=0.99,
        )
        result = svc.create_mapping(body, created_by="usr_steward")
        db_session.commit()
        assert result.mapping_id is not None
        assert result.mapping_type == "EXACT_DUPLICATE"
        assert result.status == "PENDING"
        assert result.is_ai_suggested is False

    def test_create_mapping_creates_audit_log(self, db_session: Session):
        sm, nat, svc = self._setup(db_session)
        body = MappingCreate(
            source_material_id=sm.source_material_id,
            national_material_id=nat.national_material_id,
            mapping_type="LEGACY_MAPPING",
        )
        result = svc.create_mapping(body, created_by="usr_steward")
        db_session.commit()
        audit = db_session.query(AuditLog).filter_by(
            entity_id=result.mapping_id, entity_type="MAPPING"
        ).first()
        assert audit is not None
        assert audit.action == "MAPPING_CREATED"
        assert audit.actor_id == "usr_steward"

    def test_create_duplicate_mapping_raises_409(self, db_session: Session):
        sm, nat, svc = self._setup(db_session)
        body = MappingCreate(
            source_material_id=sm.source_material_id,
            national_material_id=nat.national_material_id,
            mapping_type="EXACT_DUPLICATE",
        )
        svc.create_mapping(body, created_by="usr1")
        db_session.commit()
        with pytest.raises(HTTPException) as exc:
            svc.create_mapping(body, created_by="usr2")
        assert exc.value.status_code == 409
        assert "active" in exc.value.detail.lower() or "conflicting" in exc.value.detail.lower()

    def test_list_mappings_empty(self, db_session: Session):
        # Use source_material_id filter — unambiguous isolation even with DB state
        sm, nat, svc = self._setup(db_session)
        result = svc.list_mappings(source_material_id=sm.source_material_id)
        assert result.total == 0

    def test_list_mappings_returns_created(self, db_session: Session):
        sm, nat, svc = self._setup(db_session)
        body = MappingCreate(
            source_material_id=sm.source_material_id,
            national_material_id=nat.national_material_id,
            mapping_type="NEAR_DUPLICATE",
        )
        svc.create_mapping(body, created_by="usr1")
        db_session.commit()
        # Filter by source_material_id to avoid picking up other tests' mappings
        result = svc.list_mappings(source_material_id=sm.source_material_id)
        assert result.total == 1
        assert result.items[0].mapping_type == "NEAR_DUPLICATE"

    def test_list_mappings_filter_by_source(self, db_session: Session):
        sm, nat, svc = self._setup(db_session)
        cpse2 = _cpse(db_session)
        sm2 = _source(db_session, cpse2.cpse_id)
        nat2 = _national(db_session, _classification(db_session))

        svc.create_mapping(
            MappingCreate(source_material_id=sm.source_material_id,
                          national_material_id=nat.national_material_id,
                          mapping_type="EXACT_DUPLICATE"),
            created_by="usr1",
        )
        db_session.commit()
        svc2 = MatchService(db_session)
        svc2.create_mapping(
            MappingCreate(source_material_id=sm2.source_material_id,
                          national_material_id=nat2.national_material_id,
                          mapping_type="LEGACY_MAPPING"),
            created_by="usr1",
        )
        db_session.commit()
        result = svc.list_mappings(source_material_id=sm.source_material_id)
        assert result.total == 1
        assert result.items[0].source_material_id == sm.source_material_id

    def test_get_mapping(self, db_session: Session):
        sm, nat, svc = self._setup(db_session)
        body = MappingCreate(
            source_material_id=sm.source_material_id,
            national_material_id=nat.national_material_id,
            mapping_type="FUNCTIONALLY_EQUIVALENT",
            notes="Reviewed by engineering",
        )
        created = svc.create_mapping(body, created_by="eng1")
        db_session.commit()
        fetched = svc.get_mapping(created.mapping_id)
        assert fetched.mapping_id == created.mapping_id
        assert fetched.notes == "Reviewed by engineering"

    def test_get_mapping_not_found(self, db_session: Session):
        svc = MatchService(db_session)
        with pytest.raises(HTTPException) as exc:
            svc.get_mapping("no-such-id")
        assert exc.value.status_code == 404
