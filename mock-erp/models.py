from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class HealthResponse(BaseModel):
    status: str
    message: str
    warning: str
    cpse_code: str

class MaterialResponse(BaseModel):
    cpse_code: str
    material_code: str
    description: str
    uom: str
    category: str
    subcategory: str
    manufacturer: str
    manufacturer_part_number: str
    attributes: Dict[str, Any]

class PaginatedResponse(BaseModel):
    total: int
    page: int
    limit: int
    data: List[MaterialResponse]

class SyncRequest(BaseModel):
    materials: List[Dict[str, Any]]

class SyncResponse(BaseModel):
    status: str
    received_count: int
    message: str
