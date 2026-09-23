"""
database/models.py — Complete schema for the National Material Intelligence Platform.

Design decisions:
  - All PKs are String (UUID) except autoincrement surrogate keys.
  - Soft retirement: is_retired + retired_at + retired_reason on lifecycle tables.
  - Timestamps: created_at (immutable), updated_at (auto-update via onupdate).
  - pgvector: NormalizedMaterial.embedding uses HNSW index for ANN search.
  - Indexes: composite indexes on high-cardinality foreign keys + status columns.
  - Constraints: CHECK constraints on enum-like columns, UNIQUE where appropriate.
  - All relationships defined for ORM convenience but fetched lazily by default.
"""

from __future__ import annotations

from datetime import datetime
import uuid
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey,
    JSON, DateTime, Text, UniqueConstraint, CheckConstraint, Index,
    event, DDL
)
from sqlalchemy.orm import declarative_base, relationship, backref
from app.core.db_config import db_config

# pgvector is optional — not available on SQLite / CI environments
try:
    from pgvector.sqlalchemy import Vector as _Vector
    _PGVECTOR_AVAILABLE = True
except ImportError:
    _Vector = None
    _PGVECTOR_AVAILABLE = False


def _vector_column(dimension: int):
    """Return a Vector column for PostgreSQL, or a JSON fallback for SQLite/CI."""
    if _PGVECTOR_AVAILABLE:
        return Column(_Vector(dimension))
    return Column(JSON, nullable=True)  # SQLite / CI fallback

Base = declarative_base()


# ─────────────────────────────────────────────────────────────────────────────
# MIXINS
# ─────────────────────────────────────────────────────────────────────────────

class TimestampMixin:
    """Immutable created_at + auto-updated updated_at."""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SoftRetireMixin:
    """Soft retirement — never hard-delete lifecycle records."""
    is_retired    = Column(Boolean, default=False, nullable=False, index=True)
    retired_at    = Column(DateTime, nullable=True)
    retired_by    = Column(String, nullable=True)
    retired_reason = Column(Text, nullable=True)

    def retire(self, by: str, reason: str = "") -> None:
        self.is_retired     = True
        self.retired_at     = datetime.utcnow()
        self.retired_by     = by
        self.retired_reason = reason


# ─────────────────────────────────────────────────────────────────────────────
# REFERENCE / CONFIGURATION TABLES
# ─────────────────────────────────────────────────────────────────────────────

class CPSE(Base, TimestampMixin):
    """Central Public Sector Enterprise — top-level tenant."""
    __tablename__ = "cpse"

    cpse_id     = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    cpse_code   = Column(String(20), unique=True, nullable=False, index=True)
    cpse_name   = Column(String(200), nullable=False)
    sector      = Column(String(100))
    description = Column(Text)
    status      = Column(String(30), default="ACTIVE", nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'SUSPENDED')", name="ck_cpse_status"),
        Index("ix_cpse_sector", "sector"),
    )


class Role(Base):
    __tablename__ = "role"

    id          = Column(String(50), primary_key=True)
    description = Column(Text)


class User(Base, TimestampMixin, SoftRetireMixin):
    __tablename__ = "user_account"

    user_id       = Column(String(50), primary_key=True)
    name          = Column(String(200))
    email         = Column(String(200))
    password_hash = Column(String(256))
    role_id       = Column(String(50), ForeignKey("role.id"))
    cpse_code     = Column(String(20), ForeignKey("cpse.cpse_code"), index=True)
    permissions   = Column(JSON, default=list)

    __table_args__ = (
        Index("ix_user_cpse_role", "cpse_code", "role_id"),
        UniqueConstraint("email", name="uq_user_email"),
    )


