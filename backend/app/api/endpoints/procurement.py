from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.base import (
    NationalMaterial, MaterialMapping, SourceMaterial, ProcurementRecord
)
from app.auth.rbac import require_role, Roles, enforce_cpse_tenant

router = APIRouter()

ALL_ROLES = [Roles.ADMIN, Roles.DATA_STEWARD, Roles.ENGINEER, Roles.AUDITOR, Roles.CPSE_USER]

@router.get("/intelligence", dependencies=[Depends(require_role(ALL_ROLES))])
def get_procurement_intelligence(cpse_code: Optional[str] = Depends(enforce_cpse_tenant), db: Session = Depends(get_db)):
    """
    Returns procurement intelligence for each National Material.
    Metrics:
    - CPSE count
    - legacy code count (redundancy count = legacy code count - 1)
    - aggregated quantity
    - historical spend
    - supplier count
    - opportunity priority
    """
    
    # We query from NationalMaterial and join MaterialMapping, SourceMaterial, and ProcurementRecord
    q = db.query(
        NationalMaterial.national_material_id,
        NationalMaterial.national_material_code,
        NationalMaterial.canonical_description,
        func.count(func.distinct(SourceMaterial.cpse_id)).label("cpse_count"),
        func.count(func.distinct(SourceMaterial.source_material_id)).label("legacy_code_count"),
        func.sum(ProcurementRecord.quantity).label("total_demand"),
        func.sum(ProcurementRecord.total_spend).label("historical_spend"),
        func.count(func.distinct(ProcurementRecord.supplier)).label("supplier_count")
    )
    
    q = q.filter(MaterialMapping.status == "APPROVED")
    
    q = q.join(MaterialMapping, NationalMaterial.national_material_id == MaterialMapping.national_material_id, isouter=True)
    q = q.join(SourceMaterial, MaterialMapping.source_material_id == SourceMaterial.source_material_id)
    
    if cpse_code:
        q = q.filter(SourceMaterial.cpse_id == cpse_code)
        
    q = q.join(ProcurementRecord, SourceMaterial.source_material_id == ProcurementRecord.source_material_id, isouter=True)
    
    rows = q.group_by(
        NationalMaterial.national_material_id,
        NationalMaterial.national_material_code,
        NationalMaterial.canonical_description
    ).order_by(func.sum(ProcurementRecord.total_spend).desc()).all()
    
    results = []
    for r in rows:
        spend = float(r.historical_spend or 0.0)
        cpse_count = r.cpse_count or 0
        legacy_count = r.legacy_code_count or 0
        supplier_count = r.supplier_count or 0
        total_demand = float(r.total_demand or 0.0)
        
        # Priority logic: High if Spend > 1M and multiple CPSEs.
        if spend > 1_000_000 and cpse_count > 1:
            priority = "HIGH"
        elif spend > 100_000 or cpse_count > 1:
            priority = "MEDIUM"
        else:
            priority = "LOW"
            
        # Determine opportunities
        potential_consolidation = False
        explanation = "No actionable consolidation opportunities identified from historical data."
        
        if spend > 0:
            if cpse_count > 1:
                potential_consolidation = True
                explanation = f"Consolidating {legacy_count} redundant codes across {cpse_count} CPSEs with a historical spend of ${spend:,.2f} provides high leverage for volume negotiation."
            elif supplier_count > 1:
                potential_consolidation = True
                explanation = f"Rationalizing {supplier_count} disparate suppliers for a combined demand of {total_demand:,.0f} units could yield contract efficiencies."
            elif legacy_count > 1:
                potential_consolidation = True
                explanation = f"Internal redundancy detected: {legacy_count} separate legacy codes are being procured for the same national material."

        results.append({
            "national_material_id": r.national_material_id,
            "national_material_code": r.national_material_code,
            "description": r.canonical_description,
            "cpse_count": cpse_count,
            "legacy_code_count": legacy_count,
            "redundancy_count": max(0, legacy_count - 1),
            "total_demand": total_demand,
            "historical_spend": spend,
            "supplier_count": supplier_count,
            "opportunity_priority": priority,
            "potential_consolidation_opportunities": potential_consolidation,
            "opportunity_explanation": explanation
        })

        
    return results
