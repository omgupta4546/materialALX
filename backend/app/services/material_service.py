"""
app/services/material_service.py — Business logic for material search.

Translates HTTP query params → SearchParams → repo calls → schema objects.
No SQLAlchemy, no HTTP, no FastAPI.
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.material_repo import (
    MaterialSearchRepo,
    NationalSearchParams,
    SemanticSearchProvider,
    SourceMaterialRow,
    SourceSearchParams,
)
from app.schemas.material import (
    NationalMaterialSummary,
    PaginatedNationalMaterials,
    PaginatedSourceMaterials,
    SourceMaterialDetail,
    SourceMaterialSummary,
)


def _row_to_summary(row: SourceMaterialRow) -> SourceMaterialSummary:
    return SourceMaterialSummary(
        source_material_id=row.source_material_id,
        cpse_id=row.cpse_id,
        legacy_material_code=row.legacy_material_code,
        raw_description=row.raw_description,
        raw_uom=row.raw_uom,
        raw_category=row.raw_category,
        manufacturer=row.manufacturer,
        manufacturer_part_number=row.manufacturer_part_number,
        plant=row.plant,
        source_system=row.source_system,
        source_file=row.source_file,
        created_at=row.created_at,
        normalized_description=row.normalized_description,
        canonical_uom=row.canonical_uom,
        classification_id=row.classification_id,
        normalization_version=row.normalization_version,
        confidence=row.confidence,
        national_material_id=row.national_material_id,
        national_material_code=row.national_material_code,
        mapping_status=row.mapping_status,
        mapping_type=row.mapping_type,
        semantic_score=row.semantic_score,
    )


def _row_to_detail(row: SourceMaterialRow) -> SourceMaterialDetail:
    return SourceMaterialDetail(
        **_row_to_summary(row).model_dump(),
        raw_specification=row.raw_specification,
        source_record_reference=row.source_record_reference,
        normalized_manufacturer=row.normalized_manufacturer,
        normalized_mpn=row.normalized_mpn,
        normalization_method=row.normalization_method,
        attributes=row.attributes,
        embedding_ready=row.embedding_ready,
        national_description=row.national_description,
        audit_history=[],  # populated by future audit service
    )


class MaterialService:

    def __init__(self, db: Session, semantic: SemanticSearchProvider | None = None):
        self._repo = MaterialSearchRepo(db, semantic)

    # ── Source Materials ───────────────────────────────────────────────────────

    def list_materials(
        self,
        *,
        keyword: Optional[str] = None,
        legacy_code: Optional[str] = None,
        mpn: Optional[str] = None,
        manufacturer: Optional[str] = None,
        cpse_id: Optional[str] = None,
        raw_category: Optional[str] = None,
        raw_uom: Optional[str] = None,
        classification_id: Optional[str] = None,
        mapping_status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0,
        semantic: bool = False,
    ) -> PaginatedSourceMaterials:
        p = SourceSearchParams(
            keyword=keyword,
            legacy_code=legacy_code,
            mpn=mpn,
            manufacturer=manufacturer,
            cpse_id=cpse_id,
            raw_category=raw_category,
            raw_uom=raw_uom,
            classification_id=classification_id,
            mapping_status=mapping_status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
            semantic=semantic,
        )
        rows, total, mode = self._repo.search_source_materials(p)
        items = [_row_to_summary(r) for r in rows]
        return PaginatedSourceMaterials(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
            search_mode=mode,
            query=keyword,
        )

    def get_material(self, source_material_id: str) -> SourceMaterialDetail:
        row = self._repo.get_source_material_by_id(source_material_id)
        if not row:
            raise HTTPException(status_code=404, detail="Source material not found.")
        return _row_to_detail(row)

    # ── National Materials ─────────────────────────────────────────────────────

    def search_national_materials(
        self,
        *,
        keyword: Optional[str] = None,
        classification_id: Optional[str] = None,
        canonical_uom: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0,
        semantic: bool = False,
    ) -> PaginatedNationalMaterials:
        p = NationalSearchParams(
            keyword=keyword,
            classification_id=classification_id,
            canonical_uom=canonical_uom,
            status=status,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
            semantic=semantic,
        )
        nats, src_counts, cpse_counts, total, mode = self._repo.search_national_materials(p)

        items = [
            NationalMaterialSummary(
                national_material_id=n.national_material_id,
                national_material_code=n.national_material_code,
                canonical_description=n.canonical_description,
                classification_id=n.classification_id,
                canonical_uom=n.canonical_uom,
                status=n.status,
                version=n.version,
                created_at=n.created_at,
                updated_at=n.updated_at,
                source_count=src_counts.get(n.national_material_id, 0),
                cpse_count=cpse_counts.get(n.national_material_id, 0),
            )
            for n in nats
        ]
        return PaginatedNationalMaterials(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
            search_mode=mode,
            query=keyword,
        )