class Classification(Base):
    """Material taxonomy — tree structure via parent_id self-referential FK."""
    __tablename__ = "classification"

    classification_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_id         = Column(String(64), ForeignKey("classification.classification_id"), nullable=True, index=True)
    code              = Column(String(50), nullable=False, unique=True, index=True)
    name              = Column(String(200), nullable=False)
    level             = Column(Integer, default=0)
    description       = Column(Text)
    status            = Column(String(20), default="ACTIVE")
    version           = Column(Integer, default=1)
    is_latest         = Column(Boolean, default=True)

    children = relationship("Classification", backref=backref("parent", remote_side=[classification_id]))

    __table_args__ = (
        Index("ix_classification_parent", "parent_id"),
    )


class UOMMaster(Base):
    __tablename__ = "uom_master"

    canonical_code  = Column(String(20), primary_key=True)
    name            = Column(String(100))
    dimension       = Column(String(50))  # MASS, VOLUME, COUNT, LENGTH, etc.
    aliases         = Column(JSON, default=list)  # ["PCS", "PIECES", "NO"]
    status          = Column(String(20), default="ACTIVE")
    base_multiplier = Column(Float, default=1.0)
    is_base_unit    = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_uom_dimension", "dimension"),
        Index("ix_uom_status", "status"),
    )


class Synonym(Base):
    __tablename__ = "synonym"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    term         = Column(String(200), nullable=False)
    expansion    = Column(String(200), nullable=False)
    is_ambiguous = Column(Boolean, default=False)
    source       = Column(String(50))  # MANUAL | GENERATED | IMPORTED

    __table_args__ = (
        Index("ix_synonym_term", "term"),
        UniqueConstraint("term", "expansion", name="uq_synonym_pair"),
    )




class CriticalRule(Base, TimestampMixin):
    """
    Per-attribute critical rule for a classification category.
    Changes are versioned. Admin-only writes.
    """
    __tablename__ = "critical_rule"

    id                = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    classification_code = Column(String(100), nullable=False, index=True)  # e.g. "VALVE", "MOTOR"
    attribute         = Column(String(100), nullable=False)
    severity          = Column(String(20), nullable=False, default="CRITICAL")  # CRITICAL|HIGH|MEDIUM|LOW
    conflict_behavior = Column(String(50), default="BLOCK_EQUIVALENCE")  # BLOCK_EQUIVALENCE|REQUIRE_REVIEW|FLAG_ONLY
    version           = Column(Integer, default=1)
    is_latest         = Column(Boolean, default=True, index=True)
    status            = Column(String(20), default="ACTIVE")  # ACTIVE|INACTIVE|DEPRECATED
    created_by        = Column(String(64), ForeignKey("user_account.user_id"), nullable=True)
    notes             = Column(Text)

    __table_args__ = (
        CheckConstraint("severity IN ('CRITICAL','HIGH','MEDIUM','LOW')", name="ck_critical_rule_severity"),
        CheckConstraint("conflict_behavior IN ('BLOCK_EQUIVALENCE','REQUIRE_REVIEW','FLAG_ONLY')", name="ck_critical_rule_behavior"),
        Index("ix_critical_rule_cat_attr", "classification_code", "attribute"),
        Index("ix_critical_rule_latest", "is_latest"),
    )


