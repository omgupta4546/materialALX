"""
National materials CRUD + lifecycle endpoints.

Routes:
    GET    /api/v1/national-materials              → list / filter
    POST   /api/v1/national-materials              → create (starts PROVISIONAL)
    GET    /api/v1/national-materials/search       → keyword + facet search
    GET    /api/v1/national-materials/{id}         → full detail + audit history
    PUT    /api/v1/national-materials/{id}         → update mutable fields
    POST   /api/v1/national-materials/{id}/retire  → retire or supersede
    POST   /api/v1/national-materials/{id}/submit  → PROVISIONAL → UNDER_REVIEW
    POST   /api/v1/national-materials/{id}/approve → UNDER_REVIEW → ACTIVE
    POST   /api/v1/national-materials/{id}/reject  → any → REJECTED

Governance:
    - Status transitions validated by state machine in service/repo.
    - Version is server-managed — never accepted from clients.
    - RETIRED records are immutable.
    - Every mutation creates an AuditLog entry.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.national_material import (
    NationalMaterialCreate,
    NationalMaterialDetail,
    NationalMaterialRead,
    NationalMaterialUpdate,
    PaginatedNationalMaterialsFull,
    RetireRequest,
    StatusTransitionRequest,
)
from app.services.national_material_service import NationalMaterialService

log = logging.getLogger(__name__)

router = APIRouter()
class_router = APIRouter()          # kept separate for /classifications prefix


def _svc(db: Session = Depends(get_db)) -> NationalMaterialService:
    return NationalMaterialService(db)


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedNationalMaterialsFull,
    summary="List national materials with filtering and pagination",
)
def list_national_materials(
    q: Optional[str] = Query(None, description="Keyword across description and code"),
    classification_id: Optional[str] = Query(None),
    canonical_uom: Optional[str] = Query(None),
    status: Optional[str] = Query(
        None,
        description="PROVISIONAL | UNDER_REVIEW | ACTIVE | SUPERSEDED | RETIRED | REJECTED",
    ),
    include_retired: bool = Query(False),
    sort_by: Literal[
        "national_material_code", "canonical_description",
        "status", "version", "created_at", "updated_at"
    ] = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: NationalMaterialService = Depends(_svc),
) -> PaginatedNationalMaterialsFull:
    return svc.list(
        keyword=q,
        classification_id=classification_id,
        canonical_uom=canonical_uom,
        status=status,
        include_retired=include_retired,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/search",
    response_model=PaginatedNationalMaterialsFull,
    summary="Search national materials (keyword + facets)",
)
def search_national_materials(
    q: Optional[str] = Query(None),
    classification_id: Optional[str] = Query(None),
    canonical_uom: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: NationalMaterialService = Depends(_svc),
) -> PaginatedNationalMaterialsFull:
    return svc.list(
        keyword=q,
        classification_id=classification_id,
        canonical_uom=canonical_uom,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{national_material_id}",
    response_model=NationalMaterialDetail,
    summary="Get full detail for a national material including audit history",
)
def get_national_material(
    national_material_id: str,
    svc: NationalMaterialService = Depends(_svc),
) -> NationalMaterialDetail:
    return svc.get(national_material_id)


# ─────────────────────────────────────────────────────────────────────────────
# WRITE
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=NationalMaterialRead,
    status_code=201,
    summary="Create a new national material (starts PROVISIONAL)",
)
def create_national_material(
    body: NationalMaterialCreate,
    svc: NationalMaterialService = Depends(_svc),
) -> NationalMaterialRead:
    return svc.create(body)


@router.put(
    "/{national_material_id}",
    response_model=NationalMaterialRead,
    summary="Update mutable fields of a national material (auto-increments version)",
)
def update_national_material(
    national_material_id: str,
    body: NationalMaterialUpdate,
    svc: NationalMaterialService = Depends(_svc),
) -> NationalMaterialRead:
    return svc.update(national_material_id, body)


# ─────────────────────────────────────────────────────────────────────────────
# LIFECYCLE TRANSITIONS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{national_material_id}/retire",
    response_model=NationalMaterialRead,
    summary="Retire or supersede a national material (terminal for RETIRED; reversible for SUPERSEDED)",
)
def retire_national_material(
    national_material_id: str,
    body: RetireRequest,
    svc: NationalMaterialService = Depends(_svc),
) -> NationalMaterialRead:
    return svc.retire(national_material_id, body)


@router.post(
    "/{national_material_id}/submit",
    response_model=NationalMaterialRead,
    summary="Submit for review: PROVISIONAL → UNDER_REVIEW",
)
def submit_for_review(
    national_material_id: str,
    body: StatusTransitionRequest,
    svc: NationalMaterialService = Depends(_svc),
) -> NationalMaterialRead:
    return svc.transition(national_material_id, "UNDER_REVIEW", body)


@router.post(
    "/{national_material_id}/approve",
    response_model=NationalMaterialRead,
    summary="Approve: UNDER_REVIEW → ACTIVE",
)
def approve_national_material(
    national_material_id: str,
    body: StatusTransitionRequest,
    svc: NationalMaterialService = Depends(_svc),
) -> NationalMaterialRead:
    return svc.transition(national_material_id, "ACTIVE", body)


@router.post(
    "/{national_material_id}/reject",
    response_model=NationalMaterialRead,
    summary="Reject: PROVISIONAL or UNDER_REVIEW → REJECTED",
)
def reject_national_material(
    national_material_id: str,
    body: StatusTransitionRequest,
    svc: NationalMaterialService = Depends(_svc),
) -> NationalMaterialRead:
    return svc.transition(national_material_id, "REJECTED", body)


# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICATIONS  (existing sub-resource)
# ─────────────────────────────────────────────────────────────────────────────

from app.models.base import Classification as ClassificationModel  # noqa: E402


@class_router.get("", summary="List all classifications")
def list_classifications(db: Session = Depends(get_db)):
    rows = (
        db.query(ClassificationModel)
        .order_by(ClassificationModel.level, ClassificationModel.code)
        .all()
    )
    return [
        {
            "classification_id": r.classification_id,
            "code": r.code,
            "name": r.name,
            "parent_id": r.parent_id,
            "level": r.level,
            "description": getattr(r, "description", None),
        }
        for r in rows
    ]
