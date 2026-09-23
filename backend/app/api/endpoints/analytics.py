"""
Analytics router — Database-backed endpoints for dynamic charting.

Filters supported:
- cpse_code (str)
- sector (str)
- category_code (str)
- start_date (date)
- end_date (date)
"""
from typing import Optional, Any
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case, or_
from sqlalchemy.orm import Session, Query as SAQuery

from app.api.deps import get_db
from app.models.base import (
    SourceMaterial, NormalizedMaterial, MatchResult, MaterialMapping,
    Approval, ProcessingJob, FileUpload, NationalMaterial, CPSE,
    Classification, ProcurementRecord, DataQualityMetrics,
)
from app.auth.rbac import require_role, Roles, enforce_cpse_tenant

router = APIRouter()

ALL_ROLES = [Roles.ADMIN, Roles.DATA_STEWARD, Roles.ENGINEER, Roles.AUDITOR, Roles.CPSE_USER]

def _safe_pct(a: int, b: int) -> float:
    return round((a / b) * 100, 1) if b > 0 else 0.0

# ─────────────────────────────────────────────────────────────────
# QUERY BUILDER HELPERS
# ─────────────────────────────────────────────────────────────────

class AnalyticsFilters:
    def __init__(
        self,
        cpse_code: Optional[str] = Depends(enforce_cpse_tenant),
        sector: Optional[str] = Query(None, description="Filter by Sector"),
        category_code: Optional[str] = Query(None, description="Filter by taxonomy category"),
        start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
        end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    ):
        self.cpse_code = cpse_code
        self.sector = sector
        self.category_code = category_code
        self.start_date = start_date
        self.end_date = end_date

def apply_filters(q: SAQuery, base_model: Any, filters: AnalyticsFilters) -> SAQuery:
    """
    Applies cross-cutting filters to an SQLAlchemy query.
    Requires that base_model is joined to SourceMaterial if CPSE/Sector filtering is needed,
    or that base_model is SourceMaterial itself.
    Requires joined NormalizedMaterial if category_code filtering is needed.
    Requires base_model to have a created_at or timestamp field for date filtering.
    """
    
    # Identify timestamp field
    ts_field = None
    if hasattr(base_model, "created_at"):
        ts_field = base_model.created_at
    elif hasattr(base_model, "timestamp"):
        ts_field = base_model.timestamp
    elif hasattr(base_model, "started_at"):
        ts_field = base_model.started_at

    if ts_field is not None:
        if filters.start_date:
            q = q.filter(ts_field >= filters.start_date)
        if filters.end_date:
            q = q.filter(ts_field <= filters.end_date)
            
    if filters.cpse_code:
        # Require CPSE to be joined to check cpse_code
        q = q.filter(CPSE.cpse_code == filters.cpse_code)
        
    if filters.sector:
        # Require CPSE to be joined to check sector
        q = q.filter(CPSE.sector == filters.sector)
        
    if filters.category_code:
        # Assuming NormalizedMaterial is in the query or joined
        q = q.filter(NormalizedMaterial.category_code.like(f"{filters.category_code}%"))

    return q

# ─────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────