class GlobalMatchingConfig(Base, TimestampMixin):
    """
    Versioned global weights, thresholds, and automatic-approval policy.
    Only one record is "active" (is_latest=True) at any time.
    Admin-only writes. Each change creates a new version.
    """
    __tablename__ = "global_matching_config"

    config_id   = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    version     = Column(Integer, nullable=False, default=1)
    is_latest   = Column(Boolean, default=True, index=True)

    # ---- Matching weights (must sum to ~1.0) ----
    weight_semantic      = Column(Float, default=0.30)
    weight_attribute     = Column(Float, default=0.40)
    weight_manufacturer  = Column(Float, default=0.10)
    weight_mpn           = Column(Float, default=0.20)

    # ---- Match-type thresholds ----
    threshold_exact_duplicate         = Column(Float, default=0.95)
    threshold_near_duplicate          = Column(Float, default=0.85)
    threshold_functionally_equivalent = Column(Float, default=0.65)
    threshold_related                 = Column(Float, default=0.50)

    # ---- Penalty coefficients ----
    penalty_missing_attribute  = Column(Float, default=-0.05)
    penalty_critical_conflict  = Column(Float, default=-0.50)

    # ---- Automatic approval policy ----
    # If final_score >= auto_approve_threshold AND risk_level in auto_approve_risk_levels
    # the system may approve without human intervention.
    auto_approve_enabled          = Column(Boolean, default=False)
    auto_approve_threshold        = Column(Float, default=0.95)
    auto_approve_max_risk_level   = Column(String(20), default="LOW")  # LOW|MEDIUM|HIGH|CRITICAL

    # ---- Risk category lists ----
    high_risk_categories    = Column(JSON, default=lambda: ["VALVE", "MOTOR", "PUMP", "COMPRESSOR"])
    medium_risk_categories  = Column(JSON, default=lambda: ["PIPE", "BEARING"])

    created_by  = Column(String(64), ForeignKey("user_account.user_id"), nullable=True)
    change_note = Column(Text)

    __table_args__ = (
        CheckConstraint("auto_approve_max_risk_level IN ('LOW','MEDIUM','HIGH','CRITICAL')", name="ck_gmc_risk_level"),
        Index("ix_global_config_latest", "is_latest"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# MATERIAL LIFECYCLE — the core pipeline
# ─────────────────────────────────────────────────────────────────────────────

class SourceMaterial(Base):
    """
    Immutable ingested record — source of truth for what arrived from CPSE.
    Never modified after ingestion.
    """
    __tablename__ = "source_material"

    source_material_id       = Column(String(64), primary_key=True)   # UUID
    cpse_id                  = Column(String(64), ForeignKey("cpse.cpse_id"), nullable=False)
    legacy_material_code     = Column(String(100), nullable=False)
    raw_description          = Column(Text)
    raw_uom                  = Column(String(50))
    raw_category             = Column(String(100))
    manufacturer             = Column(String(200), index=True)
    manufacturer_part_number = Column(String(100), index=True)
    raw_specification        = Column(Text)
    plant                    = Column(String(50))
    source_system            = Column(String(100))
    source_file              = Column(String(255))
    source_record_reference  = Column(String(255))
    created_at               = Column(DateTime, default=datetime.utcnow, nullable=False)

    normalized    = relationship("NormalizedMaterial", back_populates="source", uselist=False, lazy="select")
    mappings      = relationship("MaterialMapping", back_populates="source", lazy="dynamic")

    __table_args__ = (
        UniqueConstraint("cpse_id", "legacy_material_code", name="uq_cpse_legacy_code"),
        Index("ix_source_material_cpse_legacy", "cpse_id", "legacy_material_code"),
    )


class NormalizedMaterial(Base, TimestampMixin):
    """
    AI-enriched view of a SourceMaterial.
    One-to-one with SourceMaterial. Regenerated on model update.
    """
    __tablename__ = "normalized_material"

    normalized_material_id  = Column(String(64), primary_key=True)
    source_material_id      = Column(String(64), ForeignKey("source_material.source_material_id"), nullable=False, index=True)
    raw_description         = Column(Text)
    normalized_description  = Column(Text)
    canonical_uom           = Column(String(20), ForeignKey("uom_master.canonical_code"), index=True)
    category_code           = Column(String(50), ForeignKey("classification.code"), index=True)
    normalized_manufacturer = Column(String(200), index=True)
    normalized_mpn          = Column(String(200))
    attributes              = Column(JSON, default=dict)
    normalization_version   = Column(String(50))
    normalization_method    = Column(String(50))
    confidence              = Column(Float)
    processing_time_ms      = Column(Integer)

    # pgvector — 768d (all-mpnet-base-v2) or 1536d (text-embedding-3-small)
    embedding               = _vector_column(db_config.embedding_dimension)

    source = relationship("SourceMaterial", back_populates="normalized")
    quality_metrics = relationship("DataQualityMetrics", back_populates="material", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_material_id", "normalization_version", name="uq_normalized_source_version"),
        Index("ix_normalized_category", "category_code"),
        Index("ix_normalized_manufacturer", "normalized_manufacturer"),
        # HNSW approximate nearest-neighbour index (PostgreSQL + pgvector only)
        *(
            [Index(
                "ix_normalized_embedding_hnsw",
                "embedding",
                postgresql_using="hnsw",
                postgresql_with={"m": db_config.hnsw_m, "ef_construction": db_config.hnsw_ef_construction},
                postgresql_ops={"embedding": "vector_cosine_ops"},
            )]
            if _PGVECTOR_AVAILABLE else []
        ),
    )


class NationalMaterial(Base, TimestampMixin, SoftRetireMixin):
    """Golden record — the canonical standard for a material class."""
    __tablename__ = "national_material"

    national_material_id   = Column(String(64), primary_key=True)
    national_material_code = Column(String(50), nullable=False, unique=True, index=True)
    canonical_description  = Column(Text, nullable=False)
    classification_id      = Column(String(64), ForeignKey("classification.classification_id"), index=True)
    canonical_uom          = Column(String(20), ForeignKey("uom_master.canonical_code"), index=True)
    attributes             = Column(JSON, default=dict)
    status                 = Column(String(20), default="PROVISIONAL")
    version                = Column(Integer, default=1)
    provenance             = Column(JSON, default=dict)
    created_by             = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)

    mappings = relationship("MaterialMapping", back_populates="national", lazy="dynamic")

    __table_args__ = (
        CheckConstraint(
            "status IN ('PROVISIONAL','UNDER_REVIEW','ACTIVE','SUPERSEDED','RETIRED','REJECTED')",
            name="ck_national_status"
        ),
        Index("ix_national_material_status",   "status"),
        Index("ix_national_material_category", "classification_id"),
    )


class MaterialMapping(Base, TimestampMixin):
    """
    Source → National mapping record.
    Human decision is immutable once approved — append only for corrections.
    """
    __tablename__ = "material_mapping"

    mapping_id       = Column(String(64), primary_key=True)
    source_material_id = Column(String(64), ForeignKey("source_material.source_material_id"), nullable=False, index=True)
    national_material_id = Column(String(64), ForeignKey("national_material.national_material_id"), nullable=False, index=True)
    mapping_type     = Column(String(30))
    confidence       = Column(Float)
    status           = Column(String(30), default="PENDING")
    created_by       = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)
    approved_by      = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)
    approved_at      = Column(DateTime, nullable=True)
    is_ai_suggested  = Column(Boolean, default=True)
    notes            = Column(Text, nullable=True)

    source   = relationship("SourceMaterial", back_populates="mappings")
    national = relationship("NationalMaterial", back_populates="mappings")

    __table_args__ = (
        UniqueConstraint("source_material_id", "national_material_id", name="uq_mapping_source_national"),
        CheckConstraint("mapping_type IN ('EXACT_DUPLICATE','NEAR_DUPLICATE','FUNCTIONALLY_EQUIVALENT','LEGACY_MAPPING')", name="ck_mapping_type"),
        CheckConstraint("status IN ('PENDING','APPROVED','REJECTED','ENGINEERING_REVIEW')", name="ck_mapping_status"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_confidence_range"),
        Index("ix_mapping_national_confidence", "national_material_id", "confidence"),
    )


class AttributeDefinition(Base):
    """Category-specific attribute schemas."""
    __tablename__ = "attribute_definition"

    attribute_definition_id = Column(String(64), primary_key=True)
    classification_id       = Column(String(64), ForeignKey("classification.classification_id"), nullable=False, index=True)
    attribute_name          = Column(String(100), nullable=False)
    data_type               = Column(String(20), default="STRING")
    is_required             = Column(Boolean, default=False)
    description             = Column(Text)

    __table_args__ = (
        UniqueConstraint("classification_id", "attribute_name", name="uq_attr_def_class_name"),
    )


class MaterialAttribute(Base, TimestampMixin):
    """Extracted attribute key-value pairs - normalised from NormalizedMaterial.attributes."""
    __tablename__ = "material_attribute"

    material_attribute_id   = Column(String(64), primary_key=True)
    normalized_material_id  = Column(String(64), ForeignKey("normalized_material.normalized_material_id"), index=True, nullable=True)
    national_material_id    = Column(String(64), ForeignKey("national_material.national_material_id"), index=True, nullable=True)
    attribute_name          = Column(String(100), nullable=False)
    original_value          = Column(String(500))
    normalized_value        = Column(String(500))
    unit                    = Column(String(30))
    extraction_method       = Column(String(50))
    extraction_confidence   = Column(Float)
    source_span             = Column(JSON)

    __table_args__ = (
        CheckConstraint(
            "(normalized_material_id IS NOT NULL AND national_material_id IS NULL) OR "
            "(normalized_material_id IS NULL AND national_material_id IS NOT NULL)",
            name="ck_mat_attr_reference"
        ),
        Index("ix_mat_attr_norm_name", "normalized_material_id", "attribute_name"),
        Index("ix_mat_attr_nat_name", "national_material_id", "attribute_name"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# AI / MATCHING
# ─────────────────────────────────────────────────────────────────────────────

class MatchResult(Base, TimestampMixin):
    """
    AI-generated match candidate.
    Human decisions are stored separately in Approval — never overwrite here.
    """
    __tablename__ = "match_result"

    match_id          = Column(String(64), primary_key=True)
    material_a_id     = Column(String(64), ForeignKey("normalized_material.normalized_material_id"), index=True)
    material_b_id     = Column(String(64), ForeignKey("national_material.national_material_id"), index=True)
    semantic_score    = Column(Float)
    attribute_score   = Column(Float)
    rule_score        = Column(Float)
    final_score       = Column(Float)
    match_type        = Column(String(50))
    positive_evidence = Column(JSON, default=dict)
    negative_evidence = Column(JSON, default=dict)
    conflicts         = Column(JSON, default=dict)
    recommendation    = Column(String(50))
    risk_level        = Column(String(20))
    requires_human_review = Column(Boolean, default=True)
    model_version     = Column(String(50))
    prompt_version    = Column(String(50))
    rules_version     = Column(String(50))

    __table_args__ = (
        Index("ix_match_result_final_score", "material_a_id", "final_score"),
        CheckConstraint("semantic_score >= 0 AND semantic_score <= 1", name="ck_match_semantic_score"),
        CheckConstraint("attribute_score >= 0 AND attribute_score <= 1", name="ck_match_attribute_score"),
        CheckConstraint("rule_score >= 0 AND rule_score <= 1", name="ck_match_rule_score"),
        CheckConstraint("final_score >= 0 AND final_score <= 1", name="ck_match_final_score"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNANCE
# ─────────────────────────────────────────────────────────────────────────────

class Approval(Base, TimestampMixin):
    __tablename__ = "approval"

    approval_id = Column(String(64), primary_key=True)
    match_id    = Column(String(64), ForeignKey("match_result.match_id"), index=True)
    reviewer_id = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)
    decision    = Column(String(20), nullable=False)
    comment     = Column(Text)
    review_type = Column(String(50))

    __table_args__ = (
        Index("ix_approval_status", "decision"),
        CheckConstraint(
            "decision IN ('APPROVED','REJECTED','ESCALATED')",
            name="ck_approval_decision"
        ),
    )


class AuditLog(Base):
    """Immutable, append-only audit trail. Never updated, never deleted."""
    __tablename__ = "audit_log"

    audit_id    = Column(String(64), primary_key=True)
    entity_type = Column(String(50), index=True)
    entity_id   = Column(String(64), index=True)
    action      = Column(String(50))
    old_value   = Column(JSON)
    new_value   = Column(JSON)
    actor_id    = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)
    timestamp   = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    source      = Column(String(100))
    model_version = Column(String(50))
    prompt_version = Column(String(50))
    rules_version = Column(String(50))
    request_id  = Column(String(64))

    __table_args__ = (
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
    )


class MatchingRule(Base, TimestampMixin):
    __tablename__ = "matching_rule"

    rule_id       = Column(String(64), primary_key=True)
    rule_name     = Column(String(100), nullable=False)
    description   = Column(Text)
    logic_payload = Column(JSON, default=dict)
    is_active     = Column(Boolean, default=True)


class FeedbackEvent(Base, TimestampMixin):
    """
    Human reviewer decision record. Immutable after creation.
    Drives model analytics and future retraining governance.

    Governance rule:
      - AI outputs in MatchResult are NEVER modified by this record.
      - Retraining requires explicit governance action (NOT triggered here).
    """
    __tablename__ = "feedback_event"

    event_id        = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    reviewer_id     = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)

    # ── What was reviewed ──────────────────────────────────────────────────
    match_id        = Column(String(64), ForeignKey("match_result.match_id"), nullable=True, index=True)
    target_id       = Column(String(64), index=True)           # generic fallback
    target_type     = Column(String(50), index=True)           # "MATCH", "ATTRIBUTE_CORRECTION" etc.

    # ── AI recommendation snapshot (immutable copy at time of review) ─────
    ai_match_type   = Column(String(50))                       # EXACT_DUPLICATE, FUNCTIONALLY_EQUIVALENT …
    ai_final_score  = Column(Float)
    ai_risk_level   = Column(String(20))
    ai_recommendation = Column(String(50))                     # APPROVE, REQUIRES_REVIEW …
    ai_model_version  = Column(String(50))
    ai_prompt_version = Column(String(50))
    ai_rules_version  = Column(String(50))

    # ── Human decision ─────────────────────────────────────────────────────
    event_type      = Column(String(50), nullable=False, index=True)
    # APPROVED | REJECTED | ENGINEERING_REVIEW | ATTRIBUTE_CORRECTED
    human_decision  = Column(String(50), index=True)
    reason          = Column(Text)
    corrected_attributes = Column(JSON)    # populated when event_type = ATTRIBUTE_CORRECTED

    # ── Source material snapshot (for pattern mining without re-joining) ───
    category_code   = Column(String(100), index=True)
    source_material_id = Column(String(64), ForeignKey("source_material.source_material_id"), nullable=True)

    # ── Disagreement flag (AI ≠ Human) ────────────────────────────────────
    is_disagreement = Column(Boolean, default=False, index=True)
    # True if human_decision contradicts ai_recommendation

    feedback_data   = Column(JSON, default=dict)   # any additional context

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('APPROVED','REJECTED','ENGINEERING_REVIEW','ATTRIBUTE_CORRECTED')",
            name="ck_feedback_event_type"
        ),
        Index("ix_feedback_target", "target_type", "target_id"),
        Index("ix_feedback_event_category", "category_code", "event_type"),
        Index("ix_feedback_disagreement", "is_disagreement"),
    )


