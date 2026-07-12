"""
Mirror Pupil v5.1 - Channels API Routes
CRUD operations for signal channels.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager, Channel
from ...core.firebase_auth import get_current_user, require_super_admin
from ..dependencies import get_db


router = APIRouter()


# Request/Response Models
class ChannelCreate(BaseModel):
    """Request model for creating a new channel."""
    channel_id: int
    display_name: str
    signal_prefix: str
    entry_logic_module: str
    management_logic_module: str
    priority: int = 10
    enabled: bool = True
    notes: Optional[str] = None


class ChannelUpdate(BaseModel):
    """Request model for updating a channel."""
    display_name: Optional[str] = None
    signal_prefix: Optional[str] = None
    entry_logic_module: Optional[str] = None
    management_logic_module: Optional[str] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    notes: Optional[str] = None


class ChannelResponse(BaseModel):
    """Response model for channel data."""
    channel_id: int
    display_name: str
    signal_prefix: str
    entry_logic_module: str
    management_logic_module: str
    priority: int
    enabled: bool
    notes: Optional[str]
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[ChannelResponse])
async def get_all_channels(
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get all channels.
    All users can view channels.
    
    Returns:
        List of all channels
    """
    try:
        channels = await db.get_all_channels()
        return [ChannelResponse.model_validate(ch) for ch in channels]
    except Exception as e:
        logger.error(f"Failed to get channels: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get channels: {str(e)}"
        )


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: int,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get a specific channel by ID.
    All users can view channels.
    
    Args:
        channel_id: Numeric Telegram channel ID
    
    Returns:
        Channel details
    """
    try:
        channel = await db.get_channel(channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel not found: {channel_id}"
            )
        return ChannelResponse.model_validate(channel)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get channel {channel_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get channel: {str(e)}"
        )


@router.post("/", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    channel_data: ChannelCreate,
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Create a new channel.
    **Super admin only.**
    
    Args:
        channel_data: Channel creation data
    
    Returns:
        Created channel details
    """
    try:
        # Create Channel object
        channel = Channel(
            channel_id=channel_data.channel_id,
            display_name=channel_data.display_name,
            signal_prefix=channel_data.signal_prefix,
            entry_logic_module=channel_data.entry_logic_module,
            management_logic_module=channel_data.management_logic_module,
            priority=channel_data.priority,
            enabled=channel_data.enabled,
            notes=channel_data.notes
        )
        
        # Add to database
        success = await db.add_channel(channel)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create channel (may already exist)"
            )
        
        # Sync channel subscriptions
        await db.sync_channel_subscriptions()
        
        logger.info(f"✓ Created channel: {channel_data.display_name} ({channel_data.channel_id})")
        return ChannelResponse.model_validate(channel)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create channel: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create channel: {str(e)}"
        )


@router.post("/{channel_id}/enable", response_model=ChannelResponse)
async def enable_channel(
    channel_id: int,
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Enable a channel (start listening to messages).
    **Super admin only.**
    
    Args:
        channel_id: Channel ID
    
    Returns:
        Updated channel details
    """
    try:
        success = await db.update_channel_enabled(channel_id, True)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel not found: {channel_id}"
            )
        
        channel = await db.get_channel(channel_id)
        logger.info(f"✓ Enabled channel: {channel_id}")
        return ChannelResponse.model_validate(channel)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable channel {channel_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable channel: {str(e)}"
        )


@router.post("/{channel_id}/disable", response_model=ChannelResponse)
async def disable_channel(
    channel_id: int,
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Disable a channel (stop listening to messages).
    **Super admin only.**
    
    Args:
        channel_id: Channel ID
    
    Returns:
        Updated channel details
    """
    try:
        success = await db.update_channel_enabled(channel_id, False)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel not found: {channel_id}"
            )
        
        channel = await db.get_channel(channel_id)
        logger.info(f"✓ Disabled channel: {channel_id}")
        return ChannelResponse.model_validate(channel)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable channel {channel_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable channel: {str(e)}"
        )


@router.put("/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    channel_data: ChannelUpdate,
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Update an existing channel.
    **Super admin only.**
    
    Args:
        channel_id: Channel ID
        channel_data: Channel update data
    
    Returns:
        Updated channel details
    """
    try:
        # Get existing channel
        existing = await db.get_channel(channel_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel not found: {channel_id}"
            )
        
        # Build update dict with only provided fields
        updates = {}
        if channel_data.display_name is not None:
            updates['display_name'] = channel_data.display_name
        if channel_data.signal_prefix is not None:
            updates['signal_prefix'] = channel_data.signal_prefix
        if channel_data.entry_logic_module is not None:
            updates['entry_logic_module'] = channel_data.entry_logic_module
        if channel_data.management_logic_module is not None:
            updates['management_logic_module'] = channel_data.management_logic_module
        if channel_data.priority is not None:
            updates['priority'] = channel_data.priority
        if channel_data.enabled is not None:
            updates['enabled'] = channel_data.enabled
        if channel_data.notes is not None:
            updates['notes'] = channel_data.notes
        
        # Update in database
        success = await db.update_channel(channel_id, **updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update channel"
            )
        
        # Get updated channel
        updated = await db.get_channel(channel_id)
        logger.info(f"✓ Updated channel {channel_id}")
        return ChannelResponse.model_validate(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update channel {channel_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update channel: {str(e)}"
        )


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def patch_channel(
    channel_id: int,
    channel_data: ChannelUpdate,
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Partially update a channel (PATCH endpoint).
    Same as PUT but more explicit about partial updates.
    **Super admin only.**
    
    Args:
        channel_id: Channel ID
        channel_data: Channel update data
    
    Returns:
        Updated channel details
    """
    return await update_channel(channel_id, channel_data, db, admin)


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_channel(
    channel_id: int,
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Delete a channel and all related data.
    **Super admin only.**
    
    Args:
        channel_id: Channel ID
    """
    try:
        # Check if channel exists
        channel = await db.get_channel(channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel not found: {channel_id}"
            )
        
        # Delete channel and all related data
        success = await db.delete_channel(channel_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete channel"
            )
        
        logger.info(f"✓ Deleted channel {channel_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete channel {channel_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete channel: {str(e)}"
        )
