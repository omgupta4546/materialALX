from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.auth.rbac import require_role, Roles
from app.schemas.uom import UOMCreate, UOMRead, UOMConvertRequest, UOMConvertResponse
from app.services.uom_service import UOMService

router = APIRouter(prefix="/api/v1/uoms", tags=["UOM"])

@router.get("", response_model=List[UOMRead])
def list_uoms(
    dimension: Optional[str] = Query(None, description="Filter by dimension"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    List all Unit of Measures. Optionally filter by dimension or status.
    """
    svc = UOMService(db)
    return svc.get_all(dimension=dimension, status=status)


@router.post("", response_model=UOMRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_role([Roles.ADMIN, Roles.DATA_STEWARD]))])
def create_uom(
    uom_in: UOMCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Unit of Measure. Requires ADMIN or DATA_STEWARD role.
    """
    svc = UOMService(db)
    try:
        uom = svc.create(
            canonical_code=uom_in.canonical_code,
            name=uom_in.name,
            dimension=uom_in.dimension,
            aliases=uom_in.aliases,
            base_multiplier=uom_in.base_multiplier,
            is_base_unit=uom_in.is_base_unit,
            status=uom_in.status
        )
        return uom
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/convert", response_model=UOMConvertResponse)
def convert_uom(
    req: UOMConvertRequest,
    db: Session = Depends(get_db)
):
    """
    Convert a value from one UOM to another. 
    UOMs must share the same dimension.
    """
    svc = UOMService(db)
    try:
        result = svc.convert(req.value, req.from_uom, req.to_uom)
        return UOMConvertResponse(
            value=req.value,
            from_uom=req.from_uom,
            to_uom=req.to_uom,
            result=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
