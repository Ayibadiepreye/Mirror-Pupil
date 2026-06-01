"""
Mirror Pupil v5.1 - Notifications API Routes
Endpoints for system notifications and alerts.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from ...database import DatabaseManager
from ..main import get_db


router = APIRouter()


class NotificationResponse(BaseModel):
    """Response model for notification data."""
    id: int
    severity: str  # CRITICAL, HIGH, WARNING, INFO
    message: str
    timestamp: datetime
    account_key: str | None = None
    details: dict | None = None


# In-memory notification store (in production, use database)
_notifications: List[dict] = [
    {
        "id": 1,
        "severity": "INFO",
        "message": "Bot started successfully",
        "timestamp": datetime.now(),
        "account_key": None,
        "details": None
    }
]
_notification_id_counter = 2


@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    severity: str | None = None,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get all notifications, optionally filtered by severity.
    
    Args:
        severity: Optional severity filter (CRITICAL, HIGH, WARNING, INFO)
    
    Returns:
        List of notifications
    """
    try:
        notifications = _notifications.copy()
        
        if severity and severity != "ALL":
            notifications = [n for n in notifications if n["severity"] == severity]
        
        # Sort by timestamp descending (newest first)
        notifications.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return [NotificationResponse(**n) for n in notifications]
    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}"
        )


@router.post("/")
async def create_notification(
    severity: str,
    message: str,
    account_key: str | None = None,
    details: dict | None = None,
    db: DatabaseManager = Depends(get_db)
):
    """
    Create a new notification.
    
    Args:
        severity: Notification severity
        message: Notification message
        account_key: Optional account key
        details: Optional additional details
    
    Returns:
        Created notification
    """
    global _notification_id_counter
    
    try:
        notification = {
            "id": _notification_id_counter,
            "severity": severity,
            "message": message,
            "timestamp": datetime.now(),
            "account_key": account_key,
            "details": details
        }
        
        _notifications.append(notification)
        _notification_id_counter += 1
        
        logger.info(f"Created notification: {severity} - {message}")
        
        return NotificationResponse(**notification)
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}"
        )


@router.delete("/{notification_id}")
async def dismiss_notification(
    notification_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """
    Dismiss (delete) a notification.
    
    Args:
        notification_id: Notification ID
    
    Returns:
        Success message
    """
    try:
        global _notifications
        
        # Find and remove notification
        _notifications = [n for n in _notifications if n["id"] != notification_id]
        
        logger.info(f"Dismissed notification {notification_id}")
        
        return {"status": "success", "message": "Notification dismissed"}
    except Exception as e:
        logger.error(f"Failed to dismiss notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dismiss notification: {str(e)}"
        )


@router.delete("/")
async def clear_all_notifications(db: DatabaseManager = Depends(get_db)):
    """
    Clear all notifications.
    
    Returns:
        Success message
    """
    try:
        global _notifications
        count = len(_notifications)
        _notifications = []
        
        logger.info(f"Cleared {count} notifications")
        
        return {"status": "success", "message": f"Cleared {count} notifications"}
    except Exception as e:
        logger.error(f"Failed to clear notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear notifications: {str(e)}"
        )
