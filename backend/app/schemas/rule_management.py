"""
schemas/rule_management.py

Pydantic schemas for Rule Management API.
Admin-only: CriticalRule + GlobalMatchingConfig CRUD.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ──────────────────────────────────────────────────────────────────────────────
# Critical Rule schemas
# ──────────────────────────────────────────────────────────────────────────────

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
VALID_BEHAVIORS  = {"BLOCK_EQUIVALENCE", "REQUIRE_REVIEW", "FLAG_ONLY"}


class CriticalRuleCreate(BaseModel):
    classification_code: str = Field(..., description="e.g. 'VALVE', 'MOTOR', 'PIPE'")
    attribute: str           = Field(..., description="Attribute key, e.g. 'pressure_class'")
    severity: str            = Field("CRITICAL")
    conflict_behavior: str   = Field("BLOCK_EQUIVALENCE")
    notes: Optional[str]     = None

    @model_validator(mode="after")
    def validate_enums(self) -> "CriticalRuleCreate":
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {VALID_SEVERITIES}")
        if self.conflict_behavior not in VALID_BEHAVIORS:
            raise ValueError(f"conflict_behavior must be one of {VALID_BEHAVIORS}")
        return self


class CriticalRuleUpdate(BaseModel):
    """Partial update — creates a new version."""
    severity: Optional[str]          = None
    conflict_behavior: Optional[str] = None
    notes: Optional[str]             = None

    @model_validator(mode="after")
    def validate_enums(self) -> "CriticalRuleUpdate":
        if self.severity and self.severity not in VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {VALID_SEVERITIES}")
        if self.conflict_behavior and self.conflict_behavior not in VALID_BEHAVIORS:
            raise ValueError(f"conflict_behavior must be one of {VALID_BEHAVIORS}")
        return self


class CriticalRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    classification_code: str
    attribute: str
    severity: str
    conflict_behavior: str
    version: int
    is_latest: bool
    status: str
    notes: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CriticalRuleHistory(BaseModel):
    """All versions of a rule for audit display."""
    classification_code: str
    attribute: str
    versions: List[CriticalRuleRead]


# ──────────────────────────────────────────────────────────────────────────────
# Global Matching Config schemas
# ──────────────────────────────────────────────────────────────────────────────

VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


class GlobalMatchingConfigCreate(BaseModel):
    # Weights
    weight_semantic: float     = Field(0.30, ge=0.0, le=1.0)
    weight_attribute: float    = Field(0.40, ge=0.0, le=1.0)
    weight_manufacturer: float = Field(0.10, ge=0.0, le=1.0)
    weight_mpn: float          = Field(0.20, ge=0.0, le=1.0)

    # Thresholds
    threshold_exact_duplicate: float          = Field(0.95, ge=0.0, le=1.0)
    threshold_near_duplicate: float           = Field(0.85, ge=0.0, le=1.0)
    threshold_functionally_equivalent: float  = Field(0.65, ge=0.0, le=1.0)
    threshold_related: float                  = Field(0.50, ge=0.0, le=1.0)

    # Penalties
    penalty_missing_attribute: float  = Field(-0.05, le=0.0)
    penalty_critical_conflict: float  = Field(-0.50, le=0.0)

    # Approval policy
    auto_approve_enabled: bool             = False
    auto_approve_threshold: float          = Field(0.95, ge=0.0, le=1.0)
    auto_approve_max_risk_level: str       = "LOW"

    # Risk categories
    high_risk_categories: List[str]   = Field(default_factory=lambda: ["VALVE", "MOTOR", "PUMP", "COMPRESSOR"])
    medium_risk_categories: List[str] = Field(default_factory=lambda: ["PIPE", "BEARING"])

    change_note: Optional[str] = None

    @model_validator(mode="after")
    def validate_weights_and_levels(self) -> "GlobalMatchingConfigCreate":
        total = round(self.weight_semantic + self.weight_attribute + self.weight_manufacturer + self.weight_mpn, 6)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0 (got {total})")

        if self.threshold_related > self.threshold_functionally_equivalent > self.threshold_near_duplicate > self.threshold_exact_duplicate:
            raise ValueError("Thresholds must be ascending: related < functionally_equivalent < near_duplicate < exact_duplicate")

        if self.auto_approve_max_risk_level not in VALID_RISK_LEVELS:
            raise ValueError(f"auto_approve_max_risk_level must be one of {VALID_RISK_LEVELS}")

        return self


class GlobalMatchingConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    config_id: str
    version: int
    is_latest: bool

    weight_semantic: float
    weight_attribute: float
    weight_manufacturer: float
    weight_mpn: float

    threshold_exact_duplicate: float
    threshold_near_duplicate: float
    threshold_functionally_equivalent: float
    threshold_related: float

    penalty_missing_attribute: float
    penalty_critical_conflict: float

    auto_approve_enabled: bool
    auto_approve_threshold: float
    auto_approve_max_risk_level: str

    high_risk_categories: List[str]
    medium_risk_categories: List[str]

    created_by: Optional[str] = None
    change_note: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ──────────────────────────────────────────────────────────────────────────────
# Audit helper schema
# ──────────────────────────────────────────────────────────────────────────────

class RuleAuditEntry(BaseModel):
    audit_id: str
    action: str
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    actor_id: Optional[str] = None
    timestamp: datetime
