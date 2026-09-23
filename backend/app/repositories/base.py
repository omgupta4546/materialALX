"""
database/repository.py — Generic repository base class.

Provides type-safe CRUD, pagination, soft-retire, and audit trail helpers.
All business repositories inherit from BaseRepository[ModelT].
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Generic, TypeVar, Type, Optional, List, Tuple, Any, Dict

from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic repository providing common database operations.

    Usage::

        class SourceMaterialRepo(BaseRepository[SourceMaterial]):
            model = SourceMaterial

        repo = SourceMaterialRepo(db)
        sm = repo.get("source-id-123")
    """

    model: Type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── READ ──────────────────────────────────────────────────────

    def get(self, pk: Any) -> Optional[ModelT]:
        """Fetch by primary key. Returns None if not found."""
        return self.db.get(self.model, pk)

    def get_or_raise(self, pk: Any) -> ModelT:
        obj = self.get(pk)
        if obj is None:
            raise ValueError(f"{self.model.__name__} '{pk}' not found")
        return obj

    def list(
        self,
        filters: Optional[List[Any]] = None,
        order_by: Optional[Any] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[ModelT], int]:
        """
        Return (records, total_count) with optional filtering and pagination.
        Excludes soft-retired records automatically if model supports it.
        """
        q = self.db.query(self.model)

        # Exclude soft-retired
        if hasattr(self.model, "is_retired"):
            q = q.filter(self.model.is_retired.is_(False))

        if filters:
            q = q.filter(*filters)

        total = q.count()

        if order_by is not None:
            q = q.order_by(order_by)

        records = q.offset(offset).limit(limit).all()
        return records, total

    def exists(self, pk: Any) -> bool:
        return self.db.get(self.model, pk) is not None

    def count(self, filters: Optional[List[Any]] = None) -> int:
        q = self.db.query(func.count()).select_from(self.model)
        if filters:
            q = q.filter(*filters)
        return q.scalar() or 0

    # ── WRITE ─────────────────────────────────────────────────────

    def create(self, **kwargs) -> ModelT:
        """Create and flush (but don't commit) a new record."""
        obj = self.model(**kwargs)
        self.db.add(obj)
        self.db.flush()
        return obj

    def update(self, obj: ModelT, **kwargs) -> ModelT:
        """Apply field updates and set updated_at if present."""
        for key, value in kwargs.items():
            setattr(obj, key, value)
        if hasattr(obj, "updated_at"):
            obj.updated_at = datetime.utcnow()
        self.db.flush()
        return obj

    def upsert(self, pk: Any, defaults: Dict[str, Any]) -> Tuple[ModelT, bool]:
        """
        Get-or-create pattern. Returns (obj, created).
        created=True means a new record was created.
        """
        obj = self.get(pk)
        if obj is None:
            pk_col = self.model.__table__.primary_key.columns.keys()[0]
            return self.create(**{pk_col: pk, **defaults}), True
        return obj, False

    def delete(self, obj: ModelT) -> None:
        """Hard delete — use only for non-lifecycle tables."""
        self.db.delete(obj)
        self.db.flush()

    def retire(self, obj: ModelT, by: str, reason: str = "") -> ModelT:
        """Soft-retire. Raises AttributeError if model doesn't support it."""
        if not hasattr(obj, "retire"):
            raise AttributeError(f"{self.model.__name__} does not support soft-retire")
        obj.retire(by=by, reason=reason)
        self.db.flush()
        return obj

    def bulk_create(self, records: List[Dict[str, Any]]) -> int:
        """Bulk-insert using core INSERT for high throughput. Returns count."""
        if not records:
            return 0
        self.db.execute(self.model.__table__.insert(), records)
        return len(records)

    # ── UTILITY ───────────────────────────────────────────────────

    @staticmethod
    def new_id() -> str:
        """Generate a URL-safe UUID4 string."""
        return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# SPECIALISED REPOSITORIES
# ─────────────────────────────────────────────────────────────────────────────

from app.models.base import (
    SourceMaterial, NormalizedMaterial, NationalMaterial, MaterialMapping,
    MatchResult, Approval, AuditLog, ProcessingJob, CPSE, Classification,
    AttributeDefinition, MaterialAttribute, User, Role, ProcurementRecord,
    FileUpload, Notification, UOMMaster, MatchingRule, FeedbackEvent,
    ModelRegistry
)


