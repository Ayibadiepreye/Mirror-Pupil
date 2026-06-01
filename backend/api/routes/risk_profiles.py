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