@router.get("/overview", dependencies=[Depends(require_role(ALL_ROLES))])
def get_overview(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    # Base query for source materials
    q_src = db.query(func.count(SourceMaterial.source_material_id))
    # No cartesian product here if we just join CPSE directly from SourceMaterial
    if filters.sector or filters.cpse_code:
        q_src = q_src.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
    # Apply category_code filter (requires NormalizedMaterial)
    if filters.category_code:
        q_src = q_src.join(NormalizedMaterial, SourceMaterial.source_material_id == NormalizedMaterial.source_material_id)
    q_src = apply_filters(q_src, SourceMaterial, filters)
    total_source = q_src.scalar() or 0

    # Base query for normalized materials
    q_norm = db.query(func.count(NormalizedMaterial.normalized_material_id))
    q_norm = q_norm.join(SourceMaterial, NormalizedMaterial.source_material_id == SourceMaterial.source_material_id)
    if filters.sector or filters.cpse_code:
        q_norm = q_norm.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
    q_norm = apply_filters(q_norm, NormalizedMaterial, filters)
    total_normalized = q_norm.scalar() or 0

    # Total matches
    q_match = db.query(func.count(MatchResult.match_id))
    q_match = q_match.join(NormalizedMaterial, MatchResult.material_a_id == NormalizedMaterial.normalized_material_id)
    q_match = q_match.join(SourceMaterial, NormalizedMaterial.source_material_id == SourceMaterial.source_material_id)
    if filters.sector or filters.cpse_code:
        q_match = q_match.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
    q_match = apply_filters(q_match, MatchResult, filters)
    
    total_matches = q_match.scalar() or 0
    dup_candidates = q_match.filter(MatchResult.match_type == "NEAR_DUPLICATE").scalar() or 0
    func_equiv = q_match.filter(MatchResult.match_type == "FUNCTIONALLY_EQUIVALENT").scalar() or 0
    high_risk_matches = q_match.filter(MatchResult.risk_level.in_(["HIGH", "CRITICAL"])).scalar() or 0
    engineering_reviews = q_match.filter(MatchResult.match_type == "REQUIRES_ENGINEERING_REVIEW").scalar() or 0

    # Total mapped
    q_map = db.query(func.count(MaterialMapping.mapping_id))
    q_map = q_map.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
    q_map = q_map.join(NormalizedMaterial, MaterialMapping.source_material_id == NormalizedMaterial.source_material_id, isouter=True)
    if filters.sector or filters.cpse_code:
        q_map = q_map.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
    q_map = apply_filters(q_map, MaterialMapping, filters)
    total_mapped = q_map.scalar() or 0
    
    approved_mappings = q_map.filter(MaterialMapping.approved_by.isnot(None)).scalar() or 0

    # Pending approvals
    # We query MaterialMapping where status == 'PENDING' since Approval table records actual decisions
    q_appr = db.query(func.count(MaterialMapping.mapping_id)).filter(MaterialMapping.status == "PENDING")
    
    if filters.sector or filters.cpse_code:
        q_appr = q_appr.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
        q_appr = q_appr.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
    if filters.category_code:
        # Ensure join to NormalizedMaterial if missing (if CPSE join wasn't done, we need SourceMaterial first)
        if not (filters.sector or filters.cpse_code):
            q_appr = q_appr.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
        q_appr = q_appr.join(NormalizedMaterial, MaterialMapping.source_material_id == NormalizedMaterial.source_material_id)
        
    q_appr = apply_filters(q_appr, MaterialMapping, filters)
    pending_approvals = q_appr.scalar() or 0

    norm_pct = _safe_pct(total_normalized, total_source)
    map_pct  = _safe_pct(total_mapped, total_source)
    dq_score = round((norm_pct * 0.6 + map_pct * 0.4), 1)

    return {
        "total_source_materials": total_source,
        "normalized_materials": total_normalized,
        "normalization_pct": norm_pct,
        "duplicate_candidates": dup_candidates,
        "functional_equivalents": func_equiv,
        "high_risk_matches": high_risk_matches,
        "engineering_reviews": engineering_reviews,
        "pending_approvals": pending_approvals,
        "approved_mappings": approved_mappings,
        "total_mapped": total_mapped,
        "mapping_pct": map_pct,
        "data_quality_score": dq_score,
        "total_matches": total_matches,
    }


@router.get("/dashboard", dependencies=[Depends(require_role(ALL_ROLES))])
def get_dashboard(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q_total = db.query(func.count(SourceMaterial.source_material_id))
    q_norm = db.query(func.count(NormalizedMaterial.normalized_material_id))

    if filters.sector or filters.cpse_code:
        q_total = q_total.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
        q_norm = q_norm.join(SourceMaterial, NormalizedMaterial.source_material_id == SourceMaterial.source_material_id)
        q_norm = q_norm.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)

    q_total = apply_filters(q_total, SourceMaterial, filters)
    q_norm = apply_filters(q_norm, NormalizedMaterial, filters)

    return {
        "total_materials": q_total.scalar() or 0,
        "normalized_materials": q_norm.scalar() or 0,
    }


@router.get("/materials-by-cpse", dependencies=[Depends(require_role(ALL_ROLES))])
def get_materials_by_cpse(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q = db.query(CPSE.cpse_code, func.count(SourceMaterial.source_material_id).label("count"))
    q = q.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
    # We don't join NormalizedMaterial here since it's just raw source count
    
    ts_field = SourceMaterial.created_at
    if filters.start_date: q = q.filter(ts_field >= filters.start_date)
    if filters.end_date: q = q.filter(ts_field <= filters.end_date)
    if filters.cpse_code: q = q.filter(CPSE.cpse_code == filters.cpse_code)
    if filters.sector: q = q.filter(CPSE.sector == filters.sector)
    
    rows = q.group_by(CPSE.cpse_code).order_by(func.count(SourceMaterial.source_material_id).desc()).all()
    return [{"cpse": r[0], "count": r[1]} for r in rows]


@router.get("/upload-categories", dependencies=[Depends(require_role(ALL_ROLES))])
def get_upload_categories(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q = db.query(ProcessingJob.status, func.count(ProcessingJob.job_id).label("count"))
    
    ts_field = ProcessingJob.started_at
    if filters.start_date: q = q.filter(ts_field >= filters.start_date)
    if filters.end_date: q = q.filter(ts_field <= filters.end_date)
        
    rows = q.group_by(ProcessingJob.status).all()
    return [{"status": r[0] or "UNKNOWN", "count": r[1]} for r in rows]


@router.get("/confidence-distribution", dependencies=[Depends(require_role(ALL_ROLES))])
def get_confidence_distribution(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    # We use MaterialMapping as the source of truth for confidence
    q = db.query(MaterialMapping.confidence).filter(MaterialMapping.confidence.isnot(None))
    
    q = q.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
    q = q.join(NormalizedMaterial, MaterialMapping.source_material_id == NormalizedMaterial.source_material_id, isouter=True)
    if filters.sector or filters.cpse_code:
        q = q.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
    
    q = apply_filters(q, MaterialMapping, filters)
    
    bands = {"90-100%": 0, "75-90%": 0, "50-75%": 0, "Below 50%": 0}
    for (score,) in q.all():
        if score >= 0.90: bands["90-100%"] += 1
        elif score >= 0.75: bands["75-90%"] += 1
        elif score >= 0.50: bands["50-75%"] += 1
        else: bands["Below 50%"] += 1
        
    return [{"range": k, "count": v} for k, v in bands.items()]


@router.get("/pending-approvals", dependencies=[Depends(require_role(ALL_ROLES))])
def get_pending_approvals(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q = db.query(MaterialMapping.mapping_type, func.count(MaterialMapping.mapping_id).label("count"))\
          .filter(MaterialMapping.status == "PENDING")
          
    if filters.sector or filters.cpse_code:
        q = q.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
        q = q.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
    if filters.category_code:
        if not (filters.sector or filters.cpse_code):
            q = q.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
        q = q.join(NormalizedMaterial, MaterialMapping.source_material_id == NormalizedMaterial.source_material_id)
        
    q = apply_filters(q, MaterialMapping, filters)
    
    rows = q.group_by(MaterialMapping.mapping_type).all()
    return [{"type": r[0] or "UNKNOWN", "count": r[1]} for r in rows]


@router.get("/redundant-material-groups", dependencies=[Depends(require_role(ALL_ROLES))])
def get_redundant_groups(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q = db.query(
        MaterialMapping.national_material_id,
        NationalMaterial.canonical_description,
        func.count(MaterialMapping.source_material_id).label("mapped_count"),
        func.count(func.distinct(SourceMaterial.cpse_id)).label("cpse_count")
    )
    q = q.join(NationalMaterial, MaterialMapping.national_material_id == NationalMaterial.national_material_id, isouter=True)
    q = q.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id, isouter=True)
    q = q.join(NormalizedMaterial, MaterialMapping.source_material_id == NormalizedMaterial.source_material_id, isouter=True)
    if filters.sector or filters.cpse_code:
        q = q.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
        
    q = apply_filters(q, MaterialMapping, filters)
    
    rows = q.group_by(MaterialMapping.national_material_id, NationalMaterial.canonical_description)\
            .order_by(func.count(MaterialMapping.source_material_id).desc())\
            .limit(10).all()
            
    return [{
        "national_code": r[0],
        "description": (r[1] or r[0] or "Unknown")[:40],
        "mapped_count": r[2],
        "cpse_count": r[3],
    } for r in rows]


@router.get("/procurement-opportunities", dependencies=[Depends(require_role(ALL_ROLES))])
def get_procurement_opportunities(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q = db.query(
        MaterialMapping.national_material_id,
        NationalMaterial.canonical_description,
        func.sum(ProcurementRecord.total_spend).label("total_spend"),
        func.count(func.distinct(SourceMaterial.cpse_id)).label("cpse_count"),
        func.count(ProcurementRecord.procurement_id).label("order_count")
    )
    q = q.join(ProcurementRecord, MaterialMapping.source_material_id == ProcurementRecord.source_material_id)
    q = q.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id, isouter=True)
    q = q.join(NationalMaterial, MaterialMapping.national_material_id == NationalMaterial.national_material_id, isouter=True)
    q = q.join(NormalizedMaterial, MaterialMapping.source_material_id == NormalizedMaterial.source_material_id, isouter=True)
    
    if filters.sector or filters.cpse_code:
        q = q.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
        
    q = apply_filters(q, ProcurementRecord, filters)
    
    rows = q.group_by(MaterialMapping.national_material_id, NationalMaterial.canonical_description)\
            .having(func.count(func.distinct(SourceMaterial.cpse_id)) > 1)\
            .order_by(func.sum(ProcurementRecord.total_spend).desc())\
            .limit(20).all()
            
    return [{
        "national_code": r[0],
        "description": r[1] or r[0] or "Unknown",
        "total_spend": float(r[2] or 0),
        "cpse_count": r[3],
        "order_count": r[4],
    } for r in rows]


@router.get("/classification-coverage", dependencies=[Depends(require_role(ALL_ROLES))])
def get_classification_coverage(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q = db.query(
        NormalizedMaterial.category_code,
        func.count(NormalizedMaterial.normalized_material_id).label("count")
    ).filter(NormalizedMaterial.category_code.isnot(None))
    
    q = q.join(SourceMaterial, NormalizedMaterial.source_material_id == SourceMaterial.source_material_id)
    if filters.sector:
        q = q.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
        
    q = apply_filters(q, NormalizedMaterial, filters)
    
    rows = q.group_by(NormalizedMaterial.category_code)\
            .order_by(func.count(NormalizedMaterial.normalized_material_id).desc())\
            .limit(10).all()
            
    return [{"category": r[0] or "Uncategorized", "count": r[1]} for r in rows]


@router.get("/data-quality", dependencies=[Depends(require_role(ALL_ROLES))])
def get_data_quality(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q = db.query(
        func.avg(DataQualityMetrics.completeness_score).label("avg_completeness"),
        func.avg(DataQualityMetrics.uniqueness_score).label("avg_uniqueness"),
        func.avg(DataQualityMetrics.validity_score).label("avg_validity"),
        func.avg(DataQualityMetrics.consistency_score).label("avg_consistency"),
    )
    
    q = q.join(NormalizedMaterial, DataQualityMetrics.material_id == NormalizedMaterial.normalized_material_id)
    q = q.join(SourceMaterial, NormalizedMaterial.source_material_id == SourceMaterial.source_material_id)
    
    if filters.sector or filters.cpse_code:
        q = q.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
        
    q = apply_filters(q, DataQualityMetrics, filters)
    
    res = q.first()
    return {
        "avg_completeness": float(res[0] or 0.0),
        "avg_uniqueness": float(res[1] or 0.0),
        "avg_validity": float(res[2] or 0.0),
        "avg_consistency": float(res[3] or 0.0),
    }


@router.get("/processing-health", dependencies=[Depends(require_role(ALL_ROLES))])
def get_processing_health(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    # Using PostgreSQL extract epoch for duration
    q = db.query(
        func.count(ProcessingJob.job_id).label("total_jobs"),
        func.sum(ProcessingJob.records_processed).label("total_records"),
        func.avg(
            func.extract('epoch', func.coalesce(ProcessingJob.completed_at, func.current_timestamp()) - ProcessingJob.started_at) / 86400.0
        ).label("avg_duration_days") 
    )
    
    if filters.start_date: q = q.filter(ProcessingJob.started_at >= filters.start_date)
    if filters.end_date: q = q.filter(ProcessingJob.started_at <= filters.end_date)
    
    jobs = q.all()
    return {
        "total_jobs": jobs[0][0] or 0,
        "total_records_processed": jobs[0][1] or 0,
        "avg_duration_days": float(jobs[0][2] or 0.0)
    }

@router.get("/risk-distribution", dependencies=[Depends(require_role(ALL_ROLES))])
def get_risk_distribution(
    filters: AnalyticsFilters = Depends(),
    db: Session = Depends(get_db)
):
    q = db.query(
        case(
            (MatchResult.risk_level == "CRITICAL", "High Risk"),
            (MatchResult.risk_level == "HIGH", "High Risk"),
            (MatchResult.risk_level == "MEDIUM", "Medium Risk"),
            else_="Low Risk"
        ).label("risk_level"),
        func.count(MatchResult.match_id).label("count")
    )
    
    q = q.join(NormalizedMaterial, MatchResult.material_a_id == NormalizedMaterial.normalized_material_id)
    q = q.join(SourceMaterial, NormalizedMaterial.source_material_id == SourceMaterial.source_material_id)
    if filters.sector or filters.cpse_code:
        q = q.join(CPSE, SourceMaterial.cpse_id == CPSE.cpse_id)
        
    q = apply_filters(q, MatchResult, filters)
    
    rows = q.group_by("risk_level").all()
    return [{"risk_level": r[0], "count": r[1]} for r in rows]


@router.get("/recent-uploads", dependencies=[Depends(require_role(ALL_ROLES))])
def get_recent_uploads(db: Session = Depends(get_db)):
    """Recent file uploads for dashboard activity feed."""
    rows = db.query(FileUpload).order_by(FileUpload.timestamp.desc()).limit(5).all()
    return [
        {"id": r.id, "filename": r.filename, "status": r.status, "timestamp": r.timestamp.isoformat() if r.timestamp else None}
        for r in rows
    ]


@router.get("/recent-approvals", dependencies=[Depends(require_role(ALL_ROLES))])
def get_recent_approvals(db: Session = Depends(get_db)):
    """Recent approval decisions for dashboard activity feed."""
    rows = db.query(Approval).order_by(Approval.created_at.desc()).limit(5).all()
    return [
        {"id": r.approval_id, "target_id": r.match_id or "", "target_type": r.review_type or "MATCH", "status": r.decision, "approver_id": r.reviewer_id, "timestamp": r.created_at.isoformat() if r.created_at else None}
        for r in rows
    ]


@router.get("/recent-jobs", dependencies=[Depends(require_role(ALL_ROLES))])
def get_recent_jobs(db: Session = Depends(get_db)):
    """Recent processing jobs for dashboard activity feed."""
    rows = db.query(ProcessingJob).order_by(ProcessingJob.started_at.desc()).limit(5).all()
    return [
        {"job_id": r.job_id, "status": r.status, "records_processed": r.records_processed, "started_at": r.started_at.isoformat() if r.started_at else None}
        for r in rows
    ]