class RetrainingCandidate(Base, TimestampMixin):
    """
    Staging table: curated feedback records nominated for model retraining.

    Governance rule:
      - Records are NEVER automatically promoted to production training.
      - An ADMIN must explicitly mark a retraining_run as APPROVED before
        any model pipeline consumes these records.
      - This table is append-only: no row is ever deleted.
    """
    __tablename__ = "retraining_candidate"

    candidate_id    = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id        = Column(String(64), ForeignKey("feedback_event.event_id"), nullable=False, index=True)
    nominated_by    = Column(String(64), ForeignKey("user_account.user_id"), nullable=True)
    nomination_note = Column(Text)
    # PENDING | APPROVED_FOR_TRAINING | EXCLUDED
    status          = Column(String(30), default="PENDING", index=True)
    approved_by     = Column(String(64), ForeignKey("user_account.user_id"), nullable=True)
    approved_at     = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('PENDING','APPROVED_FOR_TRAINING','EXCLUDED')", name="ck_retrain_status"),
        Index("ix_retrain_candidate_status", "status"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# OPERATIONS & JOBS
# ─────────────────────────────────────────────────────────────────────────────

class ProcessingJob(Base, TimestampMixin):
    __tablename__ = "processing_job"

    job_id            = Column(String(64), primary_key=True)
    job_type          = Column(String(50), default="UPLOAD_PROCESSING", index=True)
    status            = Column(String(30), nullable=False, default="PENDING", index=True)
    records_processed = Column(Integer, default=0)
    total_records     = Column(Integer, default=0)
    successful        = Column(Integer, default=0)
    failed            = Column(Integer, default=0)
    current_stage     = Column(String(50), nullable=True)
    errors            = Column(JSON, default=dict)
    details           = Column(JSON, default=dict)
    started_at        = Column(DateTime, default=datetime.utcnow)
    completed_at      = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED')", name="ck_job_status"),
        Index("ix_job_status_type", "status", "job_type"),
    )


