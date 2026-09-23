from pydantic import BaseModel, ValidationError
from typing import Optional

class CPSEValidator(BaseModel):
    cpse_code: str
    cpse_name: str
    sector: Optional[str] = None
    description: Optional[str] = None

class SourceMaterialValidator(BaseModel):
    material_code: str
    cpse_code: str
    description: str
    uom: Optional[str] = None
    plant: Optional[str] = None
    
def validate_dict(schema, data: dict) -> bool:
    try:
        schema(**data)
        return True
    except ValidationError:
        return False
