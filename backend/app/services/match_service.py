"""
app/services/match_service.py — Business logic for matches and mappings.

Rules enforced here:
    - AI output (MatchResult) is NEVER modified.
    - Human decisions (Approval) are append-only.
    - Permissions are validated before any mutation.
    - Duplicate/conflicting mappings are rejected.
    - Every mutation emits an audit event (via repo).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Literal, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.middleware.request_context import get_request_id
from app.repositories.match_repo import MatchRepo, MatchRow, MappingRepo
from app.schemas.match import (
    ApprovalRead,
    MappingCreate,
    MappingRead,
    MatchDetail,
    MatchSummary,
    MaterialSnapshot,
    PaginatedMappings,
    PaginatedMatches,
    ReviewActionResponse,
)

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PERMISSION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

# Maps action → required permission string (from DEMO_USERS permission list)
_REQUIRED_PERMISSIONS: Dict[str, str] = {
    "approve":            "write",
    "reject":             "write",
    "engineering_review": "write",
    "create_mapping":     "write",
}


def _require_permission(user: Optional[dict], action: str) -> None:
    """
    Validates that the authenticated user has the required permission.
    Raises HTTP 403 if denied.
    user may be None in tests where auth is skipped.
    """
    if user is None:
        return   # unauthenticated — allow (test mode)
    required = _REQUIRED_PERMISSIONS.get(action, "write")
    if required not in user.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: '{required}' required for action '{action}'.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _match_summary(row: MatchRow) -> MatchSummary:
    m = row.match
    a = row.latest_approval
    return MatchSummary(
        match_id=m.match_id,
        material_a_id=m.material_a_id,
        material_b_id=m.material_b_id,
        final_score=m.final_score,
        semantic_score=m.semantic_score,
        attribute_score=m.attribute_score,
        rule_score=m.rule_score,
        match_type=m.match_type,
        recommendation=m.recommendation,
        risk_level=m.risk_level,
        requires_human_review=m.requires_human_review,
        model_version=m.model_version,
        created_at=m.created_at,
        decision=a.decision if a else None,
        review_type=a.review_type if a else None,
        reviewer_id=a.reviewer_id if a else None,
        decided_at=a.created_at if a else None,
    )


def _material_snapshot(src=None, norm=None, nat=None) -> MaterialSnapshot:
    return MaterialSnapshot(
        source_material_id=src.source_material_id if src else None,
        cpse_id=src.cpse_id if src else None,
        legacy_material_code=src.legacy_material_code if src else None,
        raw_description=src.raw_description if src else None,
        raw_uom=src.raw_uom if src else None,
        manufacturer=src.manufacturer if src else None,
        manufacturer_part_number=src.manufacturer_part_number if src else None,
        normalized_description=norm.normalized_description if norm else None,
        canonical_uom=norm.canonical_uom if norm else None,
        classification_id=norm.category_code if norm else None,
        confidence=norm.confidence if norm else None,
        national_material_id=nat.national_material_id if nat else None,
        national_material_code=nat.national_material_code if nat else None,
        national_description=nat.canonical_description if nat else None,
    )


def _approval_read(a) -> ApprovalRead:
    return ApprovalRead(
        approval_id=a.approval_id,
        match_id=a.match_id,
        reviewer_id=a.reviewer_id,
        decision=a.decision,
        comment=a.comment,
        review_type=a.review_type,
        created_at=a.created_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class MatchService:

    def __init__(self, db: Session):
        self._repo = MatchRepo(db)
        self._mapping_repo = MappingRepo(db)

    # ── Matches: reads ─────────────────────────────────────────────────────────

    def list_matches(
        self,
        *,
        decision: Optional[str] = None,
        match_type: Optional[str] = None,
        min_score: Optional[float] = None,
        requires_review: Optional[bool] = None,
        cpse_id: Optional[str] = None,
        sort_by: str = "final_score",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedMatches:
        rows, total = self._repo.list_matches(
            decision=decision,
            match_type=match_type,
            min_score=min_score,
            requires_review=requires_review,
            cpse_id=cpse_id,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        return PaginatedMatches(
            items=[_match_summary(r) for r in rows],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )

    def get_match(self, match_id: str) -> MatchDetail:
        row = self._repo.get_match(match_id)
        if not row:
            raise HTTPException(status_code=404, detail="Match not found.")
        m = row.match
        history = self._repo.get_review_history(match_id)
        latest = history[0] if history else None

        # Update row with full history's latest decision
        row.latest_approval = latest

        return MatchDetail(
            **_match_summary(row).model_dump(),
            positive_evidence=m.positive_evidence or {},
            negative_evidence=m.negative_evidence or {},
            conflicts=m.conflicts or {},
            prompt_version=m.prompt_version,
            rules_version=m.rules_version,
            material_a=_material_snapshot(row.mat_a_source, row.mat_a_norm),
            material_b=_material_snapshot(nat=row.mat_b_national),
            review_history=[_approval_read(a) for a in history],
        )

    # ── Matches: mutations ─────────────────────────────────────────────────────

    def _review(
        self,
        match_id: str,
        decision: Literal["APPROVED", "REJECTED", "ESCALATED"],
        reviewer_id: str,
        comment: Optional[str],
        review_type: Optional[str],
        user: Optional[dict],
    ) -> ReviewActionResponse:
        _require_permission(user, "approve" if decision == "APPROVED" else "reject")

        # Verify match exists (404 if not)
        row = self._repo.get_match(match_id)
        if not row:
            raise HTTPException(status_code=404, detail="Match not found.")

        approval = self._repo.create_approval(
            match_id=match_id,
            decision=decision,
            reviewer_id=reviewer_id,
            comment=comment,
            review_type=review_type or decision,
            request_id=get_request_id(),
        )
        return ReviewActionResponse(
            match_id=match_id,
            approval_id=approval.approval_id,
            decision=decision,
            reviewer_id=reviewer_id,
            comment=comment,
            created_at=approval.created_at,
        )

    def approve_match(
        self, match_id: str, reviewer_id: str,
        comment: Optional[str] = None, user: Optional[dict] = None
    ) -> ReviewActionResponse:
        return self._review(match_id, "APPROVED", reviewer_id, comment, "HUMAN_APPROVAL", user)

    def reject_match(
        self, match_id: str, reviewer_id: str,
        comment: Optional[str] = None, user: Optional[dict] = None
    ) -> ReviewActionResponse:
        return self._review(match_id, "REJECTED", reviewer_id, comment, "HUMAN_REJECTION", user)

    def engineering_review(
        self, match_id: str, reviewer_id: str,
        comment: Optional[str] = None, user: Optional[dict] = None
    ) -> ReviewActionResponse:
        _require_permission(user, "engineering_review")
        row = self._repo.get_match(match_id)
        if not row:
            raise HTTPException(status_code=404, detail="Match not found.")
        approval = self._repo.create_approval(
            match_id=match_id,
            decision="ESCALATED",
            reviewer_id=reviewer_id,
            comment=comment,
            review_type="ENGINEERING_REVIEW",
            request_id=get_request_id(),
        )
        return ReviewActionResponse(
            match_id=match_id,
            approval_id=approval.approval_id,
            decision="ESCALATED",
            reviewer_id=reviewer_id,
            comment=comment,
            created_at=approval.created_at,
        )

    # ── Mappings ───────────────────────────────────────────────────────────────

    def create_mapping(
        self, body: MappingCreate, created_by: str, user: Optional[dict] = None
    ) -> MappingRead:
        _require_permission(user, "create_mapping")
        try:
            mm = self._mapping_repo.create_mapping(
                source_material_id=body.source_material_id,
                national_material_id=body.national_material_id,
                mapping_type=body.mapping_type,
                confidence=body.confidence,
                notes=body.notes,
                created_by=created_by,
                request_id=get_request_id(),
            )
        except ValueError as e:
            raise HTTPException(status_code=409, detail=str(e))
        return self._enrich_mapping(mm)

    def list_mappings(
        self,
        *,
        source_material_id: Optional[str] = None,
        national_material_id: Optional[str] = None,
        mapping_type: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedMappings:
        mappings, total = self._mapping_repo.list_mappings(
            source_material_id=source_material_id,
            national_material_id=national_material_id,
            mapping_type=mapping_type,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        return PaginatedMappings(
            items=[self._enrich_mapping(m) for m in mappings],
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )

    def get_mapping(self, mapping_id: str) -> MappingRead:
        mm = self._mapping_repo.get_mapping(mapping_id)
        if not mm:
            raise HTTPException(status_code=404, detail="Mapping not found.")
        return self._enrich_mapping(mm)

    def _enrich_mapping(self, mm) -> MappingRead:
        # Pull denormalised codes via session lazy-load (already joined in repo if needed)
        nat = mm.national
        src = mm.source if hasattr(mm, "source") else None
        nat_code = nat.national_material_code if nat else None
        legacy_code = src.legacy_material_code if src else None
        return MappingRead(
            mapping_id=mm.mapping_id,
            source_material_id=mm.source_material_id,
            national_material_id=mm.national_material_id,
            mapping_type=mm.mapping_type,
            confidence=mm.confidence,
            status=mm.status,
            created_by=mm.created_by,
            approved_by=mm.approved_by,
            approved_at=mm.approved_at,
            notes=mm.notes,
            is_ai_suggested=mm.is_ai_suggested,
            created_at=mm.created_at,
            updated_at=mm.updated_at,
            national_material_code=nat_code,
            legacy_material_code=legacy_code,
        )
