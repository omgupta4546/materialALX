from typing import List, Optional
from pydantic import BaseModel, Field

class UOMBase(BaseModel):
    canonical_code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    dimension: str = Field(..., max_length=50)
    aliases: List[str] = Field(default_factory=list)
    status: str = Field(default="ACTIVE", max_length=20)
    base_multiplier: float = Field(default=1.0)
    is_base_unit: bool = Field(default=False)

class UOMCreate(UOMBase):
    pass

class UOMRead(UOMBase):
    pass

class UOMConvertRequest(BaseModel):
    value: float
    from_uom: str
    to_uom: str

class UOMConvertResponse(BaseModel):
    value: float
    from_uom: str
    to_uom: str
    result: float
