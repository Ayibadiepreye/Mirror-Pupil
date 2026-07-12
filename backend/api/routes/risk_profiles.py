"""
Mirror Pupil v5.1 - Risk Profiles API Routes
CRUD operations for risk management profiles.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager, RiskProfile
from ...core.firebase_auth import get_current_user, require_super_admin
from ..dependencies import get_db


router = APIRouter()


class RiskProfileCreate(BaseModel):
    """Request model for creating a risk profile."""
    profile_name: str
    is_default: bool = False
    max_risk_per_trade_pct: float
    daily_loss_pct: float
    daily_trailing: bool
    overall_loss_pct: float
    overall_trailing: bool
    overall_trail_from_closed_balance: bool
    profit_lock_pct: float | None = None
    profit_lock_floor_pct: float | None = None
    payout_buffer_pct: float
    max_concurrent_trades: int
    commission_per_lot: float
    safety_buffer_pct: float
    notes: str | None = None


class RiskProfileUpdate(BaseModel):
    """Request model for updating a risk profile."""
    profile_name: str | None = None
    is_default: bool | None = None
    max_risk_per_trade_pct: float | None = None
    daily_loss_pct: float | None = None
    daily_trailing: bool | None = None
    overall_loss_pct: float | None = None
    overall_trailing: bool | None = None
    overall_trail_from_closed_balance: bool | None = None
    profit_lock_pct: float | None = None
    profit_lock_floor_pct: float | None = None
    payout_buffer_pct: float | None = None
    max_concurrent_trades: int | None = None
    commission_per_lot: float | None = None
    safety_buffer_pct: float | None = None
    notes: str | None = None


class RiskProfileResponse(BaseModel):
    """Response model for risk profile data."""
    profile_id: int
    profile_name: str
    is_default: bool
    max_risk_per_trade_pct: float
    daily_loss_pct: float
    daily_trailing: bool
    overall_loss_pct: float
    overall_trailing: bool
    overall_trail_from_closed_balance: bool
    profit_lock_pct: float | None
    profit_lock_floor_pct: float | None
    payout_buffer_pct: float
    max_concurrent_trades: int
    commission_per_lot: float
    safety_buffer_pct: float
    notes: str | None
    
    class Config:
        from_attributes = True


@router.get("/", response_model=List[RiskProfileResponse])
async def get_all_risk_profiles(
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get all risk profiles for current user.
    Regular users see default + their custom profiles.
    Super admin sees all profiles.
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        profiles = await db.get_risk_profiles_by_user(user_id, is_super_admin)
        return [RiskProfileResponse.model_validate(p) for p in profiles]
    except Exception as e:
        logger.error(f"Failed to get risk profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk profiles: {str(e)}"
        )


@router.get("/default", response_model=RiskProfileResponse)
async def get_default_risk_profile(
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get the default risk profile. Available to all users."""
    try:
        profile = await db.get_default_risk_profile()
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No default risk profile found"
            )
        return RiskProfileResponse.model_validate(profile)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get default risk profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get default risk profile: {str(e)}"
        )


@router.get("/{profile_id}", response_model=RiskProfileResponse)
async def get_risk_profile(
    profile_id: int,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """Get a specific risk profile by ID. User must have access."""
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # Verify access
        has_access = await db.verify_risk_profile_access(profile_id, user_id, is_super_admin)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this risk profile"
            )
        
        profile = await db.get_risk_profile(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk profile not found: {profile_id}"
            )
        return RiskProfileResponse.model_validate(profile)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get risk profile {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk profile: {str(e)}"
        )


@router.post("/", response_model=RiskProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_risk_profile(
    profile_data: RiskProfileCreate,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Create a new risk profile.
    Regular users can only create non-default profiles.
    Super admin can create any profile including defaults.
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # Only super admin can create default profiles
        if profile_data.is_default and not is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can create default profiles"
            )
        
        # Create RiskProfile object
        profile = RiskProfile(
            profile_id=0,  # Will be assigned by database
            profile_name=profile_data.profile_name,
            is_default=profile_data.is_default,
            max_risk_per_trade_pct=profile_data.max_risk_per_trade_pct,
            daily_loss_pct=profile_data.daily_loss_pct,
            daily_trailing=profile_data.daily_trailing,
            overall_loss_pct=profile_data.overall_loss_pct,
            overall_trailing=profile_data.overall_trailing,
            overall_trail_from_closed_balance=profile_data.overall_trail_from_closed_balance,
            profit_lock_pct=profile_data.profit_lock_pct,
            profit_lock_floor_pct=profile_data.profit_lock_floor_pct,
            payout_buffer_pct=profile_data.payout_buffer_pct,
            max_concurrent_trades=profile_data.max_concurrent_trades,
            commission_per_lot=profile_data.commission_per_lot,
            safety_buffer_pct=profile_data.safety_buffer_pct,
            notes=profile_data.notes
        )
        
        # Add to database with user_id (None for default profiles)
        profile_id = await db.add_risk_profile(profile, user_id=None if profile_data.is_default else user_id)
        if not profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create risk profile"
            )
        
        # Get created profile
        created_profile = await db.get_risk_profile(profile_id)
        logger.info(f"✓ Created risk profile: {profile_data.profile_name} (ID: {profile_id}, user: {user_id})")
        return RiskProfileResponse.model_validate(created_profile)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create risk profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create risk profile: {str(e)}"
        )


