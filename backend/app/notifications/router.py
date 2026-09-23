from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
import uuid

from app.notifications.schemas import NotificationCreate, NotificationResponse
from app.notifications.providers import ACTIVE_PROVIDERS, IN_MEMORY_NOTIFICATIONS
from app.auth.router import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])

@router.post("", response_model=NotificationResponse)
def trigger_notification(payload: NotificationCreate):
    """
    Internal/Webhook endpoint to trigger a notification.
    Iterates through all configured active providers.
    """
    notification = NotificationResponse(
        id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        is_read=False,
        **payload.dict()
    )
    
    for provider in ACTIVE_PROVIDERS:
        provider.send(notification)
        
    return notification

@router.get("", response_model=List[NotificationResponse])
def get_my_notifications(current_user: dict = Depends(get_current_user)):
    """
    Retrieve in-app notifications for the authenticated user.
    """
    user_id = current_user["user_id"]
    
    # Return user-specific and global broadcast notifications
    user_notifs = [
        n for n in IN_MEMORY_NOTIFICATIONS 
        if n.user_id == user_id or n.user_id == "ALL"
    ]
    
    # Sort newest first
    user_notifs.sort(key=lambda x: x.timestamp, reverse=True)
    return user_notifs

@router.post("/{notification_id}/read")
def mark_as_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    
    for n in IN_MEMORY_NOTIFICATIONS:
        if n.id == notification_id:
            if n.user_id != user_id and n.user_id != "ALL":
                raise HTTPException(status_code=403, detail="Cannot access this notification")
            n.is_read = True
            return {"status": "success", "message": "Notification marked as read"}
            
    raise HTTPException(status_code=404, detail="Notification not found")
