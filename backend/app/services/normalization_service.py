import uuid
from sqlalchemy.orm import Session
from app.models.base import SourceMaterial, NormalizedMaterial
from app.core.normalization import TextNormalizer
from app.repositories.base import NormalizedMaterialRepo

class NormalizationService:
    def __init__(self, db: Session):
        self.db = db
        self.nm_repo = NormalizedMaterialRepo(db)

    def normalize_source_material(self, source_material: SourceMaterial) -> NormalizedMaterial:
        """
        Applies text normalization rules to a SourceMaterial and persists the output
        as a new NormalizedMaterial, capturing raw input, output, version, and method.
        """
        raw_desc = source_material.raw_description
        normalized_desc = TextNormalizer.normalize_description(raw_desc)
        
        nm = NormalizedMaterial(
            normalized_material_id=str(uuid.uuid4()),
            source_material_id=source_material.source_material_id,
            raw_description=raw_desc,
            normalized_description=normalized_desc,
            normalization_version=TextNormalizer.VERSION,
            normalization_method="Regex & Dictionary",
            # Copy forward optional fields from source
            canonical_uom=source_material.raw_uom,
            normalized_manufacturer=source_material.manufacturer,
            normalized_mpn=source_material.manufacturer_part_number
        )
        
        self.db.add(nm)
        self.db.commit()
        self.db.refresh(nm)
        return nm
