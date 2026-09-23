from pydantic import BaseModel, ConfigDict, Field
from typing import Any, List, Optional


class ValidationError(BaseModel):
    row: int
    error: str
    severity: str = "ERROR"
    data: Optional[dict[str, Any]] = None


class UploadResponse(BaseModel):
    job_id: str
    upload_id: str
    status: str
    total_records: int
    accepted_records: int
    rejected_records: int
    validation_errors: List[ValidationError] = Field(default_factory=list)