@router.put("/{profile_id}", response_model=RiskProfileResponse)
async def update_risk_profile(
    profile_id: int,
    profile_data: RiskProfileUpdate,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Update an existing risk profile.
    Regular users can only edit their own profiles.
    Super admin can edit any profile including default.
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # Get existing profile
        existing = await db.get_risk_profile(profile_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk profile not found: {profile_id}"
            )
        
        # Check if this is the default profile
        if existing.is_default and not is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can edit default profile"
            )
        
        # Verify access for non-default profiles
        if not existing.is_default:
            has_access = await db.verify_risk_profile_access(profile_id, user_id, is_super_admin)
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this risk profile"
                )
        
        # Build update dict with only provided fields
        updates = {}
        if profile_data.profile_name is not None:
            updates['profile_name'] = profile_data.profile_name
        if profile_data.is_default is not None:
            # Only super admin can change is_default flag
            if not is_super_admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only super admin can change default status"
                )
            updates['is_default'] = profile_data.is_default
        if profile_data.max_risk_per_trade_pct is not None:
            updates['max_risk_per_trade_pct'] = profile_data.max_risk_per_trade_pct
        if profile_data.daily_loss_pct is not None:
            updates['daily_loss_pct'] = profile_data.daily_loss_pct
        if profile_data.daily_trailing is not None:
            updates['daily_trailing'] = profile_data.daily_trailing
        if profile_data.overall_loss_pct is not None:
            updates['overall_loss_pct'] = profile_data.overall_loss_pct
        if profile_data.overall_trailing is not None:
            updates['overall_trailing'] = profile_data.overall_trailing
        if profile_data.overall_trail_from_closed_balance is not None:
            updates['overall_trail_from_closed_balance'] = profile_data.overall_trail_from_closed_balance
        if profile_data.profit_lock_pct is not None:
            updates['profit_lock_pct'] = profile_data.profit_lock_pct
        if profile_data.profit_lock_floor_pct is not None:
            updates['profit_lock_floor_pct'] = profile_data.profit_lock_floor_pct
        if profile_data.payout_buffer_pct is not None:
            updates['payout_buffer_pct'] = profile_data.payout_buffer_pct
        if profile_data.max_concurrent_trades is not None:
            updates['max_concurrent_trades'] = profile_data.max_concurrent_trades
        if profile_data.commission_per_lot is not None:
            updates['commission_per_lot'] = profile_data.commission_per_lot
        if profile_data.safety_buffer_pct is not None:
            updates['safety_buffer_pct'] = profile_data.safety_buffer_pct
        if profile_data.notes is not None:
            updates['notes'] = profile_data.notes
        
        # Update in database
        success = await db.update_risk_profile(profile_id, **updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update risk profile"
            )
        
        # Get updated profile
        updated = await db.get_risk_profile(profile_id)
        logger.info(f"✓ Updated risk profile ID {profile_id}")
        return RiskProfileResponse.model_validate(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update risk profile {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update risk profile: {str(e)}"
        )


@router.patch("/{profile_id}", response_model=RiskProfileResponse)
async def patch_risk_profile(
    profile_id: int,
    profile_data: RiskProfileUpdate,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Partially update a risk profile (PATCH endpoint).
    Same as PUT but more explicit about partial updates.
    """
    return await update_risk_profile(profile_id, profile_data, db, user)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_profile(
    profile_id: int,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Delete a risk profile.
    Regular users can only delete their own profiles.
    Cannot delete default profile or profiles in use by accounts.
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # Get profile
        profile = await db.get_risk_profile(profile_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk profile not found: {profile_id}"
            )
        
        # Cannot delete default profile
        if profile.is_default:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete default profile"
            )
        
        # Verify access
        has_access = await db.verify_risk_profile_access(profile_id, user_id, is_super_admin)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this risk profile"
            )
        
        success = await db.delete_risk_profile(profile_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete: profile is in use by accounts"
            )
        
        logger.info(f"✓ Deleted risk profile ID {profile_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete risk profile {profile_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete risk profile: {str(e)}"
        )