class FileUpload(Base, TimestampMixin):
    __tablename__ = "file_upload"

    id          = Column(String(64), primary_key=True)
    cpse_code   = Column(String(20), ForeignKey("cpse.cpse_code"), index=True)
    filename    = Column(String(500))
    file_size   = Column(Integer)                # bytes
    uploaded_by = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)
    job_id      = Column(String(64), ForeignKey("processing_job.job_id"), nullable=True, index=True)
    status      = Column(String(30), default="UPLOADED")
    timestamp   = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_file_upload_cpse", "cpse_code"),
    )

class StoredFile(Base, TimestampMixin):
    """Metadata for uploaded files stored externally (Local/S3)."""
    __tablename__ = "stored_file"
    
    file_id      = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name    = Column(String(500), nullable=False)
    storage_key  = Column(String(1000), nullable=False, unique=True, index=True)
    file_hash    = Column(String(256))
    size_bytes   = Column(Integer)
    content_type = Column(String(100))
    uploaded_by  = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)
    uploaded_at  = Column(DateTime, default=datetime.utcnow, nullable=False)


class Notification(Base, TimestampMixin):
    __tablename__ = "notification"

    id        = Column(String(64), primary_key=True)
    user_id   = Column(String(50), ForeignKey("user_account.user_id"), index=True)
    type      = Column(String(50))
    title     = Column(String(200))
    message   = Column(Text)
    is_read   = Column(Boolean, default=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_notification_user_unread", "user_id", "is_read"),
    )


