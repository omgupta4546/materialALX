"""
api/endpoints/feedback.py

Human feedback capture and analytics.

Routes:
  POST /feedback              — capture a reviewer decision
  GET  /feedback              — paginated event list
  GET  /feedback/analytics    — pattern mining (false +/-, disagreement, error rates)
  POST /feedback/nominate     — nominate events for retraining (Engineer+)
  GET  /feedback/candidates   — list retraining candidates (Admin/Engineer)
  POST /feedback/candidates/approve  — ADMIN ONLY: approve candidate set

Governance rules enforced:
  - MatchResult is NEVER mutated here.
  - Retraining candidates can only be approved by ADMIN.
  - Retraining pipeline is NOT triggered automatically; approved candidates
    are simply flagged for a downstream governed pipeline to consume.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, case
from sqlalchemy.orm import Session
from app.api.deps import get_db

from app.auth.rbac import require_role, Roles
from app.core.connection import SessionLocal
from app.models.base import FeedbackEvent, MatchResult, RetrainingCandidate
from app.schemas.feedback import (
    ApproveRetrainingRequest,
    CategoryErrorRate,
    FalseNegativePattern,
    FalsePositivePattern,
    FeedbackAnalytics,
    FeedbackEventCreate,
    FeedbackEventRead,
    FeedbackSummary,
    ModelDisagreementRow,
    NominateForRetrainingRequest,
    RetrainingCandidateRead,
)

router = APIRouter(tags=["Feedback"])

ALL_ROLES      = [Roles.ADMIN, Roles.ENGINEER, Roles.DATA_STEWARD, Roles.AUDITOR, Roles.CPSE_USER]
WRITE_ROLES    = [Roles.ADMIN, Roles.ENGINEER, Roles.DATA_STEWARD]
NOMINATE_ROLES = [Roles.ADMIN, Roles.ENGINEER]
ADMIN_ONLY     = [Roles.ADMIN]





def _score_to_band(score: Optional[float]) -> str:
    if score is None:
        return "unknown"
    if score >= 0.95:
        return "0.95–1.0"
    if score >= 0.85:
        return "0.85–0.95"
    if score >= 0.65:
        return "0.65–0.85"
    if score >= 0.50:
        return "0.50–0.65"
    return "below–0.50"


def _is_disagreement(event_type: str, ai_recommendation: Optional[str]) -> bool:
    """
    Disagreement means the human decision contradicts the AI recommendation.
    APPROVED vs REQUIRES_REVIEW  → disagreement
    REJECTED vs high ai score / APPROVE recommendation → disagreement
    """
    if not ai_recommendation:
        return False
    human_approved = event_type == "APPROVED"
    human_rejected = event_type in ("REJECTED", "ENGINEERING_REVIEW")
    ai_approved = ai_recommendation in ("APPROVE", "AUTO_APPROVE")

    return (human_approved and not ai_approved) or (human_rejected and ai_approved)


# ──────────────────────────────────────────────────────────────────────────────
# Capture
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=FeedbackEventRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(WRITE_ROLES))],
    summary="Capture a reviewer decision",
)
def capture_feedback(
    payload: FeedbackEventCreate,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role(WRITE_ROLES)),
):
    """
    Record a human reviewer's decision for a MatchResult.
    - AI outputs in MatchResult are NEVER modified.
    - Computes is_disagreement automatically.
    """
    # If match_id given, cross-check it exists
    match_snapshot: Optional[MatchResult] = None
    if payload.match_id:
        match_snapshot = db.query(MatchResult).filter(
            MatchResult.match_id == payload.match_id
        ).first()
        if not match_snapshot:
            raise HTTPException(status_code=404, detail=f"MatchResult {payload.match_id} not found")

    # Use AI snapshot from payload (caller copies from MatchResult before sending)
    # This preserves the values at the time of review, even if MatchResult is later
    # replaced by a new model run.
    disagreement = _is_disagreement(payload.event_type, payload.ai_recommendation)

    event = FeedbackEvent(
        event_id=str(uuid.uuid4()),
        reviewer_id=current_user.get("user_id"),
        match_id=payload.match_id,
        target_id=payload.target_id or payload.match_id,
        target_type=payload.target_type,
        event_type=payload.event_type,
        human_decision=payload.event_type,
        reason=payload.reason,
        corrected_attributes=payload.corrected_attributes,
        ai_match_type=payload.ai_match_type,
        ai_final_score=payload.ai_final_score,
        ai_risk_level=payload.ai_risk_level,
        ai_recommendation=payload.ai_recommendation,
        ai_model_version=payload.ai_model_version,
        ai_prompt_version=payload.ai_prompt_version,
        ai_rules_version=payload.ai_rules_version,
        category_code=payload.category_code,
        source_material_id=payload.source_material_id,
        is_disagreement=disagreement,
        feedback_data={},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


# ──────────────────────────────────────────────────────────────────────────────
# Read
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=List[FeedbackEventRead],
    dependencies=[Depends(require_role(ALL_ROLES))],
    summary="List feedback events (paginated)",
)
def list_feedback(
    event_type: Optional[str] = None,
    category_code: Optional[str] = None,
    is_disagreement: Optional[bool] = None,
    model_version: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    q = db.query(FeedbackEvent)
    if event_type:
        q = q.filter(FeedbackEvent.event_type == event_type)
    if category_code:
        q = q.filter(FeedbackEvent.category_code == category_code.upper())
    if is_disagreement is not None:
        q = q.filter(FeedbackEvent.is_disagreement == is_disagreement)
    if model_version:
        q = q.filter(FeedbackEvent.ai_model_version == model_version)
    return q.order_by(FeedbackEvent.created_at.desc()).offset(offset).limit(limit).all()


# ──────────────────────────────────────────────────────────────────────────────
# Analytics
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/analytics",
    response_model=FeedbackAnalytics,
    dependencies=[Depends(require_role(ALL_ROLES))],
    summary="Feedback analytics — patterns, disagreement rates, category errors",
)
def feedback_analytics(db: Session = Depends(get_db)):

    # ── Summary counts ────────────────────────────────────────────────────────
    total = db.query(func.count(FeedbackEvent.event_id)).scalar() or 0
    approved = db.query(func.count(FeedbackEvent.event_id)).filter(FeedbackEvent.event_type == "APPROVED").scalar() or 0
    rejected = db.query(func.count(FeedbackEvent.event_id)).filter(FeedbackEvent.event_type == "REJECTED").scalar() or 0
    eng_review = db.query(func.count(FeedbackEvent.event_id)).filter(FeedbackEvent.event_type == "ENGINEERING_REVIEW").scalar() or 0
    attr_corrected = db.query(func.count(FeedbackEvent.event_id)).filter(FeedbackEvent.event_type == "ATTRIBUTE_CORRECTED").scalar() or 0
    disagreements = db.query(func.count(FeedbackEvent.event_id)).filter(FeedbackEvent.is_disagreement == True).scalar() or 0

    summary = FeedbackSummary(
        total_events=total,
        approved=approved,
        rejected=rejected,
        engineering_review=eng_review,
        attribute_corrected=attr_corrected,
        disagreement_count=disagreements,
        disagreement_rate=round(disagreements / total, 4) if total else 0.0,
    )

    # ── Category error rates ──────────────────────────────────────────────────
    cat_rows = (
        db.query(
            FeedbackEvent.category_code,
            func.count(FeedbackEvent.event_id).label("total"),
            func.sum(
                case((FeedbackEvent.event_type.in_(["REJECTED", "ENGINEERING_REVIEW"]), 1), else_=0)
            ).label("rejected"),
        )
        .filter(FeedbackEvent.category_code.isnot(None))
        .group_by(FeedbackEvent.category_code)
        .order_by(func.count(FeedbackEvent.event_id).desc())
        .limit(20)
        .all()
    )
    category_error_rates = [
        CategoryErrorRate(
            category_code=r.category_code,
            total_reviews=r.total,
            rejected_count=r.rejected,
            error_rate=round((r.rejected or 0) / r.total, 4) if r.total else 0.0,
        )
        for r in cat_rows
    ]

    # ── False positives: AI said APPROVE but human REJECTED ───────────────────
    fp_rows = (
        db.query(
            FeedbackEvent.ai_match_type,
            FeedbackEvent.ai_final_score,
            FeedbackEvent.category_code,
            func.count(FeedbackEvent.event_id).label("count"),
        )
        .filter(
            FeedbackEvent.event_type.in_(["REJECTED", "ENGINEERING_REVIEW"]),
            FeedbackEvent.ai_recommendation.in_(["APPROVE", "AUTO_APPROVE"]),
        )
        .group_by(
            FeedbackEvent.ai_match_type,
            FeedbackEvent.ai_final_score,
            FeedbackEvent.category_code,
        )
        .order_by(func.count(FeedbackEvent.event_id).desc())
        .limit(20)
        .all()
    )
    false_positive_patterns = [
        FalsePositivePattern(
            ai_match_type=r.ai_match_type,
            ai_score_band=_score_to_band(r.ai_final_score),
            category_code=r.category_code,
            count=r.count,
        )
        for r in fp_rows
    ]

    # ── False negatives: AI flagged REVIEW but human APPROVED ────────────────
    fn_rows = (
        db.query(
            FeedbackEvent.ai_match_type,
            FeedbackEvent.ai_final_score,
            FeedbackEvent.category_code,
            func.count(FeedbackEvent.event_id).label("count"),
        )
        .filter(
            FeedbackEvent.event_type == "APPROVED",
            FeedbackEvent.ai_recommendation.in_(["REQUIRES_REVIEW", "DOWNGRADE_TO_REVIEW"]),
        )
        .group_by(
            FeedbackEvent.ai_match_type,
            FeedbackEvent.ai_final_score,
            FeedbackEvent.category_code,
        )
        .order_by(func.count(FeedbackEvent.event_id).desc())
        .limit(20)
        .all()
    )
    false_negative_patterns = [
        FalseNegativePattern(
            ai_match_type=r.ai_match_type,
            ai_score_band=_score_to_band(r.ai_final_score),
            category_code=r.category_code,
            count=r.count,
        )
        for r in fn_rows
    ]

    # ── Model disagreement rates by model version ─────────────────────────────
    mv_rows = (
        db.query(
            FeedbackEvent.ai_model_version,
            func.count(FeedbackEvent.event_id).label("total"),
            func.sum(
                case((FeedbackEvent.is_disagreement == True, 1), else_=0)
            ).label("disagreements"),
        )
        .group_by(FeedbackEvent.ai_model_version)
        .order_by(func.count(FeedbackEvent.event_id).desc())
        .all()
    )
    model_disagreement = [
        ModelDisagreementRow(
            ai_model_version=r.ai_model_version,
            total_reviewed=r.total,
            disagreements=r.disagreements or 0,
            disagreement_rate=round((r.disagreements or 0) / r.total, 4) if r.total else 0.0,
        )
        for r in mv_rows
    ]

    return FeedbackAnalytics(
        summary=summary,
        category_error_rates=category_error_rates,
        false_positive_patterns=false_positive_patterns,
        false_negative_patterns=false_negative_patterns,
        model_disagreement=model_disagreement,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Retraining governance (NEVER auto-runs training)
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/nominate",
    response_model=RetrainingCandidateRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(NOMINATE_ROLES))],
    summary="Nominate a feedback event for the retraining pipeline",
)
def nominate_for_retraining(
    payload: NominateForRetrainingRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role(NOMINATE_ROLES)),
):
    """
    Creates a PENDING retraining candidate.
    ADMIN must separately approve before any training pipeline sees it.
    """
    event = db.query(FeedbackEvent).filter(FeedbackEvent.event_id == payload.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Feedback event not found")

    # Prevent duplicate nominations
    existing = db.query(RetrainingCandidate).filter(
        RetrainingCandidate.event_id == payload.event_id,
        RetrainingCandidate.status == "PENDING",
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="This event is already nominated and pending.")

    candidate = RetrainingCandidate(
        candidate_id=str(uuid.uuid4()),
        event_id=payload.event_id,
        nominated_by=current_user.get("user_id"),
        nomination_note=payload.nomination_note,
        status="PENDING",
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    return candidate


@router.get(
    "/candidates",
    response_model=List[RetrainingCandidateRead],
    dependencies=[Depends(require_role(NOMINATE_ROLES))],
    summary="List retraining candidates",
)
def list_retraining_candidates(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(RetrainingCandidate)
    if status_filter:
        q = q.filter(RetrainingCandidate.status == status_filter)
    return q.order_by(RetrainingCandidate.created_at.desc()).limit(200).all()


@router.post(
    "/candidates/approve",
    dependencies=[Depends(require_role(ADMIN_ONLY))],
    summary="[ADMIN] Approve retraining candidates — does NOT trigger training automatically",
)
def approve_retraining_candidates(
    payload: ApproveRetrainingRequest,
    db: Session = Depends(get_db),
    current_user: Dict[str, Any] = Depends(require_role(ADMIN_ONLY)),
):
    """
    Marks selected candidates as APPROVED_FOR_TRAINING.

    IMPORTANT: This does NOT automatically retrain production models.
    A separate, explicitly governed pipeline must be triggered by an operator
    to consume these approved candidates.
    """
    approved = []
    not_found = []

    for cid in payload.candidate_ids:
        candidate = db.query(RetrainingCandidate).filter(
            RetrainingCandidate.candidate_id == cid,
            RetrainingCandidate.status == "PENDING",
        ).first()
        if not candidate:
            not_found.append(cid)
            continue
        candidate.status = "APPROVED_FOR_TRAINING"
        candidate.approved_by = current_user.get("user_id")
        candidate.approved_at = datetime.utcnow()
        approved.append(cid)

    db.commit()
    return {
        "approved": approved,
        "not_found": not_found,
        "message": (
            f"{len(approved)} candidate(s) approved for future training. "
            "No model retraining has been triggered. "
            "An operator must explicitly run the governed retraining pipeline."
        ),
    }
