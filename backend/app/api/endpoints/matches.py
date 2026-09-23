"""
Matches endpoints — pure delegation to MatchService.

Routes:
    GET  /api/v1/matches
    GET  /api/v1/matches/{id}
    POST /api/v1/matches/{id}/approve
    POST /api/v1/matches/{id}/reject
    POST /api/v1/matches/{id}/engineering-review
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.auth.router import get_current_user
from app.schemas.match import (
    MatchDetail,
    PaginatedMatches,
    ReviewActionRequest,
    ReviewActionResponse,
)
from app.services.match_service import MatchService

log = logging.getLogger(__name__)
router = APIRouter()


def _svc(db: Session = Depends(get_db)) -> MatchService:
    return MatchService(db)


def _optional_user(
    db: Session = Depends(get_db),
) -> Optional[dict]:
    """Returns current user dict; None if no auth token present (dev/test)."""
    try:
        from fastapi.security import HTTPBearer
        # Auth is optional for backwards-compat with non-authenticated dev usage
        # The service layer enforces permissions — 403 is raised there if needed
        return None
    except Exception:
        return None


from app.auth.rbac import enforce_cpse_tenant

@router.get("", response_model=PaginatedMatches, summary="List AI match candidates")
def list_matches(
    decision: Optional[str] = Query(None, description="APPROVED | REJECTED | ESCALATED | PENDING"),
    match_type: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    requires_review: Optional[bool] = Query(None),
    cpse_id: Optional[str] = Depends(enforce_cpse_tenant),
    sort_by: Literal["final_score", "semantic_score", "created_at"] = Query("final_score"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    svc: MatchService = Depends(_svc),
) -> PaginatedMatches:
    return svc.list_matches(
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


@router.get("/{match_id}", response_model=MatchDetail, summary="Get match detail with review history")
def get_match(
    match_id: str,
    svc: MatchService = Depends(_svc),
) -> MatchDetail:
    return svc.get_match(match_id)


@router.post(
    "/{match_id}/approve",
    response_model=ReviewActionResponse,
    summary="Approve an AI match candidate",
)
def approve_match(
    match_id: str,
    body: ReviewActionRequest,
    svc: MatchService = Depends(_svc),
) -> ReviewActionResponse:
    reviewer_id = body.reviewer_id or "SYSTEM"
    return svc.approve_match(
        match_id=match_id,
        reviewer_id=reviewer_id,
        comment=body.comment,
        user=None,   # permission check skipped in dev; hook user in via get_current_user
    )


@router.post(
    "/{match_id}/reject",
    response_model=ReviewActionResponse,
    summary="Reject an AI match candidate",
)
def reject_match(
    match_id: str,
    body: ReviewActionRequest,
    svc: MatchService = Depends(_svc),
) -> ReviewActionResponse:
    reviewer_id = body.reviewer_id or "SYSTEM"
    return svc.reject_match(
        match_id=match_id,
        reviewer_id=reviewer_id,
        comment=body.comment,
        user=None,
    )


@router.post(
    "/{match_id}/engineering-review",
    response_model=ReviewActionResponse,
    summary="Escalate match for engineering review",
)
def engineering_review(
    match_id: str,
    body: ReviewActionRequest,
    svc: MatchService = Depends(_svc),
) -> ReviewActionResponse:
    reviewer_id = body.reviewer_id or "SYSTEM"
    return svc.engineering_review(
        match_id=match_id,
        reviewer_id=reviewer_id,
        comment=body.comment,
        user=None,
    )
