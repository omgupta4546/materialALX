"""
app/schemas/match.py — Pydantic schemas for MatchResult, Approval, and MaterialMapping.

Design rule:
    - AI-generated fields (scores, evidence, recommendation) are READ-ONLY.
    - Human decisions (Approval) are separate write models.
    - MatchResult is NEVER mutated by human action.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# APPROVAL (human decision)
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    approval_id: str
    match_id: str
    reviewer_id: Optional[str]
    decision: Literal["APPROVED", "REJECTED", "ESCALATED"]
    comment: Optional[str]
    review_type: Optional[str]
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# MATCH RESULT — list + detail
# ─────────────────────────────────────────────────────────────────────────────

class MatchSummary(BaseModel):
    """Lightweight list-view item — no heavy evidence blobs."""
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    material_a_id: str
    material_b_id: str
    final_score: Optional[float]
    semantic_score: Optional[float]
    attribute_score: Optional[float]
    rule_score: Optional[float]
    match_type: Optional[str]
    recommendation: Optional[str]
    risk_level: Optional[str]
    requires_human_review: bool
    model_version: Optional[str]
    created_at: datetime

    # Denormalised human-decision layer
    decision: Optional[Literal["APPROVED", "REJECTED", "ESCALATED"]] = None
    review_type: Optional[str] = None
    reviewer_id: Optional[str] = None
    decided_at: Optional[datetime] = None


class MaterialSnapshot(BaseModel):
    """Compact snapshot of one side of a match."""
    source_material_id: Optional[str] = None
    cpse_id: Optional[str] = None
    legacy_material_code: Optional[str] = None
    raw_description: Optional[str] = None
    raw_uom: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    # from NormalizedMaterial
    normalized_description: Optional[str] = None
    canonical_uom: Optional[str] = None
    classification_id: Optional[str] = None
    confidence: Optional[float] = None
    # from NationalMaterial
    national_material_id: Optional[str] = None
    national_material_code: Optional[str] = None
    national_description: Optional[str] = None


class MatchDetail(MatchSummary):
    """Full detail — includes evidence and review history."""
    positive_evidence: Dict[str, Any] = Field(default_factory=dict)
    negative_evidence: Dict[str, Any] = Field(default_factory=dict)
    conflicts: Dict[str, Any] = Field(default_factory=dict)
    prompt_version: Optional[str] = None
    rules_version: Optional[str] = None

    material_a: Optional[MaterialSnapshot] = None
    material_b: Optional[MaterialSnapshot] = None

    review_history: List[ApprovalRead] = Field(default_factory=list)


class PaginatedMatches(BaseModel):
    items: List[MatchSummary]
    total: int
    limit: int
    offset: int
    has_more: bool


# ─────────────────────────────────────────────────────────────────────────────
# ACTION REQUEST  (human decisions — sent TO the API)
# ─────────────────────────────────────────────────────────────────────────────

class ReviewActionRequest(BaseModel):
    reviewer_id: Optional[str] = Field(None, description="Overrides authenticated user (for dev/testing)")
    comment: Optional[str] = None
    review_type: Optional[str] = None


class ReviewActionResponse(BaseModel):
    match_id: str
    approval_id: str
    decision: str
    reviewer_id: str
    comment: Optional[str]
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL MAPPING
# ─────────────────────────────────────────────────────────────────────────────

class MappingCreate(BaseModel):
    source_material_id: str
    national_material_id: str
    mapping_type: Literal[
        "EXACT_DUPLICATE", "NEAR_DUPLICATE",
        "FUNCTIONALLY_EQUIVALENT", "LEGACY_MAPPING"
    ]
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    notes: Optional[str] = None


class MappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    mapping_id: str
    source_material_id: str
    national_material_id: str
    mapping_type: str
    confidence: Optional[float]
    status: str
    created_by: Optional[str]
    approved_by: Optional[str]
    approved_at: Optional[datetime]
    notes: Optional[str]
    is_ai_suggested: bool
    created_at: datetime
    updated_at: datetime

    # Denormalised for convenience
    national_material_code: Optional[str] = None
    legacy_material_code: Optional[str] = None


class PaginatedMappings(BaseModel):
    items: List[MappingRead]
    total: int
    limit: int
    offset: int
    has_more: bool
