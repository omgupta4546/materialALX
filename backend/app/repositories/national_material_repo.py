"""
app/repositories/national_material_repo.py — All SQL for NationalMaterial CRUD + lifecycle.

Governance responsibilities:
    - Code uniqueness check on create
    - Status-transition validation (state machine)
    - Version auto-increment on every approved change
    - Audit entry written alongside every mutation
    - RETIRED records are never mutated further
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.base import (
    AuditLog,
    Classification,
    MaterialMapping,
    NationalMaterial,
    SourceMaterial,
)
from app.schemas.national_material import ALLOWED_TRANSITIONS

log = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_id() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICATION BREADCRUMB HELPER
# ─────────────────────────────────────────────────────────────────────────────

def build_breadcrumb(db: Session, classification_id: Optional[str]) -> List[Dict]:
    if not classification_id:
        return []
    breadcrumb = []
    seen: set = set()
    cur_id = classification_id
    while cur_id and cur_id not in seen:
        seen.add(cur_id)
        cl = db.query(Classification).filter(
            Classification.classification_id == cur_id
        ).first()
        if not cl:
            break
        breadcrumb.insert(0, {
            "classification_id": cl.classification_id,
            "code": cl.code,
            "name": cl.name,
            "level": cl.level,
        })
        cur_id = cl.parent_id
    return breadcrumb


# ─────────────────────────────────────────────────────────────────────────────
# MAPPING COUNTS
# ─────────────────────────────────────────────────────────────────────────────

def get_mapping_counts(
    db: Session, national_material_id: str
) -> Tuple[int, int]:
    """Returns (source_count, cpse_count) for a given national material."""
    row = (
        db.query(
            func.count(MaterialMapping.source_material_id).label("src"),
            func.count(func.distinct(SourceMaterial.cpse_id)).label("cpse"),
        )
        .join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
        .filter(MaterialMapping.national_material_id == national_material_id)
        .first()
    )
    return (row.src if row else 0), (row.cpse if row else 0)


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _audit(
    db: Session,
    action: str,
    entity_id: str,
    actor_id: Optional[str],
    old_value: Optional[Dict] = None,
    new_value: Optional[Dict] = None,
    request_id: Optional[str] = None,
) -> None:
    db.add(AuditLog(
        audit_id=_new_id(),
        entity_type="NATIONAL_MATERIAL",
        entity_id=entity_id,
        action=action,
        old_value=old_value or {},
        new_value=new_value or {},
        actor_id=actor_id,
        timestamp=_utcnow(),
        source="API",
        request_id=request_id,
    ))


# ─────────────────────────────────────────────────────────────────────────────
# REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class NationalMaterialRepo:

    def __init__(self, db: Session):
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, national_material_id: str) -> Optional[NationalMaterial]:
        return self.db.query(NationalMaterial).filter(
            NationalMaterial.national_material_id == national_material_id
        ).first()

    def get_by_code(self, code: str) -> Optional[NationalMaterial]:
        return self.db.query(NationalMaterial).filter(
            NationalMaterial.national_material_code == code
        ).first()

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
    ) -> Tuple[List[NationalMaterial], int]:
        from sqlalchemy import or_
        q = self.db.query(NationalMaterial)

        if not include_retired:
            q = q.filter(NationalMaterial.is_retired.is_(False))
        if keyword:
            kw = f"%{keyword}%"
            q = q.filter(
                or_(
                    NationalMaterial.canonical_description.ilike(kw),
                    NationalMaterial.national_material_code.ilike(kw),
                )
            )
        if classification_id:
            q = q.filter(NationalMaterial.classification_id == classification_id)
        if canonical_uom:
            q = q.filter(NationalMaterial.canonical_uom == canonical_uom)
        if status:
            q = q.filter(NationalMaterial.status == status)

        total = q.count()
        col_map = {
            "national_material_code": NationalMaterial.national_material_code,
            "canonical_description":  NationalMaterial.canonical_description,
            "status":                 NationalMaterial.status,
            "version":                NationalMaterial.version,
            "created_at":             NationalMaterial.created_at,
            "updated_at":             NationalMaterial.updated_at,
        }
        col = col_map.get(sort_by, NationalMaterial.created_at)
        q = q.order_by(col.asc() if sort_dir == "asc" else col.desc())
        return q.offset(offset).limit(limit).all(), total

    def get_audit_history(self, national_material_id: str, limit: int = 50) -> List[AuditLog]:
        return (
            self.db.query(AuditLog)
            .filter(
                AuditLog.entity_type == "NATIONAL_MATERIAL",
                AuditLog.entity_id == national_material_id,
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )

    # ── Create ────────────────────────────────────────────────────────────────

    def create(
        self,
        canonical_description: str,
        classification_id: Optional[str],
        canonical_uom: Optional[str],
        attributes: Optional[Dict[str, Any]],
        provenance: Optional[Dict[str, Any]],
        created_by: Optional[str],
        national_material_code: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> NationalMaterial:
        if national_material_code:
            code = national_material_code.strip()
            if self.get_by_code(code):
                raise ValueError(f"National material code '{code}' already exists.")
        else:
            class_code = "UNK"
            if classification_id:
                cl = self.db.query(Classification).filter(Classification.classification_id == classification_id).first()
                if cl and cl.code:
                    class_code = cl.code.upper()

            max_code = (
                self.db.query(func.max(NationalMaterial.national_material_code))
                .filter(NationalMaterial.national_material_code.like(f"NAT-{class_code}-%"))
                .scalar()
            )
            if max_code:
                try:
                    seq = int(max_code.split("-")[-1]) + 1
                except ValueError:
                    seq = 1
            else:
                seq = 1

            code = f"NAT-{class_code}-{seq:06d}"
            while self.get_by_code(code):
                seq += 1
                code = f"NAT-{class_code}-{seq:06d}"

        nm = NationalMaterial(
            national_material_id=_new_id(),
            national_material_code=code,
            canonical_description=canonical_description,
            classification_id=classification_id,
            canonical_uom=canonical_uom,
            attributes=attributes or {},
            provenance=provenance or {},
            created_by=created_by,
            status="PROVISIONAL",
            version=1,
        )
        self.db.add(nm)
        self.db.flush()

        _audit(
            self.db,
            action="NATIONAL_MATERIAL_CREATED",
            entity_id=nm.national_material_id,
            actor_id=created_by,
            new_value={
                "code": code,
                "description": canonical_description,
                "status": "PROVISIONAL",
            },
            request_id=request_id,
        )
        return nm

    # ── Update ────────────────────────────────────────────────────────────────

    def update(
        self,
        nm: NationalMaterial,
        *,
        canonical_description: Optional[str] = None,
        classification_id: Optional[str] = None,
        canonical_uom: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        provenance: Optional[Dict[str, Any]] = None,
        editor_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> NationalMaterial:
        if nm.is_retired or nm.status == "RETIRED":
            raise ValueError("Cannot edit a RETIRED national material.")

        old = {
            "canonical_description": nm.canonical_description,
            "classification_id": nm.classification_id,
            "canonical_uom": nm.canonical_uom,
            "attributes": nm.attributes,
            "status": nm.status,
            "version": nm.version,
        }
        changes: Dict[str, Any] = {}

        if canonical_description is not None:
            nm.canonical_description = canonical_description
            changes["canonical_description"] = canonical_description
        if classification_id is not None:
            nm.classification_id = classification_id
            changes["classification_id"] = classification_id
        if canonical_uom is not None:
            nm.canonical_uom = canonical_uom
            changes["canonical_uom"] = canonical_uom
        if attributes is not None:
            nm.attributes = attributes
            changes["attributes"] = attributes
        if provenance is not None:
            nm.provenance = provenance
            changes["provenance"] = provenance

        if changes:
            nm.version += 1
            changes["version"] = nm.version
            self.db.flush()
            _audit(
                self.db,
                action="NATIONAL_MATERIAL_UPDATED",
                entity_id=nm.national_material_id,
                actor_id=editor_id,
                old_value=old,
                new_value=changes,
                request_id=request_id,
            )
        return nm

    # ── Status transitions ─────────────────────────────────────────────────────

    def transition_status(
        self,
        nm: NationalMaterial,
        target_status: str,
        actor_id: Optional[str],
        reason: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> NationalMaterial:
        current = nm.status
        allowed = ALLOWED_TRANSITIONS.get(current, set())
        if target_status not in allowed:
            raise ValueError(
                f"Cannot transition '{current}' → '{target_status}'. "
                f"Allowed transitions from '{current}': {sorted(allowed) or ['(none — terminal)']}"
            )

        old_status = nm.status
        nm.status = target_status
        nm.version += 1

        # SoftRetireMixin: set is_retired for RETIRED status
        if target_status == "RETIRED":
            nm.is_retired = True

        self.db.flush()
        _audit(
            self.db,
            action=f"NATIONAL_MATERIAL_{target_status}",
            entity_id=nm.national_material_id,
            actor_id=actor_id,
            old_value={"status": old_status, "version": nm.version - 1},
            new_value={"status": target_status, "version": nm.version, "reason": reason},
            request_id=request_id,
        )
        return nm

    # ── Convenience wrappers ──────────────────────────────────────────────────

    def retire(
        self,
        nm: NationalMaterial,
        actor_id: Optional[str],
        reason: Optional[str] = None,
        superseded_by: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> NationalMaterial:
        # Choose correct terminal status
        target = "SUPERSEDED" if superseded_by else "RETIRED"
        if target == "SUPERSEDED":
            # ACTIVE → SUPERSEDED is allowed
            allowed = ALLOWED_TRANSITIONS.get(nm.status, set())
            if "SUPERSEDED" not in allowed:
                raise ValueError(
                    f"Cannot supersede a material with status '{nm.status}'. "
                    "Only ACTIVE materials can be superseded."
                )
            old_status = nm.status
            nm.status = "SUPERSEDED"
            nm.version += 1
            self.db.flush()
            _audit(
                self.db,
                action="NATIONAL_MATERIAL_SUPERSEDED",
                entity_id=nm.national_material_id,
                actor_id=actor_id,
                old_value={"status": old_status},
                new_value={
                    "status": "SUPERSEDED",
                    "superseded_by": superseded_by,
                    "reason": reason,
                },
                request_id=request_id,
            )
            return nm
        # RETIRED path
        return self.transition_status(
            nm, "RETIRED", actor_id, reason, request_id=request_id
        )