class SourceMaterialRepo(BaseRepository[SourceMaterial]):
    model = SourceMaterial

    def __init__(self, db: Session):
        super().__init__(db)

    def get_by_cpse_and_legacy_code(self, cpse_id: str, legacy_code: str) -> Optional[SourceMaterial]:
        return self.db.query(SourceMaterial).filter(
            SourceMaterial.cpse_id == cpse_id,
            SourceMaterial.legacy_material_code == legacy_code
        ).first()

    def get_by_cpse(self, cpse_id: str, limit: int = 100, offset: int = 0) -> List[SourceMaterial]:
        return self.db.query(SourceMaterial)\
            .filter(SourceMaterial.cpse_id == cpse_id)\
            .limit(limit).offset(offset).all()

    def count_by_cpse(self) -> Dict[str, int]:
        rows = (
            self.db.query(SourceMaterial.cpse_id, func.count(SourceMaterial.source_material_id))
            .group_by(SourceMaterial.cpse_id)
            .all()
        )
        return {r[0]: r[1] for r in rows}


class NormalizedMaterialRepo(BaseRepository[NormalizedMaterial]):
    model = NormalizedMaterial

    def by_source(self, source_material_id: str) -> List[NormalizedMaterial]:
        return self.db.query(NormalizedMaterial).filter(
            NormalizedMaterial.source_material_id == source_material_id
        ).order_by(NormalizedMaterial.created_at.desc()).all()

    def get_latest_by_source(self, source_material_id: str) -> Optional[NormalizedMaterial]:
        return self.db.query(NormalizedMaterial).filter(
            NormalizedMaterial.source_material_id == source_material_id
        ).order_by(NormalizedMaterial.created_at.desc()).first()

    def by_source_and_version(self, source_material_id: str, version: str) -> Optional[NormalizedMaterial]:
        return self.db.query(NormalizedMaterial).filter(
            NormalizedMaterial.source_material_id == source_material_id,
            NormalizedMaterial.normalization_version == version
        ).first()

    def without_embeddings(self) -> List[NormalizedMaterial]:
        return self.db.query(NormalizedMaterial).filter(
            NormalizedMaterial.embedding.is_(None)
        ).all()


class NationalMaterialRepo(BaseRepository[NationalMaterial]):
    model = NationalMaterial

    def by_code(self, code: str) -> Optional[NationalMaterial]:
        return self.db.query(NationalMaterial).filter(
            NationalMaterial.national_material_code == code
        ).first()

    def active_only(self) -> List[NationalMaterial]:
        return self.db.query(NationalMaterial).filter(
            NationalMaterial.status == "ACTIVE",
            NationalMaterial.is_retired.is_(False)
        ).all()

    def next_version(self, code: str) -> int:
        obj = self.by_code(code)
        if not obj:
            return 1
        return obj.version + 1


class MatchResultRepo(BaseRepository[MatchResult]):
    model = MatchResult

    def pending_review(self, min_score: float = 0.0) -> List[MatchResult]:
        approved_ids = self.db.query(Approval.match_id).subquery()
        return (
            self.db.query(MatchResult)
            .filter(
                MatchResult.final_score >= min_score,
                MatchResult.requires_human_review == True,
                MatchResult.match_id.not_in(approved_ids)
            )
            .order_by(MatchResult.final_score.desc())
            .all()
        )

class ApprovalRepo(BaseRepository[Approval]):
    model = Approval

    def get_by_match_id(self, match_id: str) -> List[Approval]:
        return self.db.query(Approval).filter(Approval.match_id == match_id).all()


