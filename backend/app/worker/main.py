import asyncio
import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any

from arq import Worker
from sqlalchemy.orm import Session
from app.core.connection import engine
from app.models.base import ProcessingJob, SourceMaterial
from app.ai.pipeline import MatchingPipeline
from app.services.upload_service import UploadService, UploadResult, _parse_file

logger = logging.getLogger(__name__)

async def startup(ctx):
    logger.info("Worker starting up...")
    
async def shutdown(ctx):
    logger.info("Worker shutting down...")

async def process_upload_job(ctx, content: bytes, filename: str, cpse_id: str, job_id: str, upload_id: str):
    """
    Background task to parse an uploaded file, save SourceMaterials, and run the MatchingPipeline.
    Handles individual failures without crashing the entire job.
    """
    logger.info(f"Starting upload processing job {job_id} for file {filename}")
    
    with Session(engine) as db:
        job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
        if not job:
            logger.error(f"ProcessingJob {job_id} not found in DB!")
            return
            
        result = UploadResult(job_id=job_id, upload_id=upload_id)
        svc = UploadService(db)

        # 1. Parse File
        try:
            raw_rows = _parse_file(content, filename)
        except ValueError as parse_err:
            job.status = "FAILED"
            job.errors = {"error": str(parse_err)}
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        if not raw_rows:
            job.status = "COMPLETED"
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        # 2. Persist SourceMaterials
        job.status = "RUNNING"
        job.current_stage = "SAVING_SOURCE_MATERIALS"
        job.started_at = datetime.utcnow()
        db.commit()

        try:
            svc._process_rows(raw_rows, cpse_id, filename, job, result)
        except Exception as exc:
            logger.exception("Unexpected error during row processing")
            job.status = "FAILED"
            job.errors = {"error": str(exc)}
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        # 3. AI Matching Pipeline
        job.current_stage = "AI_MATCHING"
        db.commit()

        # Fetch the newly created source materials for this file
        source_materials = db.query(SourceMaterial).filter(
            SourceMaterial.cpse_id == cpse_id,
            SourceMaterial.source_file == filename
        ).all()
        
        target_ids = [sm.source_material_id for sm in source_materials]
        
        # Reset progress counters for AI pipeline phase
        job.records_processed = 0
        job.successful = 0
        job.failed = 0
        db.commit()

        pipeline = MatchingPipeline(db)
        
        for idx, target_id in enumerate(target_ids):
            # Check for cancellation before processing next item
            db.refresh(job)
            if job.status == "CANCELLED":
                logger.warning(f"Job {job_id} was cancelled by user.")
                return
                
            try:
                best_match_id = pipeline.process(target_id)
                job.successful += 1
            except Exception as e:
                logger.error(f"Item {target_id} failed: {str(e)}")
                job.failed += 1
                errors = dict(job.errors) if job.errors else {}
                errors[target_id] = str(e)
                job.errors = errors
                
            finally:
                job.records_processed += 1
                if idx % 10 == 0:
                    db.commit()
                    
        # 4. Finalise Job
        if job.failed == job.total_records and job.total_records > 0:
            job.status = "FAILED"
            job.current_stage = "ALL_ITEMS_FAILED"
        else:
            job.status = "COMPLETED"
            job.current_stage = "FINISHED"
            
        job.completed_at = datetime.utcnow()
        
        details = dict(job.details) if job.details else {}
        details.update({
            "total_raw_records": result.total_records,
            "accepted_source_records": result.accepted_records,
            "rejected_source_records": result.rejected_records,
        })
        job.details = details
        
        db.commit()
        logger.info(f"Job {job_id} finished. Success: {job.successful}, Failed: {job.failed}")


class WorkerSettings:
    functions = [process_upload_job]
    on_startup = startup
    on_shutdown = shutdown
    # Redis configuration from environment
    from worker.config import worker_config
    from arq.connections import RedisSettings
    redis_settings = RedisSettings.from_dsn(worker_config.REDIS_URL)
