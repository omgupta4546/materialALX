"""
schemas/feedback.py

Pydantic schemas for human feedback capture and analytics read-back.

Governance rule enforced here:
  - Retraining nominations return a PENDING candidate — never auto-approved.
  - corrected_attributes is only accepted for ATTRIBUTE_CORRECTED events.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

VALID_EVENT_TYPES = {"APPROVED", "REJECTED", "ENGINEERING_REVIEW", "ATTRIBUTE_CORRECTED"}
VALID_RETRAIN_STATUS = {"PENDING", "APPROVED_FOR_TRAINING", "EXCLUDED"}


# ──────────────────────────────────────────────────────────────────────────────
# Feedback capture
# ──────────────────────────────────────────────────────────────────────────────

class FeedbackEventCreate(BaseModel):
    """
    Posted by the UI whenever a reviewer takes an action.
    The match_id links back to the AI-generated MatchResult (never modified).
    """
    match_id: Optional[str] = None
    target_id: Optional[str] = None
    target_type: str = "MATCH"

    event_type: str = Field(..., description="APPROVED | REJECTED | ENGINEERING_REVIEW | ATTRIBUTE_CORRECTED")
    reason: Optional[str] = None

    # Provided when event_type == ATTRIBUTE_CORRECTED
    corrected_attributes: Optional[Dict[str, Any]] = None

    # AI snapshot — caller must pass these from the MatchResult being reviewed
    ai_match_type:      Optional[str]   = None
    ai_final_score:     Optional[float] = None
    ai_risk_level:      Optional[str]   = None
    ai_recommendation:  Optional[str]   = None
    ai_model_version:   Optional[str]   = None
    ai_prompt_version:  Optional[str]   = None
    ai_rules_version:   Optional[str]   = None

    category_code: Optional[str] = None
    source_material_id: Optional[str] = None

    @model_validator(mode="after")
    def validate_event(self) -> "FeedbackEventCreate":
        if self.event_type not in VALID_EVENT_TYPES:
            raise ValueError(f"event_type must be one of {VALID_EVENT_TYPES}")
        if self.event_type == "ATTRIBUTE_CORRECTED" and not self.corrected_attributes:
            raise ValueError("corrected_attributes must be provided for ATTRIBUTE_CORRECTED events")
        if not self.match_id and not self.target_id:
            raise ValueError("Either match_id or target_id must be provided")
        return self


class FeedbackEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    reviewer_id: Optional[str] = None
    match_id: Optional[str] = None
    target_id: Optional[str] = None
    target_type: Optional[str] = None

    event_type: str
    human_decision: Optional[str] = None
    reason: Optional[str] = None
    corrected_attributes: Optional[Dict[str, Any]] = None

    ai_match_type: Optional[str] = None
    ai_final_score: Optional[float] = None
    ai_risk_level: Optional[str] = None
    ai_recommendation: Optional[str] = None
    ai_model_version: Optional[str] = None

    category_code: Optional[str] = None
    is_disagreement: bool = False
    created_at: datetime


# ──────────────────────────────────────────────────────────────────────────────
# Retraining governance
# ──────────────────────────────────────────────────────────────────────────────

class NominateForRetrainingRequest(BaseModel):
    """Admin/Engineer nominates a feedback event for the retraining pipeline."""
    event_id: str
    nomination_note: Optional[str] = None


class RetrainingCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    candidate_id: str
    event_id: str
    nominated_by: Optional[str] = None
    nomination_note: Optional[str] = None
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime


class ApproveRetrainingRequest(BaseModel):
    """ADMIN ONLY: explicitly approves a retraining candidate set."""
    candidate_ids: List[str] = Field(..., min_length=1)
    approval_note: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Analytics schemas
# ──────────────────────────────────────────────────────────────────────────────

class FeedbackSummary(BaseModel):
    total_events: int
    approved: int
    rejected: int
    engineering_review: int
    attribute_corrected: int
    disagreement_count: int
    disagreement_rate: float


class CategoryErrorRate(BaseModel):
    category_code: str
    total_reviews: int
    rejected_count: int
    error_rate: float


class FalsePositivePattern(BaseModel):
    """AI said APPROVE / high-score but human REJECTED."""
    ai_match_type: Optional[str]
    ai_score_band: str        # e.g. "0.85–0.95"
    category_code: Optional[str]
    count: int


class FalseNegativePattern(BaseModel):
    """AI flagged REQUIRES_REVIEW / low score but human APPROVED."""
    ai_match_type: Optional[str]
    ai_score_band: str
    category_code: Optional[str]
    count: int


class ModelDisagreementRow(BaseModel):
    ai_model_version: Optional[str]
    total_reviewed: int
    disagreements: int
    disagreement_rate: float


class FeedbackAnalytics(BaseModel):
    summary: FeedbackSummary
    category_error_rates: List[CategoryErrorRate]
    false_positive_patterns: List[FalsePositivePattern]
    false_negative_patterns: List[FalseNegativePattern]
    model_disagreement: List[ModelDisagreementRow]