class ModelRegistry(Base, TimestampMixin):
    """Track which AI model versions are deployed for reproducibility."""
    __tablename__ = "model_registry"

    model_id            = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_name          = Column(String(100), nullable=False)
    model_version       = Column(String(100), nullable=False)
    provider            = Column(String(50), nullable=False)
    task                = Column(String(100), nullable=False)
    embedding_dimension = Column(Integer, nullable=True)
    deployment_status   = Column(String(30), default="ACTIVE", index=True)

    __table_args__ = (
        UniqueConstraint("model_name", "model_version", name="uq_model_registry_name_version"),
        CheckConstraint("deployment_status IN ('ACTIVE','DEPRECATED','ARCHIVED')", name="ck_model_deployment_status"),
    )


class PromptRegistry(Base, TimestampMixin):
    """Track exactly what prompt templates were used during AI orchestration."""
    __tablename__ = "prompt_registry"
    
    prompt_id       = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    task            = Column(String(100), nullable=False, index=True)
    prompt_version  = Column(String(100), nullable=False, unique=True)
    prompt_template = Column(Text, nullable=False)
    is_active       = Column(Boolean, default=True, index=True)


class DataQualityMetrics(Base, TimestampMixin):
    """Track data quality indicators per normalized material."""
    __tablename__ = "data_quality_metrics"
    
    metric_id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    material_id = Column(String(64), ForeignKey("normalized_material.normalized_material_id"), unique=True)
    
    completeness_score = Column(Float, default=0.0)
    uniqueness_score = Column(Float, default=0.0)
    validity_score = Column(Float, default=0.0)
    consistency_score = Column(Float, default=0.0)
    standardization_score = Column(Float, default=0.0)
    attribute_coverage = Column(Float, default=0.0)
    
    flags = Column(JSON, default=list)  # e.g., ["missing_pressure_class", "invalid_uom"]
    
    material = relationship("NormalizedMaterial", back_populates="quality_metrics")




