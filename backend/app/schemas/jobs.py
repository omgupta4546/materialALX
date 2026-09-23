from typing import Dict, Any, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class JobCreate(BaseModel):
    job_type: str
    target_ids: list[str]
    config: Optional[Dict[str, Any]] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    job_type: str
    current_stage: Optional[str] = None
    records_processed: int
    total_records: int
    successful: int
    failed: int

class JobRead(JobStatusResponse):
    errors: Dict[str, Any]
    details: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
