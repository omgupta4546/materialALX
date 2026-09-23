from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

class SourceMaterialBase(BaseModel):
    cpse_id: str
    legacy_material_code: str
    raw_description: Optional[str] = None
    raw_uom: Optional[str] = None
    raw_category: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_part_number: Optional[str] = None
    raw_specification: Optional[str] = None
    plant: Optional[str] = None
    source_system: Optional[str] = None
    source_file: Optional[str] = None
    source_record_reference: Optional[str] = None

class SourceMaterialCreate(SourceMaterialBase):
    pass

class SourceMaterialRead(SourceMaterialBase):
    source_material_id: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
