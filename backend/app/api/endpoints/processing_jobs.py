from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.processing_job import ProcessingJobCreate, ProcessingJobRead
from app.services.processing_job_service import ProcessingJobService
from typing import Dict, Any

router = APIRouter()

def get_job_service(db: Session = Depends(get_db)) -> ProcessingJobService:
    return ProcessingJobService(db)

@router.post("", response_model=ProcessingJobRead, status_code=201)
def create_job(
    job_in: ProcessingJobCreate,
    service: ProcessingJobService = Depends(get_job_service)
):
    return service.create_job(job_in)

@router.get("/{job_id}", response_model=ProcessingJobRead)
def get_job(
    job_id: str,
    service: ProcessingJobService = Depends(get_job_service)
):
    return service.get_job(job_id)

@router.get("/{job_id}/status", response_model=Dict[str, Any])
def get_job_status(
    job_id: str,
    service: ProcessingJobService = Depends(get_job_service)
):
    return service.get_job_status(job_id)

@router.post("/{job_id}/retry", response_model=ProcessingJobRead)
def retry_job(
    job_id: str,
    service: ProcessingJobService = Depends(get_job_service)
):
    return service.retry_job(job_id)

@router.post("/{job_id}/cancel", response_model=ProcessingJobRead)
def cancel_job(
    job_id: str,
    service: ProcessingJobService = Depends(get_job_service)
):
    return service.cancel_job(job_id)
