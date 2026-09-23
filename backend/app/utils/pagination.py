from typing import Generic, TypeVar, List, Optional
from pydantic import BaseModel, Field
from fastapi import Query

T = TypeVar("T")

class Page(BaseModel, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int
    
class PaginationParams(BaseModel):
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)
    
def get_pagination_params(
    limit: int = Query(50, ge=1, le=100, description="Page size limit"),
    offset: int = Query(0, ge=0, description="Page offset")
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)
