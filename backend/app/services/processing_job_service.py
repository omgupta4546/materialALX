import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.repositories.processing_job_repo import ProcessingJobRepo
from app.schemas.processing_job import ProcessingJobCreate, ProcessingJobUpdate, ProcessingJobRead
from app.models.base import ProcessingJob

class ProcessingJobService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ProcessingJobRepo(db)

    def create_job(self, job_in: ProcessingJobCreate) -> ProcessingJobRead:
        job = ProcessingJob(
            job_id=str(uuid.uuid4()),
            job_type=job_in.job_type,
            status="PENDING",
            records_processed=0,
            total_records=0,
            successful=0,
            failed=0,
            errors={},
            details={},
            started_at=datetime.utcnow()
        )
        self.repo.db.add(job)
        self.repo.db.commit()
        self.repo.db.refresh(job)
        return ProcessingJobRead.model_validate(job)

    def get_job(self, job_id: str) -> ProcessingJobRead:
        job = self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return ProcessingJobRead.model_validate(job)

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        job = self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return {
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.records_processed,
            "total": job.total_records,
            "processed": job.records_processed,
            "successful": job.successful,
            "failed": job.failed,
            "current_stage": job.current_stage,
            "error_summary": job.errors,
            "started_at": job.started_at,
            "completed_at": job.completed_at
        }

    def update_job(self, job_id: str, job_update: ProcessingJobUpdate) -> ProcessingJobRead:
        job = self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        update_data = job_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(job, key, value)
            
        self.repo.db.commit()
        self.repo.db.refresh(job)
        return ProcessingJobRead.model_validate(job)

    def retry_job(self, job_id: str) -> ProcessingJobRead:
        job = self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status not in ["FAILED", "CANCELLED"]:
            raise HTTPException(status_code=400, detail="Can only retry failed or cancelled jobs")
        
        job.status = "PENDING"
        job.current_stage = "RETRYING"
        # Reset counters if starting from scratch, or keep them if resumable
        # Since it's resumable, we might just leave counters as is and rely on the worker to continue
        
        self.repo.db.commit()
        self.repo.db.refresh(job)
        return ProcessingJobRead.model_validate(job)

    def cancel_job(self, job_id: str) -> ProcessingJobRead:
        job = self.repo.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            raise HTTPException(status_code=400, detail="Job is already finished")
        
        job.status = "CANCELLED"
        job.completed_at = datetime.utcnow()
        self.repo.db.commit()
        self.repo.db.refresh(job)
        return ProcessingJobRead.model_validate(job)
