import io
import csv
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.base import (
    MaterialMapping, SourceMaterial, NationalMaterial,
    MatchResult, ProcessingJob, AuditLog, DataQualityMetrics,
    ProcurementRecord
)
from app.auth.rbac import require_role, Roles, enforce_cpse_tenant
import pandas as pd
from typing import Optional

router = APIRouter()

ALL_ROLES = [Roles.ADMIN, Roles.DATA_STEWARD, Roles.ENGINEER, Roles.AUDITOR, Roles.CPSE_USER]

def generate_export_response(data: List[Dict[str, Any]], filename: str, format_type: str) -> StreamingResponse:
    if not data:
        data = [{"message": "No data available"}]
        
    df = pd.DataFrame(data)
    
    if format_type == 'csv':
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
        )
    elif format_type == 'xlsx':
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
        stream.seek(0)
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")


@router.get("/{report_type}", dependencies=[Depends(require_role(ALL_ROLES))])
def export_report(
    report_type: str,
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    cpse_code: Optional[str] = Depends(enforce_cpse_tenant),
    db: Session = Depends(get_db)
):
    data = []
    filename = f"{report_type}_report"

    if report_type == "cpse-mapping":
        # CPSE mapping report
        q = db.query(
            MaterialMapping.mapping_id,
            MaterialMapping.status,
            SourceMaterial.cpse_id,
            SourceMaterial.legacy_material_code,
            SourceMaterial.raw_description,
            NationalMaterial.national_material_code,
            NationalMaterial.canonical_description,
            MaterialMapping.confidence
        ).join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)\
         .join(NationalMaterial, MaterialMapping.national_material_id == NationalMaterial.national_material_id, isouter=True)
        if cpse_code:
            q = q.filter(SourceMaterial.cpse_id == cpse_code)
        rows = q.all()
        data = [dict(zip(r._fields, r)) for r in rows]

    elif report_type == "duplicate-report":
        # duplicate report
        q = db.query(
            MatchResult.match_id,
            MatchResult.material_a_id,
            MatchResult.material_b_id,
            MatchResult.match_type,
            MatchResult.risk_level,
            MatchResult.final_score
        ).filter(MatchResult.match_type == "NEAR_DUPLICATE")
        # In a real app we would join SourceMaterial to filter MatchResult by CPSE.
        rows = q.all()
        data = [dict(zip(r._fields, r)) for r in rows]

    elif report_type == "material-master":
        # material master
        if cpse_code:
            # If tenant-restricted, they shouldn't dump the whole national master.
            raise HTTPException(status_code=403, detail="Only admins and stewards can export the full material master.")
        rows = db.query(
            NationalMaterial.national_material_code,
            NationalMaterial.canonical_description,
            NationalMaterial.canonical_uom,
            NationalMaterial.status
        ).all()
        data = [dict(zip(r._fields, r)) for r in rows]

    elif report_type == "migration-report":
        # migration report
        rows = db.query(
            ProcessingJob.job_id,
            ProcessingJob.status,
            ProcessingJob.records_processed,
            ProcessingJob.started_at,
            ProcessingJob.completed_at
        ).all()
        data = [dict(zip(r._fields, r)) for r in rows]

    elif report_type == "procurement-opportunity":
        # Just use procurement intelligence API logic
        from sqlalchemy import func
        q = db.query(
            NationalMaterial.national_material_code,
            NationalMaterial.canonical_description,
            func.count(func.distinct(SourceMaterial.cpse_id)).label("cpse_count"),
            func.sum(ProcurementRecord.total_spend).label("historical_spend")
        ).join(MaterialMapping, NationalMaterial.national_material_id == MaterialMapping.national_material_id, isouter=True)\
         .join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id, isouter=True)\
         .join(ProcurementRecord, SourceMaterial.source_material_id == ProcurementRecord.source_material_id, isouter=True)
        if cpse_code:
            q = q.filter(SourceMaterial.cpse_id == cpse_code)
            
        rows = q.group_by(NationalMaterial.national_material_code, NationalMaterial.canonical_description)\
         .having(func.count(func.distinct(SourceMaterial.cpse_id)) > 1).all()
        data = [dict(zip(r._fields, r)) for r in rows]

    elif report_type == "audit-report":
        rows = db.query(
            AuditLog.audit_id,
            AuditLog.actor_id,
            AuditLog.action,
            AuditLog.entity_type,
            AuditLog.entity_id,
            AuditLog.timestamp
        ).all()
        data = [dict(zip(r._fields, r)) for r in rows]

    elif report_type == "data-quality-report":
        rows = db.query(
            DataQualityMetrics.metric_id,
            DataQualityMetrics.material_id,
            DataQualityMetrics.completeness_score,
            DataQualityMetrics.uniqueness_score,
            DataQualityMetrics.validity_score,
            DataQualityMetrics.consistency_score
        ).all()
        data = [dict(zip(r._fields, r)) for r in rows]

    else:
        raise HTTPException(status_code=404, detail="Unknown report type")

    return generate_export_response(data, filename, format)
