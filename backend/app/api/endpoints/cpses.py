from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.cpse_service import CPSEService
from app.schemas.cpse import CPSECreate, CPSEUpdate, CPSERead
from app.utils.pagination import PaginationParams, get_pagination_params

router = APIRouter()

def get_cpse_service(db: Session = Depends(get_db)) -> CPSEService:
    return CPSEService(db)

@router.get("", response_model=List[CPSERead])
def list_cpses(
    pagination: PaginationParams = Depends(get_pagination_params), 
    service: CPSEService = Depends(get_cpse_service)
):
    return service.list_cpses(skip=pagination.offset, limit=pagination.limit)

@router.post("", response_model=CPSERead, status_code=status.HTTP_201_CREATED)
def create_cpse(cpse_in: CPSECreate, service: CPSEService = Depends(get_cpse_service)):
    return service.create_cpse(cpse_in)

@router.get("/{cpse_id}", response_model=CPSERead)
def get_cpse(cpse_id: str, service: CPSEService = Depends(get_cpse_service)):
    return service.get_cpse(cpse_id)

@router.put("/{cpse_id}", response_model=CPSERead)
def update_cpse(cpse_id: str, cpse_in: CPSEUpdate, service: CPSEService = Depends(get_cpse_service)):
    return service.update_cpse(cpse_id, cpse_in)

@router.delete("/{cpse_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cpse(cpse_id: str, service: CPSEService = Depends(get_cpse_service)):
    service.delete_cpse(cpse_id)
