from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class CPSEBase(BaseModel):
    cpse_code: str = Field(..., max_length=20, description="Unique code for the CPSE")
    cpse_name: str = Field(..., max_length=200, description="Full name of the CPSE")
    sector: Optional[str] = Field(None, max_length=100, description="Industrial sector")
    description: Optional[str] = Field(None, description="Detailed description")
    status: str = Field("ACTIVE", max_length=30, description="Status (ACTIVE, INACTIVE, SUSPENDED)")

class CPSECreate(CPSEBase):
    pass

class CPSEUpdate(BaseModel):
    cpse_name: Optional[str] = Field(None, max_length=200)
    sector: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None)
    status: Optional[str] = Field(None, max_length=30)

class CPSERead(CPSEBase):
    model_config = ConfigDict(from_attributes=True)

    cpse_id: str
    created_at: datetime
    updated_at: datetime