# ─────────────────────────────────────────────────────────────────────────────
# PROCUREMENT
# ─────────────────────────────────────────────────────────────────────────────

class ProcurementRecord(Base, TimestampMixin):
    __tablename__ = "procurement_record"

    procurement_id   = Column(String(64), primary_key=True)
    source_material_id = Column(String(64), ForeignKey("source_material.source_material_id"), index=True)
    supplier         = Column(String(200), index=True)
    quantity         = Column(Float)
    unit_price       = Column(Float)
    total_spend      = Column(Float, index=True)
    currency         = Column(String(10), default="INR")
    procurement_date = Column(DateTime, index=True)
    plant            = Column(String(50))
    purchase_order   = Column(String(100))

    __table_args__ = (
        Index("ix_proc_source_date", "source_material_id", "procurement_date"),
        Index("ix_proc_supplier",    "supplier"),
    )


class GroundTruth(Base, TimestampMixin):
    __tablename__ = "ground_truth"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    source_material_id_a       = Column(String(64), ForeignKey("source_material.source_material_id"), index=True)
    source_material_id_b       = Column(String(64), ForeignKey("source_material.source_material_id"), index=True)
    ground_truth_label = Column(String(50), nullable=False)  # MATCH | NO_MATCH | CONFLICT
    reason            = Column(Text)
    annotator_id      = Column(String(50))

    __table_args__ = (
        UniqueConstraint("source_material_id_a", "source_material_id_b", name="uq_ground_truth_pair"),
        CheckConstraint("ground_truth_label IN ('MATCH','NO_MATCH','CONFLICT','NEAR_DUPLICATE','FUNCTIONAL_EQUIV')", name="ck_gt_label"),
    )

