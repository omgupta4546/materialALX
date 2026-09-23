"""
app/repositories/match_repo.py — Query logic for matches, approvals, and mappings.

All SQL lives here. No HTTP concerns, no business rules.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from app.models.base import (
    Approval,
    AuditLog,
    MaterialMapping,
    MatchResult,
    NationalMaterial,
    NormalizedMaterial,
    SourceMaterial,
)

log = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─────────────────────────────────────────────────────────────────────────────
# RESULT PROJECTIONS
# ─────────────────────────────────────────────────────────────────────────────

class MatchRow:
    """Flat projection of MatchResult + latest Approval (if any)."""
    __slots__ = (
        "match", "latest_approval",
        "mat_a_source", "mat_a_norm",
        "mat_b_national",
    )

    def __init__(
        self,
        match: MatchResult,
        latest_approval: Optional[Approval] = None,
        mat_a_source: Optional[SourceMaterial] = None,
        mat_a_norm: Optional[NormalizedMaterial] = None,
        mat_b_national: Optional[NationalMaterial] = None,
    ):
        self.match = match
        self.latest_approval = latest_approval
        self.mat_a_source = mat_a_source
        self.mat_a_norm = mat_a_norm
        self.mat_b_national = mat_b_national


# ─────────────────────────────────────────────────────────────────────────────
# MATCH REPO
# ─────────────────────────────────────────────────────────────────────────────

class MatchRepo:

    def __init__(self, db: Session):
        self.db = db

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _latest_approvals_subq(self):
        """Subquery: latest approval per match_id."""
        inner = (
            self.db.query(
                Approval.match_id,
                func.max(Approval.created_at).label("max_ts"),
            )
            .group_by(Approval.match_id)
            .subquery()
        )
        return inner

    def _enrich(self, match: MatchResult) -> MatchRow:
        approval = (
            self.db.query(Approval)
            .filter(Approval.match_id == match.match_id)
            .order_by(Approval.created_at.desc())
            .first()
        )
        src_a = self.db.query(SourceMaterial).filter(
            SourceMaterial.source_material_id == match.material_a_id
        ).first()
        norm_a = (
            self.db.query(NormalizedMaterial)
            .filter(NormalizedMaterial.normalized_material_id == match.material_a_id)
            .first()
        ) if not src_a else (
            self.db.query(NormalizedMaterial)
            .filter(NormalizedMaterial.source_material_id == match.material_a_id)
            .first()
        )
        nat_b = self.db.query(NationalMaterial).filter(
            NationalMaterial.national_material_id == match.material_b_id
        ).first()
        return MatchRow(match, approval, src_a, norm_a, nat_b)

    # ── List / search ─────────────────────────────────────────────────────────

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
    ) -> Tuple[List[MatchRow], int]:
        q = self.db.query(MatchResult)

        if match_type:
            q = q.filter(MatchResult.match_type == match_type)
        if min_score is not None:
            q = q.filter(MatchResult.final_score >= min_score)
        if requires_review is not None:
            q = q.filter(MatchResult.requires_human_review == requires_review)
        if cpse_id:
            q = q.filter(or_(
                self.db.query(SourceMaterial.source_material_id)
                .filter(SourceMaterial.source_material_id == MatchResult.material_a_id, SourceMaterial.cpse_id == cpse_id)
                .exists(),
                self.db.query(NormalizedMaterial.normalized_material_id)
                .join(SourceMaterial, NormalizedMaterial.source_material_id == SourceMaterial.source_material_id)
                .filter(NormalizedMaterial.normalized_material_id == MatchResult.material_a_id, SourceMaterial.cpse_id == cpse_id)
                .exists()
            ))

        # Filter on latest decision via subquery
        if decision:
            latest_subq = self._latest_approvals_subq()
            approval_alias = aliased(Approval)
            q = (
                q.join(
                    latest_subq,
                    latest_subq.c.match_id == MatchResult.match_id,
                    isouter=True,
                )
                .outerjoin(
                    approval_alias,
                    (approval_alias.match_id == MatchResult.match_id)
                    & (approval_alias.created_at == latest_subq.c.max_ts),
                )
            )
            if decision == "PENDING":
                q = q.filter(approval_alias.approval_id.is_(None))
            else:
                q = q.filter(approval_alias.decision == decision)

        total = q.count()

        sort_col = {
            "final_score": MatchResult.final_score,
            "semantic_score": MatchResult.semantic_score,
            "created_at": MatchResult.created_at,
        }.get(sort_by, MatchResult.final_score)
        q = q.order_by(sort_col.asc() if sort_dir == "asc" else sort_col.desc())

        matches = q.offset(offset).limit(limit).all()
        rows = [self._enrich(m) for m in matches]
        return rows, total

    # ── Single match ──────────────────────────────────────────────────────────

    def get_match(self, match_id: str) -> Optional[MatchRow]:
        m = self.db.query(MatchResult).filter(MatchResult.match_id == match_id).first()
        if not m:
            return None
        row = self._enrich(m)
        row.latest_approval = None  # full history loaded by service
        return row

    def get_review_history(self, match_id: str) -> List[Approval]:
        return (
            self.db.query(Approval)
            .filter(Approval.match_id == match_id)
            .order_by(Approval.created_at.desc())
            .all()
        )

    # ── Human decision persistence ─────────────────────────────────────────────

    def create_approval(
        self,
        match_id: str,
        decision: str,
        reviewer_id: str,
        comment: Optional[str],
        review_type: Optional[str],
        request_id: Optional[str] = None,
    ) -> Approval:
        """
        Persist a human review decision.
        MatchResult is NEVER touched — it is append-only AI output.
        """
        approval = Approval(
            approval_id=str(uuid.uuid4()),
            match_id=match_id,
            reviewer_id=reviewer_id,
            decision=decision,
            comment=comment,
            review_type=review_type,
        )
        self.db.add(approval)

        audit = AuditLog(
            audit_id=str(uuid.uuid4()),
            entity_type="MATCH",
            entity_id=match_id,
            action=f"MATCH_{decision}",
            old_value={},
            new_value={
                "decision": decision,
                "reviewer_id": reviewer_id,
                "comment": comment,
                "review_type": review_type,
            },
            actor_id=reviewer_id,
            timestamp=_utcnow(),
            source="API",
            request_id=request_id,
        )
        self.db.add(audit)
        self.db.flush()
        return approval


# ─────────────────────────────────────────────────────────────────────────────
# MAPPING REPO
# ─────────────────────────────────────────────────────────────────────────────

class MappingRepo:

    def __init__(self, db: Session):
        self.db = db

    def _check_conflicts(self, source_material_id: str) -> None:
        """A source material may only have one PENDING or APPROVED mapping at a time."""
        existing = (
            self.db.query(MaterialMapping)
            .filter(
                MaterialMapping.source_material_id == source_material_id,
                MaterialMapping.status.in_(["PENDING", "APPROVED"]),
            )
            .first()
        )
        if existing:
            raise ValueError(
                f"Source material '{source_material_id}' already has an active "
                f"mapping (mapping_id={existing.mapping_id}, status={existing.status}). "
                "Reject or supersede it before creating a new one."
            )

    def create_mapping(
        self,
        source_material_id: str,
        national_material_id: str,
        mapping_type: str,
        confidence: Optional[float],
        notes: Optional[str],
        created_by: str,
        request_id: Optional[str] = None,
    ) -> MaterialMapping:
        self._check_conflicts(source_material_id)

        mm = MaterialMapping(
            mapping_id=str(uuid.uuid4()),
            source_material_id=source_material_id,
            national_material_id=national_material_id,
            mapping_type=mapping_type,
            confidence=confidence,
            status="PENDING",
            created_by=created_by,
            is_ai_suggested=False,
            notes=notes,
        )
        self.db.add(mm)

        audit = AuditLog(
            audit_id=str(uuid.uuid4()),
            entity_type="MAPPING",
            entity_id=mm.mapping_id,
            action="MAPPING_CREATED",
            old_value={},
            new_value={
                "source_material_id": source_material_id,
                "national_material_id": national_material_id,
                "mapping_type": mapping_type,
                "created_by": created_by,
            },
            actor_id=created_by,
            timestamp=_utcnow(),
            source="API",
            request_id=request_id,
        )
        self.db.add(audit)
        self.db.flush()
        return mm

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
    ) -> Tuple[List[MaterialMapping], int]:
        q = self.db.query(MaterialMapping)
        if source_material_id:
            q = q.filter(MaterialMapping.source_material_id == source_material_id)
        if national_material_id:
            q = q.filter(MaterialMapping.national_material_id == national_material_id)
        if mapping_type:
            q = q.filter(MaterialMapping.mapping_type == mapping_type)
        if status:
            q = q.filter(MaterialMapping.status == status)

        total = q.count()
        col = {
            "created_at": MaterialMapping.created_at,
            "confidence": MaterialMapping.confidence,
            "status": MaterialMapping.status,
            "mapping_type": MaterialMapping.mapping_type,
        }.get(sort_by, MaterialMapping.created_at)
        q = q.order_by(col.asc() if sort_dir == "asc" else col.desc())
        return q.offset(offset).limit(limit).all(), total

    def get_mapping(self, mapping_id: str) -> Optional[MaterialMapping]:
        return self.db.query(MaterialMapping).filter(
            MaterialMapping.mapping_id == mapping_id
        ).first()
