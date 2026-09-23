from typing import List, Dict, Any
from app.schemas.material import NormalizedMaterial
from app.schemas.data_quality import DataQualityIndicator

class DataQualityEngine:
    def __init__(self):
        pass

    def evaluate_material(self, material: NormalizedMaterial, has_classification: bool = False, attributes: Dict[str, Any] = None) -> DataQualityIndicator:
        """
        Evaluate a single material and produce a DataQualityIndicator.
        """
        flags = []
        
        # 1. Completeness
        # Simple heuristic: Does it have a manufacturer and MPN?
        fields_present = 0
        total_fields = 4 # category, manufacturer, mpn, description
        
        if material.category_code: fields_present += 1
        if material.normalized_manufacturer: fields_present += 1
        else: flags.append("missing_manufacturer")
            
        if material.normalized_mpn: fields_present += 1
        if material.normalized_description: fields_present += 1
        
        completeness = fields_present / total_fields
        
        # 2. Validity
        validity = 1.0
        if material.canonical_uom == "INVALID" or not material.canonical_uom:
            validity -= 0.5
            flags.append("invalid_uom")
            
        # 3. Standardization (Mock calculation)
        standardization = 1.0 if material.normalization_method == "deterministic" else 0.8
        
        # 4. Consistency (Mock calculation)
        consistency = 1.0
        
        # 5. Coverage
        attribute_coverage = 0.0
        if attributes:
            # Check for critical fields like pressure class if it's a valve
            if material.category_code == "VALVE" and "pressure_class" not in attributes:
                flags.append("missing_pressure_class")
                attribute_coverage = 0.5
            else:
                attribute_coverage = len(attributes) / max(len(attributes), 1) # simple ratio
        else:
            attribute_coverage = 0.0
            
        if not has_classification:
            flags.append("missing_classification")
            
        # 6. Uniqueness / Duplicate Rate (this requires cross-evaluation, mock for single item)
        uniqueness = 1.0
        if "LEGACY" in (material.normalized_mpn or ""):
            flags.append("duplicate_legacy_code")
            uniqueness = 0.0
        
        return DataQualityIndicator(
            material_id=material.normalized_material_id or "pending",
            completeness_score=completeness,
            uniqueness_score=uniqueness,
            validity_score=validity,
            consistency_score=consistency,
            standardization_score=standardization,
            attribute_coverage=attribute_coverage,
            flags=flags
        )