# ─────────────────────────────────────────────────────────────────────────────
# MIGRATION
# ─────────────────────────────────────────────────────────────────────────────

class MigrationBatch(Base, TimestampMixin):
    """Tracks a batch of legacy codes slated for migration to national codes."""
    __tablename__ = "migration_batch"
    
    batch_id    = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name        = Column(String(200), nullable=False)
    status      = Column(String(50), default="DRAFT", index=True)
    created_by  = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','VALIDATED','APPROVED','READY','EXECUTED','ROLLED_BACK','FAILED')",
            name="ck_migration_batch_status"
        ),
    )


class MigrationRecord(Base):
    """Individual legacy code migration within a batch."""
    __tablename__ = "migration_record"
    
    record_id      = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id       = Column(String(64), ForeignKey("migration_batch.batch_id"), nullable=False, index=True)
    legacy_code    = Column(String(100), nullable=False, index=True)
    national_code  = Column(String(50), nullable=False, index=True)
    mapping_id     = Column(String(64), ForeignKey("material_mapping.mapping_id"), nullable=True)
    status         = Column(String(50), default="DRAFT", index=True)
    result         = Column(Text, nullable=True)
    timestamp      = Column(DateTime, default=datetime.utcnow)
    operator_id    = Column(String(50), ForeignKey("user_account.user_id"), nullable=True)
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','VALIDATED','APPROVED','READY','EXECUTED','ROLLED_BACK','FAILED')",
            name="ck_migration_record_status"
        ),
        UniqueConstraint("batch_id", "legacy_code", name="uq_migration_batch_legacy"),
    )

from sqlalchemy import event

@event.listens_for(SourceMaterial, "before_update")
def receive_before_update(mapper, connection, target):
    raise ValueError("SourceMaterial records are strictly immutable. They cannot be updated.")
