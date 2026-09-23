from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime

class ProcessingJobBase(BaseModel):
    job_type: str = "UPLOAD_PROCESSING"

class ProcessingJobCreate(ProcessingJobBase):
    pass

class ProcessingJobUpdate(BaseModel):
    status: Optional[str] = None
    records_processed: Optional[int] = None
    total_records: Optional[int] = None
    successful: Optional[int] = None
    failed: Optional[int] = None
    current_stage: Optional[str] = None
    errors: Optional[Dict[str, Any]] = None
    details: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None

class ProcessingJobRead(ProcessingJobBase):
    job_id: str
    status: str
    records_processed: int
    total_records: int
    successful: int
    failed: int
    current_stage: Optional[str]
    errors: Dict[str, Any]
    details: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
