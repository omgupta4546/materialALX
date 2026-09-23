import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status, Request, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_redis_pool
from arq import ArqRedis
from app.services.upload_service import UploadService
from app.schemas.upload import UploadResponse, ValidationError

log = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a materials file (CSV / XLSX / JSON)",
    description=(
        "Accepts a materials file and a target CPSE ID. "
        "Validates, parses, and persists each row as an immutable SourceMaterial record in the background. "
        "Returns a job summary with QUEUED status."
    ),
)
async def upload_materials(
    request: Request,
    file: UploadFile = File(..., description="CSV, XLSX, or JSON file"),
    cpse_id: str = Form(..., description="CPSE UUID that owns these materials"),
    db: Session = Depends(get_db),
    redis_pool: ArqRedis = Depends(get_redis_pool)
) -> UploadResponse:
    """
    Validates file type and size before delegating to UploadService.
    """
    log.info(f"Received upload: filename={file.filename!r}, cpse_id={cpse_id!r}")
    
    ALLOWED_TYPES = [
        "text/csv", 
        "application/vnd.ms-excel", 
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        "application/json"
    ]
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only CSV, Excel, and JSON are allowed.")

    MAX_FILE_SIZE = 50 * 1024 * 1024 # 50 MB
    
    content = await file.read()
    
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 50MB.")

    svc = UploadService(db)

    try:
        # We process preflight and queueing synchronously
        result = await svc.process_upload_async(content, file.filename or "upload", cpse_id, redis_pool)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    db.commit()

    return UploadResponse(
        job_id=result.job_id,
        upload_id=result.upload_id,
        status="QUEUED",
        total_records=0,
        accepted_records=0,
        rejected_records=0,
        validation_errors=[],
    )
