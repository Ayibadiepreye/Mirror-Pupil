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
from ...services.push_notifications import get_push_notification_service
from ..main import get_db
from ...core.firebase_auth import get_current_user


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
    created_at: str  # Changed to str for JSON serialization
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_db(cls, notification_dict: dict):
        """Create NotificationResponse from database dict, handling datetime conversion."""
        if notification_dict and 'created_at' in notification_dict:
            created_at = notification_dict['created_at']
            if hasattr(created_at, 'isoformat'):
                notification_dict['created_at'] = created_at.isoformat()
            elif not isinstance(created_at, str):
                notification_dict['created_at'] = str(created_at)
        return cls(**notification_dict)


@router.get("/", response_model=List[NotificationResponse])
async def get_all_notifications(
    account_key: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 100,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get all notifications for current user.
    Regular users see notifications for their accounts only.
    Super admin sees all notifications.
    
    Args:
        account_key: Optional account filter
        unread_only: Only return unread notifications
        limit: Maximum number of notifications
    
    Returns:
        List of notifications
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # If account_key specified, verify ownership
        if account_key:
            has_access = await db.verify_account_ownership(account_key, user_id, is_super_admin)
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this account"
                )
        
        notifications = await db.get_notifications(
            account_key=account_key,
            user_id=user_id,
            is_super_admin=is_super_admin,
            unread_only=unread_only,
            limit=limit
        )
        return [NotificationResponse.from_db(n) for n in notifications]
    except HTTPException:
        raise
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
        
        # Send push notification to mobile devices
        push_service = get_push_notification_service()
        if notification_data.account_key:
            # Get users who own this account
            users = await db.get_users_by_account(notification_data.account_key)
        else:
            # System-wide notification - send to all users with FCM tokens
            users = await db.get_all_users_with_fcm()
        
        fcm_tokens = [u['fcm_token'] for u in users if u.get('fcm_token')]
        if fcm_tokens:
            await push_service.send_to_multiple(
                fcm_tokens=fcm_tokens,
                title=notification_data.title,
                body=notification_data.message,
                notification_id=notification_id,
                data={
                    'category': notification_data.category,
                    'severity': notification_data.severity,
                }
            )
        
        return NotificationResponse.from_db(notification)
        
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
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Mark a notification as read. User must own the related account or be super admin.
    
    Args:
        notification_id: Notification ID
    
    Returns:
        Updated notification
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # Get notification to check ownership
        notification = await db.get_notification(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification not found: {notification_id}"
            )
        
        # If notification has account_key, verify ownership
        if notification.get('account_key'):
            has_access = await db.verify_account_ownership(notification['account_key'], user_id, is_super_admin)
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this notification"
                )
        
        success = await db.mark_notification_read(notification_id, True)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to mark notification as read"
            )
        
        notification = await db.get_notification(notification_id)
        return NotificationResponse.from_db(notification)
        
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
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Mark all notifications as read for current user.
    
    Args:
        account_key: Optional account filter
    
    Returns:
        Number of notifications marked as read
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # If account_key specified, verify ownership
        if account_key:
            has_access = await db.verify_account_ownership(account_key, user_id, is_super_admin)
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this account"
                )
        
        count = await db.mark_all_notifications_read(account_key, user_id, is_super_admin)
        return {"marked_read": count}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark all notifications as read: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all notifications as read: {str(e)}"
        )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Delete a notification. User must own the related account or be super admin.
    
    Args:
        notification_id: Notification ID
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # Get notification to check ownership
        notification = await db.get_notification(notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification not found: {notification_id}"
            )
        
        # If notification has account_key, verify ownership
        if notification.get('account_key'):
            has_access = await db.verify_account_ownership(notification['account_key'], user_id, is_super_admin)
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this notification"
                )
        
        success = await db.delete_notification(notification_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete notification"
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
