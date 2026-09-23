"""
app/repositories/material_repo.py — Query logic for material search endpoints.

All query building lives here — zero business logic, zero HTTP concerns.
Semantic search is stubbed behind SemanticSearchProvider so it can be swapped in
without touching the service layer.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from app.models.base import (
    CPSE,
    Classification,
    MaterialMapping,
    NationalMaterial,
    NormalizedMaterial,
    SourceMaterial,
    UOMMaster,
)

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# SORT COLUMNS WHITELIST  (prevents SQL-injection via sort_by param)
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_SORT_COLS: Dict[str, Any] = {
    "created_at":           SourceMaterial.created_at,
    "legacy_material_code": SourceMaterial.legacy_material_code,
    "manufacturer":         SourceMaterial.manufacturer,
    "plant":                SourceMaterial.plant,
    "raw_uom":              SourceMaterial.raw_uom,
    "raw_description":      SourceMaterial.raw_description,
    "cpse_id":              SourceMaterial.cpse_id,
}

_NATIONAL_SORT_COLS: Dict[str, Any] = {
    "national_material_code": NationalMaterial.national_material_code,
    "canonical_description":  NationalMaterial.canonical_description,
    "status":                 NationalMaterial.status,
    "version":                NationalMaterial.version,
    "created_at":             NationalMaterial.created_at,
    "updated_at":             NationalMaterial.updated_at,
}


# ─────────────────────────────────────────────────────────────────────────────
# SEMANTIC SEARCH PROTOCOL  (dependency-inversion — plug in real provider later)
# ─────────────────────────────────────────────────────────────────────────────

class SemanticSearchProvider(Protocol):
    """
    Contract that any semantic-search backend must satisfy.
    Returns an ordered list of (source_material_id, score) pairs.
    """
    def search_source_materials(
        self, query: str, limit: int, cpse_id: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        ...

    def search_national_materials(
        self, query: str, limit: int
    ) -> List[Tuple[str, float]]:
        ...


class _NoOpSemanticProvider:
    """Stub — returns empty results. Replace with pgvector / Pinecone / etc."""
    def search_source_materials(self, *_, **__) -> List[Tuple[str, float]]:
        return []

    def search_national_materials(self, *_, **__) -> List[Tuple[str, float]]:
        return []


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH PARAMS  (value objects passed from service to repo)
# ─────────────────────────────────────────────────────────────────────────────

class SourceSearchParams:
    __slots__ = (
        "keyword", "legacy_code", "mpn", "manufacturer",
        "cpse_id", "raw_category", "raw_uom", "classification_id",
        "mapping_status", "sort_by", "sort_dir", "limit", "offset",
        "semantic",
    )

    def __init__(
        self,
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
    ):
        self.keyword = keyword
        self.legacy_code = legacy_code
        self.mpn = mpn
        self.manufacturer = manufacturer
        self.cpse_id = cpse_id
        self.raw_category = raw_category
        self.raw_uom = raw_uom
        self.classification_id = classification_id
        self.mapping_status = mapping_status
        self.sort_by = sort_by
        self.sort_dir = sort_dir
        self.limit = limit
        self.offset = offset
        self.semantic = semantic


class NationalSearchParams:
    __slots__ = (
        "keyword", "classification_id", "canonical_uom",
        "status", "sort_by", "sort_dir", "limit", "offset", "semantic",
    )

    def __init__(
        self,
        keyword: Optional[str] = None,
        classification_id: Optional[str] = None,
        canonical_uom: Optional[str] = None,
        status: Optional[str] = None,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0,
        semantic: bool = False,
    ):
        self.keyword = keyword
        self.classification_id = classification_id
        self.canonical_uom = canonical_uom
        self.status = status
        self.sort_by = sort_by
        self.sort_dir = sort_dir
        self.limit = limit
        self.offset = offset
        self.semantic = semantic


# ─────────────────────────────────────────────────────────────────────────────
# RESULT TYPES
# ─────────────────────────────────────────────────────────────────────────────

class SourceMaterialRow:
    """Flat projection from the multi-join query."""
    __slots__ = (
        "source_material_id", "cpse_id", "legacy_material_code",
        "raw_description", "raw_uom", "raw_category",
        "manufacturer", "manufacturer_part_number",
        "raw_specification", "plant", "source_system",
        "source_file", "source_record_reference", "created_at",
        # from NormalizedMaterial
        "normalized_description", "canonical_uom", "classification_id",
        "normalization_version", "normalization_method", "confidence",
        "normalized_manufacturer", "normalized_mpn", "attributes", "embedding_ready",
        # from MaterialMapping + NationalMaterial
        "national_material_id", "national_material_code",
        "national_description", "mapping_status", "mapping_type",
        # semantic
        "semantic_score",
    )

    def __init__(self, sm: SourceMaterial, nm: Optional[NormalizedMaterial],
                 mm: Optional[MaterialMapping], nat: Optional[NationalMaterial],
                 semantic_score: Optional[float] = None):
        self.source_material_id = sm.source_material_id
        self.cpse_id = sm.cpse_id
        self.legacy_material_code = sm.legacy_material_code
        self.raw_description = sm.raw_description
        self.raw_uom = sm.raw_uom
        self.raw_category = sm.raw_category
        self.manufacturer = sm.manufacturer
        self.manufacturer_part_number = sm.manufacturer_part_number
        self.raw_specification = sm.raw_specification
        self.plant = sm.plant
        self.source_system = sm.source_system
        self.source_file = sm.source_file
        self.source_record_reference = sm.source_record_reference
        self.created_at = sm.created_at
        # normalised
        self.normalized_description = nm.normalized_description if nm else None
        self.canonical_uom = nm.canonical_uom if nm else None
        self.classification_id = nm.category_code if nm else None
        self.normalization_version = nm.normalization_version if nm else None
        self.normalization_method = nm.normalization_method if nm else None
        self.confidence = nm.confidence if nm else None
        self.normalized_manufacturer = nm.normalized_manufacturer if nm else None
        self.normalized_mpn = nm.normalized_mpn if nm else None
        self.attributes = nm.attributes if nm else None
        self.embedding_ready = nm is not None and getattr(nm, "embedding", None) is not None
        # mapping
        self.national_material_id = mm.national_material_id if mm else None
        self.mapping_type = mm.mapping_type if mm else None
        self.mapping_status = "MAPPED" if mm else "UNMAPPED"
        self.national_material_code = nat.national_material_code if nat else None
        self.national_description = nat.canonical_description if nat else None
        self.semantic_score = semantic_score


# ─────────────────────────────────────────────────────────────────────────────
# REPOSITORY
# ─────────────────────────────────────────────────────────────────────────────

class MaterialSearchRepo:

    def __init__(self, db: Session, semantic: SemanticSearchProvider | None = None):
        self.db = db
        self._semantic = semantic or _NoOpSemanticProvider()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _base_source_query(self):
        """Build the canonical multi-join query over SourceMaterial."""
        nm = aliased(NormalizedMaterial)
        mm = aliased(MaterialMapping)
        nat = aliased(NationalMaterial)
        return (
            self.db.query(SourceMaterial, nm, mm, nat)
            .outerjoin(nm, SourceMaterial.source_material_id == nm.source_material_id)
            .outerjoin(mm, SourceMaterial.source_material_id == mm.source_material_id)
            .outerjoin(nat, mm.national_material_id == nat.national_material_id)
        ), nm, mm, nat

    def _apply_source_filters(self, q, nm, mm, p: SourceSearchParams):
        if p.cpse_id:
            q = q.filter(SourceMaterial.cpse_id == p.cpse_id)
        if p.legacy_code:
            q = q.filter(SourceMaterial.legacy_material_code.ilike(f"%{p.legacy_code}%"))
        if p.manufacturer:
            q = q.filter(
                or_(
                    SourceMaterial.manufacturer.ilike(f"%{p.manufacturer}%"),
                    nm.normalized_manufacturer.ilike(f"%{p.manufacturer}%"),
                )
            )
        if p.mpn:
            q = q.filter(
                or_(
                    SourceMaterial.manufacturer_part_number.ilike(f"%{p.mpn}%"),
                    nm.normalized_mpn.ilike(f"%{p.mpn}%"),
                )
            )
        if p.raw_category:
            q = q.filter(
                or_(
                    SourceMaterial.raw_category.ilike(f"%{p.raw_category}%"),
                    nm.category_code == p.raw_category,
                )
            )
        if p.raw_uom:
            q = q.filter(
                or_(
                    SourceMaterial.raw_uom.ilike(p.raw_uom),
                    nm.canonical_uom == p.raw_uom,
                )
            )
        if p.classification_id:
            q = q.filter(nm.category_code == p.classification_id)
        if p.mapping_status == "MAPPED":
            q = q.filter(mm.mapping_id.isnot(None))
        elif p.mapping_status == "UNMAPPED":
            q = q.filter(mm.mapping_id.is_(None))
        if p.keyword:
            kw = f"%{p.keyword}%"
            q = q.filter(
                or_(
                    SourceMaterial.raw_description.ilike(kw),
                    SourceMaterial.legacy_material_code.ilike(kw),
                    SourceMaterial.manufacturer.ilike(kw),
                    SourceMaterial.manufacturer_part_number.ilike(kw),
                    nm.normalized_description.ilike(kw),
                )
            )
        return q

    def _apply_source_sort(self, q, p: SourceSearchParams):
        col = _SOURCE_SORT_COLS.get(p.sort_by, SourceMaterial.created_at)
        return q.order_by(col.asc() if p.sort_dir == "asc" else col.desc())

    # ── Public: Source Material ────────────────────────────────────────────────

    def search_source_materials(
        self, p: SourceSearchParams
    ) -> Tuple[List[SourceMaterialRow], int, str]:
        """
        Returns (rows, total_count, search_mode).
        search_mode: 'semantic' | 'keyword' | 'none'
        """
        # ── Semantic path ──────────────────────────────────────────────────────
        if p.semantic and p.keyword:
            hits = self._semantic.search_source_materials(
                p.keyword, limit=p.limit + p.offset, cpse_id=p.cpse_id
            )
            if hits:
                score_map = {sm_id: score for sm_id, score in hits}
                ids = list(score_map.keys())[p.offset: p.offset + p.limit]
                q, nm, mm, nat = self._base_source_query()
                q = q.filter(SourceMaterial.source_material_id.in_(ids))
                rows_raw = q.all()
                rows = []
                for sm, nm_, mm_, nat_ in rows_raw:
                    r = SourceMaterialRow(sm, nm_, mm_, nat_, score_map.get(sm.source_material_id))
                    rows.append(r)
                rows.sort(key=lambda r: r.semantic_score or 0, reverse=True)
                return rows, len(hits), "semantic"

        # ── Keyword / filter path ──────────────────────────────────────────────
        q, nm, mm, nat = self._base_source_query()
        q = self._apply_source_filters(q, nm, mm, p)
        total = q.count()
        q = self._apply_source_sort(q, p)
        rows_raw = q.offset(p.offset).limit(p.limit).all()
        rows = [SourceMaterialRow(sm, nm_, mm_, nat_) for sm, nm_, mm_, nat_ in rows_raw]
        mode = "keyword" if (p.keyword or any([p.legacy_code, p.manufacturer, p.mpn])) else "none"
        return rows, total, mode

    def get_source_material_by_id(self, source_material_id: str) -> Optional[SourceMaterialRow]:
        q, nm, mm, nat = self._base_source_query()
        q = q.filter(SourceMaterial.source_material_id == source_material_id)
        row = q.first()
        if not row:
            return None
        sm, nm_, mm_, nat_ = row
        return SourceMaterialRow(sm, nm_, mm_, nat_)

    # ── Public: National Material ──────────────────────────────────────────────

    def search_national_materials(
        self, p: NationalSearchParams
    ) -> Tuple[List[NationalMaterial], List[int], List[int], int, str]:
        """
        Returns (nat_materials, source_counts, cpse_counts, total, search_mode).
        """
        # ── Semantic path ──────────────────────────────────────────────────────
        if p.semantic and p.keyword:
            hits = self._semantic.search_national_materials(p.keyword, limit=p.limit + p.offset)
            if hits:
                score_map = {nm_id: score for nm_id, score in hits}
                ids = list(score_map.keys())[p.offset: p.offset + p.limit]
                nats = (
                    self.db.query(NationalMaterial)
                    .filter(NationalMaterial.national_material_id.in_(ids))
                    .all()
                )
                src_counts, cpse_counts = self._get_mapping_counts([n.national_material_id for n in nats])
                return nats, src_counts, cpse_counts, len(hits), "semantic"

        # ── Keyword / filter path ──────────────────────────────────────────────
        q = self.db.query(NationalMaterial)

        if p.keyword:
            kw = f"%{p.keyword}%"
            q = q.filter(
                or_(
                    NationalMaterial.canonical_description.ilike(kw),
                    NationalMaterial.national_material_code.ilike(kw),
                )
            )
        if p.classification_id:
            q = q.filter(NationalMaterial.classification_id == p.classification_id)
        if p.canonical_uom:
            q = q.filter(NationalMaterial.canonical_uom == p.canonical_uom)
        if p.status:
            q = q.filter(NationalMaterial.status == p.status)
        # Exclude soft-retired
        q = q.filter(NationalMaterial.is_retired.is_(False))

        total = q.count()
        col = _NATIONAL_SORT_COLS.get(p.sort_by, NationalMaterial.created_at)
        q = q.order_by(col.asc() if p.sort_dir == "asc" else col.desc())
        nats = q.offset(p.offset).limit(p.limit).all()

        src_counts, cpse_counts = self._get_mapping_counts([n.national_material_id for n in nats])
        mode = "keyword" if p.keyword else "none"
        return nats, src_counts, cpse_counts, total, mode

    def _get_mapping_counts(
        self, nat_ids: List[str]
    ) -> Tuple[Dict[str, int], Dict[str, int]]:
        if not nat_ids:
            return {}, {}
        rows = (
            self.db.query(
                MaterialMapping.national_material_id,
                func.count(MaterialMapping.source_material_id).label("src_count"),
                func.count(func.distinct(SourceMaterial.cpse_id)).label("cpse_count"),
            )
            .join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
            .filter(MaterialMapping.national_material_id.in_(nat_ids))
            .group_by(MaterialMapping.national_material_id)
            .all()
        )
        src = {r.national_material_id: r.src_count for r in rows}
        cpse = {r.national_material_id: r.cpse_count for r in rows}
        return src, cpse