class AuditLogRepo(BaseRepository[AuditLog]):
    model = AuditLog

    def log(
        self,
        action: str,
        entity_id: str,
        entity_type: str = "",
        old_value: Optional[Dict] = None,
        new_value: Optional[Dict] = None,
        actor_id: Optional[str] = None,
        source: Optional[str] = None,
        model_version: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> AuditLog:
        entry = AuditLog(
            audit_id=str(uuid.uuid4()),
            action=action,
            actor_id=actor_id,
            entity_id=entity_id,
            entity_type=entity_type,
            old_value=old_value or {},
            new_value=new_value or {},
            timestamp=datetime.utcnow(),
            source=source,
            model_version=model_version,
            request_id=request_id,
        )
        self.db.add(entry)
        return entry


class ProcessingJobRepo(BaseRepository[ProcessingJob]):
    model = ProcessingJob

    def start(self, job_id: str, total_records: int = 0) -> ProcessingJob:
        obj = self.get_or_raise(job_id)
        obj.status = "RUNNING"
        obj.started_at = datetime.utcnow()
        obj.total_records = total_records
        self.db.flush()
        return obj

    def complete(self, job_id: str, records_processed: int) -> ProcessingJob:
        obj = self.get_or_raise(job_id)
        obj.status = "COMPLETED"
        obj.completed_at = datetime.utcnow()
        obj.records_processed = records_processed
        self.db.flush()
        return obj

    def fail(self, job_id: str, error: str) -> ProcessingJob:
        obj = self.get_or_raise(job_id)
        obj.status = "FAILED"
        obj.completed_at = datetime.utcnow()
        obj.errors = {"error": error}
        self.db.flush()
        return obj

class CPSERepo(BaseRepository[CPSE]):
    model = CPSE

    def get_by_code(self, code: str) -> Optional[CPSE]:
        return self.db.query(CPSE).filter(CPSE.cpse_code == code).first()


class MaterialMappingRepo(BaseRepository[MaterialMapping]):
    model = MaterialMapping

    def get_by_source(self, source_material_id: str) -> List[MaterialMapping]:
        return self.db.query(MaterialMapping).filter(
            MaterialMapping.source_material_id == source_material_id
        ).all()

    def check_conflicts(self, source_material_id: str) -> None:
        """Raises ValueError if an ACTIVE or PENDING mapping already exists for this source."""
        existing = self.db.query(MaterialMapping).filter(
            MaterialMapping.source_material_id == source_material_id,
            MaterialMapping.status.in_(["PENDING", "APPROVED"])
        ).first()
        if existing:
            raise ValueError(f"Conflicting mapping exists for source {source_material_id}")

    def create(self, **kwargs) -> MaterialMapping:
        if "source_material_id" in kwargs:
            self.check_conflicts(kwargs["source_material_id"])
        return super().create(**kwargs)


class AttributeDefinitionRepo(BaseRepository[AttributeDefinition]):
    model = AttributeDefinition

    def get_by_classification(self, classification_id: str) -> List[AttributeDefinition]:
        return self.db.query(AttributeDefinition).filter(
            AttributeDefinition.classification_id == classification_id
        ).all()


class MaterialAttributeRepo(BaseRepository[MaterialAttribute]):
    model = MaterialAttribute

    def get_by_normalized(self, normalized_material_id: str) -> List[MaterialAttribute]:
        return self.db.query(MaterialAttribute).filter(
            MaterialAttribute.normalized_material_id == normalized_material_id
        ).all()

    def get_by_national(self, national_material_id: str) -> List[MaterialAttribute]:
        return self.db.query(MaterialAttribute).filter(
            MaterialAttribute.national_material_id == national_material_id
        ).all()


class ClassificationRepo(BaseRepository[Classification]):
    model = Classification

    def get_roots(self) -> List[Classification]:
        return self.db.query(Classification).filter(
            Classification.parent_id.is_(None)
        ).all()

    def get_children(self, parent_id: str) -> List[Classification]:
        return self.db.query(Classification).filter(
            Classification.parent_id == parent_id
        ).all()


class UserRepo(BaseRepository[User]):
    model = User

class RoleRepo(BaseRepository[Role]):
    model = Role

class ProcurementRecordRepo(BaseRepository[ProcurementRecord]):
    model = ProcurementRecord

class FileUploadRepo(BaseRepository[FileUpload]):
    model = FileUpload

class NotificationRepo(BaseRepository[Notification]):
    model = Notification

class UOMMasterRepo(BaseRepository[UOMMaster]):
    model = UOMMaster

class MatchingRuleRepo(BaseRepository[MatchingRule]):
    model = MatchingRule

class FeedbackEventRepo(BaseRepository[FeedbackEvent]):
    model = FeedbackEvent

class ModelRegistryRepo(BaseRepository[ModelRegistry]):
    model = ModelRegistry
