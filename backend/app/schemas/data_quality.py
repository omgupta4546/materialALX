from typing import List
from pydantic import BaseModel

class DataQualityIndicator(BaseModel):
    material_id: str
    completeness_score: float
    uniqueness_score: float
    validity_score: float
    consistency_score: float
    standardization_score: float
    attribute_coverage: float
    flags: List[str]

class DataQualityOverview(BaseModel):
    avg_completeness: float
    avg_validity: float
    system_duplicate_rate: float
    total_materials_scored: int

class CategoryQuality(BaseModel):
    classification_id: str
    avg_completeness: float
    avg_validity: float
    issue_count: int
