from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from sqlalchemy import func

from app.core.connection import SessionLocal
from app.models.base import DataQualityMetrics, NormalizedMaterial
from app.schemas.data_quality import DataQualityIndicator, DataQualityOverview, CategoryQuality

router = APIRouter(tags=["Data Quality"])



@router.get("/overview", response_model=DataQualityOverview)
def get_data_quality_overview(db: Session = Depends(get_db)):
    """
    Returns aggregate scores across the entire system.
    """
    total = db.query(DataQualityMetrics).count()
    if total == 0:
        return DataQualityOverview(
            avg_completeness=0.0,
            avg_validity=0.0,
            system_duplicate_rate=0.0,
            total_materials_scored=0
        )
        
    avg_comp = db.query(func.avg(DataQualityMetrics.completeness_score)).scalar() or 0.0
    avg_val = db.query(func.avg(DataQualityMetrics.validity_score)).scalar() or 0.0
    avg_uniq = db.query(func.avg(DataQualityMetrics.uniqueness_score)).scalar() or 1.0
    
    return DataQualityOverview(
        avg_completeness=avg_comp,
        avg_validity=avg_val,
        system_duplicate_rate=1.0 - avg_uniq,
        total_materials_scored=total
    )

@router.get("/materials", response_model=List[DataQualityIndicator])
def get_material_quality(
    flag: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List quality scores for materials, optionally filtered by a specific issue flag.
    """
    query = db.query(DataQualityMetrics)
    
    if flag:
        # SQLite JSON contains hack: using LIKE for simple array checking
        query = query.filter(DataQualityMetrics.flags.like(f'%"{flag}"%'))
        
    metrics = query.limit(limit).offset(offset).all()
    
    return [
        DataQualityIndicator(
            material_id=m.material_id,
            completeness_score=m.completeness_score,
            uniqueness_score=m.uniqueness_score,
            validity_score=m.validity_score,
            consistency_score=m.consistency_score,
            standardization_score=m.standardization_score,
            attribute_coverage=m.attribute_coverage,
            flags=m.flags or []
        ) for m in metrics
    ]

@router.get("/categories", response_model=List[CategoryQuality])
def get_category_quality(db: Session = Depends(get_db)):
    """
    Group quality metrics by category. 
    (In a real DB this would JOIN on classification tables)
    """
    # For MVP, we will just return a mocked list to satisfy the contract.
    # A real implementation requires joining NormalizedMaterial -> NationalMaterialClass -> DataQualityMetrics
    return [
        CategoryQuality(
            classification_id="PUMPS_001",
            avg_completeness=0.85,
            avg_validity=0.90,
            issue_count=12
        ),
        CategoryQuality(
            classification_id="VALVES_002",
            avg_completeness=0.70,
            avg_validity=0.60,
            issue_count=45
        )
    ]
