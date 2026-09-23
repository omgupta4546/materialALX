"""
app/schemas/material.py — Pydantic schemas for SourceMaterial and NationalMaterial search.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# SOURCE MATERIAL  (immutable ingestion record)
# ─────────────────────────────────────────────────────────────────────────────

class SourceMaterialSummary(BaseModel):
    """Lightweight list-view item."""
    model_config = ConfigDict(from_attributes=True)

    source_material_id: str
    cpse_id: str
    legacy_material_code: str
    raw_description: Optional[str] = None
    raw_uom: Optional[str] = None
    raw_category: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    plant: Optional[str] = None
    source_system: Optional[str] = None
    source_file: Optional[str] = None
    created_at: datetime

    # Denormalised from joins — may be null if not yet normalised/mapped
    normalized_description: Optional[str] = None
    canonical_uom: Optional[str] = None
    classification_id: Optional[str] = None
    normalization_version: Optional[str] = None
    confidence: Optional[float] = None
    national_material_id: Optional[str] = None
    national_material_code: Optional[str] = None
    mapping_status: Literal["MAPPED", "UNMAPPED"] = "UNMAPPED"
    mapping_type: Optional[str] = None

    # Semantic-search hook
    semantic_score: Optional[float] = None    # populated when semantic search is active


class AuditEvent(BaseModel):
    action: str
    user_id: Optional[str] = None
    timestamp: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SourceMaterialDetail(SourceMaterialSummary):
    """Full detail view — superset of summary."""
    raw_specification: Optional[str] = None
    source_record_reference: Optional[str] = None
    # NormalizedMaterial fields
    normalized_manufacturer: Optional[str] = None
    normalized_mpn: Optional[str] = None
    normalization_method: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    embedding_ready: bool = False
    # Relationship summaries
    national_description: Optional[str] = None
    # Audit history — populated from Approval/ProcessingJob events where available
    audit_history: List[AuditEvent] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# NATIONAL MATERIAL  (golden record)
# ─────────────────────────────────────────────────────────────────────────────

class NationalMaterialSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    national_material_id: str
    national_material_code: str
    canonical_description: str
    classification_id: Optional[str] = None
    canonical_uom: Optional[str] = None
    status: str
    version: int
    created_at: datetime
    updated_at: datetime

    # Aggregates
    source_count: int = 0         # how many source materials map to this
    cpse_count: int = 0           # unique CPSEs

    # Semantic search hook
    semantic_score: Optional[float] = None


# ─────────────────────────────────────────────────────────────────────────────
# SHARED RESPONSE ENVELOPES
# ─────────────────────────────────────────────────────────────────────────────

class PaginatedSourceMaterials(BaseModel):
    items: List[SourceMaterialSummary]
    total: int
    limit: int
    offset: int
    has_more: bool
    # Search metadata
    search_mode: Literal["keyword", "semantic", "none"] = "none"
    query: Optional[str] = None


class PaginatedNationalMaterials(BaseModel):
    items: List[NationalMaterialSummary]
    total: int
    limit: int
    offset: int
    has_more: bool
    search_mode: Literal["keyword", "semantic", "none"] = "none"
    query: Optional[str] = None


class NormalizedMaterial(BaseModel):
    normalized_material_id: Optional[str] = None
    category_code: Optional[str] = None
    normalized_manufacturer: Optional[str] = None
    normalized_mpn: Optional[str] = None
    normalized_description: Optional[str] = None
    canonical_uom: Optional[str] = None
    normalization_method: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
