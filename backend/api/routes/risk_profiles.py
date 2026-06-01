"""
Mirror Pupil v5.1 - Risk Profiles API Routes
CRUD operations for risk management profiles.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager, RiskProfile
from ..main import get_db


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
async def get_all_risk_profiles(db: DatabaseManager = Depends(get_db)):
    """Get all risk profiles."""
    try:
        profiles = await db.get_all_risk_profiles()
        return [RiskProfileResponse.model_validate(p) for p in profiles]
    except Exception as e:
        logger.error(f"Failed to get risk profiles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk profiles: {str(e)}"
        )


@router.get("/default", response_model=RiskProfileResponse)
async def get_default_risk_profile(db: DatabaseManager = Depends(get_db)):
    """Get the default risk profile."""
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
async def get_risk_profile(profile_id: int, db: DatabaseManager = Depends(get_db)):
    """Get a specific risk profile by ID."""
    try:
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
    db: DatabaseManager = Depends(get_db)
):
    """Create a new risk profile."""
    try:
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
        
        # Add to database
        profile_id = await db.add_risk_profile(profile)
        if not profile_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create risk profile"
            )
        
        # Get created profile
        created_profile = await db.get_risk_profile(profile_id)
        logger.info(f"✓ Created risk profile: {profile_data.profile_name} (ID: {profile_id})")
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
    db: DatabaseManager = Depends(get_db)
):
    """Update an existing risk profile."""
    try:
        # Get existing profile
        existing = await db.get_risk_profile(profile_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk profile not found: {profile_id}"
            )
        
        # Update fields (keep existing if not provided)
        updated_profile = RiskProfile(
            profile_id=profile_id,
            profile_name=profile_data.profile_name or existing.profile_name,
            is_default=profile_data.is_default if profile_data.is_default is not None else existing.is_default,
            max_risk_per_trade_pct=profile_data.max_risk_per_trade_pct or existing.max_risk_per_trade_pct,
            daily_loss_pct=profile_data.daily_loss_pct or existing.daily_loss_pct,
            daily_trailing=profile_data.daily_trailing if profile_data.daily_trailing is not None else existing.daily_trailing,
            overall_loss_pct=profile_data.overall_loss_pct or existing.overall_loss_pct,
            overall_trailing=profile_data.overall_trailing if profile_data.overall_trailing is not None else existing.overall_trailing,
            overall_trail_from_closed_balance=profile_data.overall_trail_from_closed_balance if profile_data.overall_trail_from_closed_balance is not None else existing.overall_trail_from_closed_balance,
            profit_lock_pct=profile_data.profit_lock_pct if profile_data.profit_lock_pct is not None else existing.profit_lock_pct,
            profit_lock_floor_pct=profile_data.profit_lock_floor_pct if profile_data.profit_lock_floor_pct is not None else existing.profit_lock_floor_pct,
            payout_buffer_pct=profile_data.payout_buffer_pct or existing.payout_buffer_pct,
            max_concurrent_trades=profile_data.max_concurrent_trades or existing.max_concurrent_trades,
            commission_per_lot=profile_data.commission_per_lot or existing.commission_per_lot,
            safety_buffer_pct=profile_data.safety_buffer_pct or existing.safety_buffer_pct,
            notes=profile_data.notes if profile_data.notes is not None else existing.notes
        )
        
        # Update in database
        success = await db.update_risk_profile(profile_id, updated_profile)
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


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_risk_profile(profile_id: int, db: DatabaseManager = Depends(get_db)):
    """
    Delete a risk profile.
    
    Cannot delete:
    - Default profile
    - Profiles in use by accounts
    """
    try:
        success = await db.delete_risk_profile(profile_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete: profile is default or in use by accounts"
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
