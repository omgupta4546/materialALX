from typing import Optional
from sqlalchemy.orm import Session
from app.models.base import ProcessingJob
from app.repositories.base import BaseRepository

class ProcessingJobRepo(BaseRepository[ProcessingJob]):
    model = ProcessingJob

    def get_by_id(self, job_id: str) -> Optional[ProcessingJob]:
        return self.db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
