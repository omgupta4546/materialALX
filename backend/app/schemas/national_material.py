"""
app/schemas/national_material.py — Pydantic schemas for NationalMaterial CRUD + lifecycle.

Governance rule:
    Only authorised mutations (via service) may advance the status.
    Direct writes from the frontend are never accepted.
    Version is server-managed, never client-supplied.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# ── Valid statuses and allowed transitions ────────────────────────────────────
VALID_STATUSES = {
    "PROVISIONAL", "UNDER_REVIEW", "ACTIVE",
    "SUPERSEDED", "RETIRED", "REJECTED",
}

# State machine: which statuses can transition to which
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "PROVISIONAL":   {"UNDER_REVIEW", "REJECTED"},
    "UNDER_REVIEW":  {"ACTIVE", "REJECTED", "PROVISIONAL"},
    "ACTIVE":        {"SUPERSEDED", "RETIRED", "UNDER_REVIEW"},
    "SUPERSEDED":    {"RETIRED"},
    "RETIRED":       set(),       # terminal
    "REJECTED":      {"PROVISIONAL"},   # can be resubmitted
}


# ── Read models ───────────────────────────────────────────────────────────────

class ClassificationBreadcrumb(BaseModel):
    classification_id: str
    code: str
    name: str
    level: int


class NationalMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    national_material_id: str
    national_material_code: str
    canonical_description: str
    classification_id: Optional[str] = None
    canonical_uom: Optional[str] = None
    status: str
    version: int
    provenance: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_retired: bool

    # Enriched (denormalised)
    classification_breadcrumb: List[ClassificationBreadcrumb] = Field(default_factory=list)
    source_count: int = 0
    cpse_count: int = 0
    attributes: Optional[Dict[str, Any]] = None


class NationalMaterialDetail(NationalMaterialRead):
    """Full detail view — adds mappings summary and audit history."""
    mappings_summary: List[Dict[str, Any]] = Field(default_factory=list)
    audit_history: List[Dict[str, Any]] = Field(default_factory=list)


class PaginatedNationalMaterialsFull(BaseModel):
    items: List[NationalMaterialRead]
    total: int
    limit: int
    offset: int
    has_more: bool


# ── Write models ──────────────────────────────────────────────────────────────

class NationalMaterialCreate(BaseModel):
    national_material_code: Optional[str] = None
    canonical_description: str = Field(..., min_length=3, max_length=512)
    classification_id: Optional[str] = None
    canonical_uom: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    created_by: Optional[str] = None


class NationalMaterialUpdate(BaseModel):
    """Only mutable fields — version and status are NOT directly settable."""
    canonical_description: Optional[str] = Field(None, min_length=3, max_length=512)
    classification_id: Optional[str] = None
    canonical_uom: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    provenance: Optional[Dict[str, Any]] = None
    editor_id: Optional[str] = None


class StatusTransitionRequest(BaseModel):
    """Generic body for any status-change action (retire, review, activate, etc.)."""
    reason: Optional[str] = None
    actor_id: Optional[str] = None


class RetireRequest(StatusTransitionRequest):
    superseded_by: Optional[str] = Field(
        None,
        description="national_material_id of the replacement record (when retiring as SUPERSEDED).",
    )
