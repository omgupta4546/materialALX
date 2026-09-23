"""
Mappings endpoints.

Routes:
    POST /api/v1/mappings
    GET  /api/v1/mappings
    GET  /api/v1/mappings/{id}
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.match import MappingCreate, MappingRead, PaginatedMappings
from app.services.match_service import MatchService

log = logging.getLogger(__name__)
router = APIRouter()


def _svc(db: Session = Depends(get_db)) -> MatchService:
    return MatchService(db)


@router.post("", response_model=MappingRead, status_code=201, summary="Create a manual source→national mapping")
def create_mapping(
    body: MappingCreate,
    created_by: str = Query("SYSTEM", description="User ID of the creator (dev param; use auth in prod)"),
    svc: MatchService = Depends(_svc),
) -> MappingRead:
    return svc.create_mapping(body=body, created_by=created_by, user=None)


@router.get("", response_model=PaginatedMappings, summary="List material mappings with optional filters")
def list_mappings(
    source_material_id: Optional[str] = Query(None),
    national_material_id: Optional[str] = Query(None),
    mapping_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: Literal["created_at", "confidence", "status", "mapping_type"] = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: MatchService = Depends(_svc),
) -> PaginatedMappings:
    return svc.list_mappings(
        source_material_id=source_material_id,
        national_material_id=national_material_id,
        mapping_type=mapping_type,
        status=status,
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )


@router.get("/{mapping_id}", response_model=MappingRead, summary="Get a single mapping by ID")
def get_mapping(
    mapping_id: str,
    svc: MatchService = Depends(_svc),
) -> MappingRead:
    return svc.get_mapping(mapping_id)
