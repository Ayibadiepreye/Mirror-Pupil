"""
Mirror Pupil v5.1 - Firebase Authentication
Handles Firebase JWT verification and user authorization.
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from firebase_admin import credentials, auth as firebase_auth, initialize_app
from loguru import logger

# Initialize Firebase Admin SDK
FIREBASE_INITIALIZED = False
SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").lower() == "true"

if SERVICE_ACCOUNT_PATH and os.path.exists(SERVICE_ACCOUNT_PATH):
    try:
        cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
        initialize_app(cred)
        FIREBASE_INITIALIZED = True
        logger.info("✓ Firebase Admin SDK initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
elif AUTH_DISABLED:
    logger.warning("⚠️ Auth disabled - running in dev mode")
else:
    logger.warning("⚠️ Firebase service account not found - auth will fail")


async def get_current_user_id(
    authorization: Optional[str] = Header(None, alias="Authorization")
) -> str:
    """
    Extract and verify Firebase JWT token.
    
    Returns:
        Firebase user_id (UID)
    
    Raises:
        HTTPException: If token is missing or invalid
    """
    # Dev mode bypass
    if AUTH_DISABLED:
        dev_user_id = os.getenv("DEV_USER_ID", "dev-super-admin")
        logger.debug(f"Auth disabled - using dev user: {dev_user_id}")
        return dev_user_id
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split("Bearer ")[1]
    
    try:
        decoded = firebase_auth.verify_id_token(token)
        user_id = decoded['uid']
        logger.debug(f"Authenticated user: {user_id}")
        return user_id
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    Get full user object from database.
    
    Args:
        user_id: Firebase UID from get_current_user_id
    
    Returns:
        User dict with is_super_admin, is_approved flags
    
    Raises:
        HTTPException: If user not found or not approved
    """
    from ..api.main import get_db
    from ...database import DatabaseManager
    
    # Get database manager from dependency injection
    db: DatabaseManager = get_db()
    user = await db.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not found in database. Please contact admin."
        )
    
    if not user['is_approved']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending admin approval"
        )
    
    return user


async def require_super_admin(
    user: dict = Depends(get_current_user)
) -> dict:
    """
    Require super admin role.
    
    Args:
        user: User dict from get_current_user
    
    Returns:
        User dict if super admin
    
    Raises:
        HTTPException: If not super admin
    """
    if not user.get('is_super_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return user
