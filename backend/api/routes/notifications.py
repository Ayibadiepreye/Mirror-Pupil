"""
Mirror Pupil v5.1 - Notifications API Routes
Real-time notifications for GUI display.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from ...database import DatabaseManager
from ..main import get_db


router = APIRouter()


class NotificationCreate(BaseModel):
    """Request model for creating a notification."""
    account_key: Optional[str] = None
    category: str  # SIGNAL, EXECUTION, MANAGEMENT, BREACH, SYSTEM
    severity: str  # INFO, WARNING, ERROR, CRITICAL
    title: str
    message: str
    metadata: Optional[dict] = None


class NotificationResponse(BaseModel):
    """Response model for notification data."""
    notification_id: int
    account_key: Optional[str]
    category: str
    severity: str
    title: str
    message: str
    metadata: Optional[dict]
    read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[NotificationResponse])
async def get_all_notifications(
    account_key: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 100,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get all notifications with optional filtering.
    
    Args:
        account_key: Optional account filter
        unread_only: Only return unread notifications
        limit: Maximum number of notifications
    
    Returns:
        List of notifications
    """
    try:
        notifications = await db.get_notifications(
            account_key=account_key,
            unread_only=unread_only,
            limit=limit
        )
        return [NotificationResponse(**n) for n in notifications]
    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notifications: {str(e)}"
        )


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    db: DatabaseManager = Depends(get_db)
):
    """
    Create a new notification.
    
    Args:
        notification_data: Notification creation data
    
    Returns:
        Created notification
    """
    try:
        notification_id = await db.add_notification(
            account_key=notification_data.account_key,
            category=notification_data.category,
            severity=notification_data.severity,
            title=notification_data.title,
            message=notification_data.message,
            metadata=notification_data.metadata
        )
        
        if not notification_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create notification"
            )
        
        # Get created notification
        notification = await db.get_notification(notification_id)
        logger.info(f"✓ Created notification: {notification_data.title}")
        return NotificationResponse(**notification)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}"
        )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """
    Mark a notification as read.
    
    Args:
        notification_id: Notification ID
    
    Returns:
        Updated notification
    """
    try:
        success = await db.mark_notification_read(notification_id, True)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification not found: {notification_id}"
            )
        
        notification = await db.get_notification(notification_id)
        return NotificationResponse(**notification)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification as read: {str(e)}"
        )


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    account_key: Optional[str] = None,
    db: DatabaseManager = Depends(get_db)
):
    """
    Mark all notifications as read.
    
    Args:
        account_key: Optional account filter
    
    Returns:
        Number of notifications marked as read
    """
    try:
        count = await db.mark_all_notifications_read(account_key)
        return {"marked_read": count}
    except Exception as e:
        logger.error(f"Failed to mark all notifications as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """
    Delete a notification.
    
    Args:
        notification_id: Notification ID
    """
    try:
        success = await db.delete_notification(notification_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification not found: {notification_id}"
            )
        logger.info(f"✓ Deleted notification {notification_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )


@router.post("/cleanup")
async def cleanup_old_notifications(db: DatabaseManager = Depends(get_db)):
    """
    Manually trigger cleanup of notifications older than 48 hours.
    
    Returns:
        Number of notifications deleted
    """
    try:
        count = await db.cleanup_old_notifications()
        return {"deleted": count}
    except Exception as e:
        logger.error(f"Failed to cleanup notifications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup notifications: {str(e)}"
        )
