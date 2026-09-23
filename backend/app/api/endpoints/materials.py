"""
Materials endpoints — all routes delegate 100% to MaterialService.

Routes:
    GET /api/v1/materials               → list / filter source materials
    GET /api/v1/materials/search        → keyword + facet search
    GET /api/v1/materials/{id}          → detail view
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.auth.rbac import enforce_cpse_tenant
from app.schemas.material import (
    PaginatedSourceMaterials,
    SourceMaterialDetail,
)
from app.services.material_service import MaterialService

log = logging.getLogger(__name__)
router = APIRouter()


def _svc(db: Session = Depends(get_db)) -> MaterialService:
    return MaterialService(db)


# ─────────────────────────────────────────────────────────────────────────────
# SHARED QUERY PARAMS
# ─────────────────────────────────────────────────────────────────────────────

def _common_filters(
    q: Optional[str]   = Query(None, description="Keyword across description, code, MPN, manufacturer"),
    legacy_code: Optional[str] = Query(None, alias="legacy_code", description="Partial match on legacy material code"),
    mpn: Optional[str] = Query(None, description="Partial match on manufacturer part number"),
    manufacturer: Optional[str] = Query(None, description="Partial match on manufacturer name"),
    cpse_id: Optional[str] = Depends(enforce_cpse_tenant),
    raw_category: Optional[str] = Query(None, description="Filter by raw category or classification code"),
    raw_uom: Optional[str] = Query(None, description="Filter by UOM (raw or canonical)"),
    classification_id: Optional[str] = Query(None, description="Filter by classification UUID"),
    mapping_status: Optional[Literal["MAPPED", "UNMAPPED"]] = Query(None),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    semantic: bool = Query(False, description="Enable semantic search (requires embeddings)"),
):
    return dict(
        keyword=q,
        legacy_code=legacy_code,
        mpn=mpn,
        manufacturer=manufacturer,
        cpse_id=cpse_id,
        raw_category=raw_category,
        raw_uom=raw_uom,
        classification_id=classification_id,
        mapping_status=mapping_status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
        semantic=semantic,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedSourceMaterials,
    summary="List source materials with filtering and pagination",
)
def list_materials(
    filters: dict = Depends(_common_filters),
    svc: MaterialService = Depends(_svc),
) -> PaginatedSourceMaterials:
    return svc.list_materials(**filters)


@router.get(
    "/search",
    response_model=PaginatedSourceMaterials,
    summary="Search source materials (keyword + facets + optional semantic)",
    description=(
        "Identical to GET /materials but semantically named for search-heavy clients. "
        "Pass ?semantic=true to activate vector search (requires embeddings in DB)."
    ),
)
def search_materials(
    filters: dict = Depends(_common_filters),
    svc: MaterialService = Depends(_svc),
) -> PaginatedSourceMaterials:
    return svc.list_materials(**filters)


@router.get(
    "/{source_material_id}",
    response_model=SourceMaterialDetail,
    summary="Get full detail for a single source material",
)
def get_material(
    source_material_id: str,
    svc: MaterialService = Depends(_svc),
) -> SourceMaterialDetail:
    return svc.get_material(source_material_id)
