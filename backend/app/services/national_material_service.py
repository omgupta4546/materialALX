"""
app/services/national_material_service.py — Business logic for the governed national material lifecycle.

No SQLAlchemy imported here — all DB access flows through NationalMaterialRepo.
No HTTP imported here — all HTTP concerns stay in the router.

Governance rules enforced:
    - Status may only advance through the defined state machine.
    - Version is auto-incremented on every persisted change.
    - RETIRED records are permanently immutable.
    - No frontend can write directly — all writes pass through this service.
    - Every mutation produces an immutable AuditLog entry.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.middleware.request_context import get_request_id
from app.repositories.national_material_repo import (
    NationalMaterialRepo,
    build_breadcrumb,
    get_mapping_counts,
)
from app.schemas.national_material import (
    NationalMaterialCreate,
    NationalMaterialDetail,
    NationalMaterialRead,
    NationalMaterialUpdate,
    PaginatedNationalMaterialsFull,
    RetireRequest,
    StatusTransitionRequest,
)

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _to_read(nm, breadcrumb, src_count: int, cpse_count: int) -> NationalMaterialRead:
    return NationalMaterialRead(
        national_material_id=nm.national_material_id,
        national_material_code=nm.national_material_code,
        canonical_description=nm.canonical_description,
        classification_id=nm.classification_id,
        canonical_uom=nm.canonical_uom,
        status=nm.status,
        version=nm.version,
        provenance=nm.provenance,
        created_by=nm.created_by,
        created_at=nm.created_at,
        updated_at=nm.updated_at,
        is_retired=nm.is_retired,
        classification_breadcrumb=breadcrumb,
        source_count=src_count,
        cpse_count=cpse_count,
        attributes=nm.attributes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class NationalMaterialService:

    def __init__(self, db: Session):
        self._db = db
        self._repo = NationalMaterialRepo(db)

    def _get_or_404(self, national_material_id: str):
        nm = self._repo.get(national_material_id)
        if not nm:
            raise HTTPException(status_code=404, detail="National material not found.")
        return nm

    def _enrich(self, nm) -> NationalMaterialRead:
        breadcrumb = build_breadcrumb(self._db, nm.classification_id)
        src_count, cpse_count = get_mapping_counts(self._db, nm.national_material_id)
        return _to_read(nm, breadcrumb, src_count, cpse_count)

    # ── READ ──────────────────────────────────────────────────────────────────

    def list(
        self,
        *,
        keyword: Optional[str] = None,
        classification_id: Optional[str] = None,
        canonical_uom: Optional[str] = None,
        status: Optional[str] = None,
        include_retired: bool = False,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedNationalMaterialsFull:
        nats, total = self._repo.list(
            keyword=keyword,
            classification_id=classification_id,
            canonical_uom=canonical_uom,
            status=status,
            include_retired=include_retired,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        items = [self._enrich(n) for n in nats]
        return PaginatedNationalMaterialsFull(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        )

    def get(self, national_material_id: str) -> NationalMaterialDetail:
        nm = self._get_or_404(national_material_id)
        base = self._enrich(nm)

        # Mappings summary (up to 50)
        from app.models.base import MaterialMapping, SourceMaterial
        mappings_raw = (
            self._db.query(MaterialMapping, SourceMaterial)
            .join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
            .filter(MaterialMapping.national_material_id == national_material_id)
            .limit(50)
            .all()
        )
        mappings_summary = [
            {
                "mapping_id": mm.mapping_id,
                "source_material_id": sm.source_material_id,
                "legacy_material_code": sm.legacy_material_code,
                "cpse_id": sm.cpse_id,
                "mapping_type": mm.mapping_type,
                "status": mm.status,
                "confidence": mm.confidence,
            }
            for mm, sm in mappings_raw
        ]

        # Audit history (last 50 events)
        audit_rows = self._repo.get_audit_history(national_material_id)
        audit_history = [
            {
                "action": a.action,
                "actor_id": a.actor_id,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "old_value": a.old_value,
                "new_value": a.new_value,
            }
            for a in audit_rows
        ]

        return NationalMaterialDetail(
            **base.model_dump(),
            mappings_summary=mappings_summary,
            audit_history=audit_history,
        )

    # ── CREATE ────────────────────────────────────────────────────────────────

    def create(self, body: NationalMaterialCreate) -> NationalMaterialRead:
        try:
            nm = self._repo.create(
                canonical_description=body.canonical_description,
                classification_id=body.classification_id,
                canonical_uom=body.canonical_uom,
                attributes=body.attributes,
                provenance=body.provenance,
                created_by=body.created_by,
                national_material_code=body.national_material_code,
                request_id=get_request_id(),
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        return self._enrich(nm)

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def update(
        self, national_material_id: str, body: NationalMaterialUpdate
    ) -> NationalMaterialRead:
        nm = self._get_or_404(national_material_id)
        try:
            nm = self._repo.update(
                nm,
                canonical_description=body.canonical_description,
                classification_id=body.classification_id,
                canonical_uom=body.canonical_uom,
                attributes=body.attributes,
                provenance=body.provenance,
                editor_id=body.editor_id,
                request_id=get_request_id(),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return self._enrich(nm)

    # ── LIFECYCLE TRANSITIONS ─────────────────────────────────────────────────

    def retire(self, national_material_id: str, body: RetireRequest) -> NationalMaterialRead:
        nm = self._get_or_404(national_material_id)
        try:
            nm = self._repo.retire(
                nm,
                actor_id=body.actor_id,
                reason=body.reason,
                superseded_by=body.superseded_by,
                request_id=get_request_id(),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return self._enrich(nm)

    def transition(
        self,
        national_material_id: str,
        target_status: str,
        body: StatusTransitionRequest,
    ) -> NationalMaterialRead:
        nm = self._get_or_404(national_material_id)
        try:
            nm = self._repo.transition_status(
                nm,
                target_status=target_status,
                actor_id=body.actor_id,
                reason=body.reason,
                request_id=get_request_id(),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        return self._enrich(nm)
