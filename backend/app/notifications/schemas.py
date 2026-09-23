from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid

NotificationType = Literal[
    "job_completed", 
    "review_required", 
    "engineering_review_required", 
    "mapping_approved", 
    "migration_ready", 
    "system_warning"
]

class NotificationCreate(BaseModel):
    user_id: str = Field(..., description="Target user ID. Use 'ALL' for global broadcast.")
    type: NotificationType
    title: str
    message: str
    action_url: Optional[str] = None

class NotificationResponse(NotificationCreate):
    id: str
    timestamp: datetime
    is_read: bool
