"""
Mirror Pupil v5.1 - User Management API Routes
Handle user registration, approval, and info retrieval.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager
from ...core.firebase_auth import get_current_user, get_current_user_id, require_super_admin
from ..main import get_db


router = APIRouter()


class UserResponse(BaseModel):
    """User information response."""
    user_id: str
    email: str
    display_name: str | None
    is_super_admin: bool
    is_approved: bool
    created_at: str
    
    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    """Request to create/register a user."""
    display_name: str | None = None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user_id: str = Depends(get_current_user_id),
    db: DatabaseManager = Depends(get_db)
):
    """
    Get current authenticated user's information.
    Creates user record if doesn't exist (first login).
    """
    try:
        # Try to get existing user
        user = await db.get_user_by_id(user_id)
        
        # If user doesn't exist, create from Firebase token
        if not user:
            # Get email from Firebase (would need to decode token again or pass through)
            # For now, create with minimal info
            from firebase_admin import auth as firebase_auth
            firebase_user = firebase_auth.get_user(user_id)
            
            user = await db.create_user(
                user_id=user_id,
                email=firebase_user.email,
                display_name=firebase_user.display_name,
                is_super_admin=False
            )
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user record"
                )
            
            logger.info(f"✓ Auto-created user record for {firebase_user.email}")
        
        # Convert datetime to string for JSON serialization
        if user and 'created_at' in user:
            user['created_at'] = user['created_at'].isoformat() if hasattr(user['created_at'], 'isoformat') else str(user['created_at'])
        
        return UserResponse(**user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user info: {str(e)}"
        )


@router.get("/pending", response_model=List[UserResponse])
async def list_pending_users(
    admin: dict = Depends(require_super_admin),
    db: DatabaseManager = Depends(get_db)
):
    """List users pending approval (super admin only)."""
    try:
        users = await db.get_pending_users()
        return [UserResponse(**u) for u in users]
    except Exception as e:
        logger.error(f"Failed to get pending users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending users: {str(e)}"
        )


@router.get("/all", response_model=List[UserResponse])
async def list_all_users(
    admin: dict = Depends(require_super_admin),
    db: DatabaseManager = Depends(get_db)
):
    """List all users (super admin only)."""
    try:
        users = await db.get_all_users()
        return [UserResponse(**u) for u in users]
    except Exception as e:
        logger.error(f"Failed to get all users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all users: {str(e)}"
        )


@router.post("/{user_id}/approve")
async def approve_user(
    user_id: str,
    admin: dict = Depends(require_super_admin),
    db: DatabaseManager = Depends(get_db)
):
    """Approve user (super admin only)."""
    try:
        success = await db.approve_user(user_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {"success": True, "message": "User approved"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve user: {str(e)}"
        )


class FcmTokenRequest(BaseModel):
    """Request to register FCM token."""
    fcm_token: str


@router.post("/register-fcm-token")
async def register_fcm_token(
    request: FcmTokenRequest,
    user: dict = Depends(get_current_user),
    db: DatabaseManager = Depends(get_db)
):
    """Register FCM token for push notifications."""
    try:
        user_id = user['user_id']
        success = await db.update_user_fcm_token(user_id, request.fcm_token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register FCM token"
            )
        
        logger.info(f"✓ Registered FCM token for user {user_id}")
        return {"success": True, "message": "FCM token registered"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to register FCM token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register FCM token: {str(e)}"
        )
