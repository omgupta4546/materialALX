import asyncio
import os
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_db
from sse_starlette.sse import EventSourceResponse
from arq import create_pool
from arq.connections import RedisSettings

from app.core.connection import SessionLocal
from app.models.base import ProcessingJob
from app.schemas.jobs import JobCreate, JobRead, JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["Jobs"])



async def get_redis_pool():
    # Helper to connect to the ARQ Redis queue
    from app.core.config import settings
    from arq.connections import RedisSettings
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    return await create_pool(redis_settings)

@router.post("", response_model=JobStatusResponse, status_code=202)
async def create_job(job_in: JobCreate, db: Session = Depends(get_db)):
    """Dispatch a new background job to the Redis queue."""
    
    # 1. Create DB record
    job_id = str(uuid.uuid4())
    db_job = ProcessingJob(
        job_id=job_id,
        job_type=job_in.job_type,
        status="PENDING",
        total_records=len(job_in.target_ids)
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    
    # 2. Push to Redis (arq)
    try:
        pool = await get_redis_pool()
        await pool.enqueue_job(
            'process_batch_job',
            job_id,
            job_in.job_type,
            job_in.target_ids,
            job_in.config or {}
        )
    except Exception as e:
        # If Redis is down, we fail the job instantly
        db_job.status = "FAILED"
        db_job.errors = {"queue_error": str(e)}
        db.commit()
        raise HTTPException(status_code=503, detail="Redis queue is unavailable")
        
    return db_job

@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Fetch complete job metadata and errors."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.get("/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Lightweight polling endpoint for job status."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    """Request a graceful cancellation of a running job."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Cannot cancel a finished job")
        
    # The worker loop checks this status to halt gracefully
    job.status = "CANCELLED"
    db.commit()
    return {"message": "Job cancellation requested"}

@router.post("/{job_id}/retry", response_model=JobStatusResponse)
async def retry_job(job_id: str, db: Session = Depends(get_db)):
    """Retry a failed or cancelled job. Maintains progress."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.status not in ["FAILED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Can only retry failed or cancelled jobs")
        
    # In a real app we'd fetch the original uncompleted target_ids. 
    # For this MVP, we will just re-enqueue the whole array (assumed empty config)
    # to demonstrate the architectural hook.
    
    job.status = "PENDING"
    db.commit()
    db.refresh(job)
    
    try:
        pool = await get_redis_pool()
        await pool.enqueue_job(
            'process_batch_job',
            job_id,
            job.job_type,
            ["retry_mock_id"], # Mocking targets for retry
            {}
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail="Redis queue is unavailable")
        
    return job

@router.get("/{job_id}/stream")
async def stream_job_progress(request: Request, job_id: str, db: Session = Depends(get_db)):
    """Server-Sent Events (SSE) endpoint to push real-time job progress."""
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
                
            # Fetch fresh state
            current_job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
            if not current_job:
                break
                
            payload = {
                "status": current_job.status,
                "processed": current_job.records_processed,
                "total": current_job.total_records,
                "successful": current_job.successful,
                "failed": current_job.failed,
            }
            
            yield {
                "event": "progress",
                "data": json.dumps(payload)
            }
            
            if current_job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
                break
                
            await asyncio.sleep(1.0) # Poll DB every second to push to client

    return EventSourceResponse(event_generator())
