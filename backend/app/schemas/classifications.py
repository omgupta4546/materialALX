from typing import Optional, List, ForwardRef
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class ClassificationBase(BaseModel):
    code: str = Field(..., max_length=50)
    name: str = Field(..., max_length=150)
    description: Optional[str] = None
    level: int = 0
    status: str = "ACTIVE"

class ClassificationCreate(ClassificationBase):
    parent_id: Optional[str] = None

class ClassificationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ClassificationMove(BaseModel):
    new_parent_id: Optional[str] = None

class ClassificationRead(ClassificationBase):
    classification_id: str
    parent_id: Optional[str] = None
    version: int
    is_latest: bool

    model_config = ConfigDict(from_attributes=True)

ClassificationNode = ForwardRef('ClassificationNode')

class ClassificationNode(ClassificationRead):
    children: List[ClassificationNode] = Field(default_factory=list)

ClassificationNode.model_rebuild()
