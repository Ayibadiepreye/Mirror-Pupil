"""
Mirror Pupil v5.1 - Bot Control API Routes
Endpoints for controlling the bot (pause/resume, dry-run toggle).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager
from ..main import get_db


router = APIRouter()


class BotStatusResponse(BaseModel):
    """Response model for bot status."""
    status: str
    dry_run: bool
    active_accounts: int
    paused_accounts: int
    breached_accounts: int
    total_active_trades: int


@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status(db: DatabaseManager = Depends(get_db)):
    """
    Get current bot status.
    
    Returns:
        Bot status information
    """
    try:
        # Get all accounts
        accounts = await db.get_all_accounts()
        
        # Count account statuses
        active_accounts = sum(1 for a in accounts if not a.paused and not a.breached)
        paused_accounts = sum(1 for a in accounts if a.paused)
        breached_accounts = sum(1 for a in accounts if a.breached)
        
        # Count total active trades
        total_trades = 0
        for account in accounts:
            trades = await db.get_active_trades(account.account_key)
            total_trades += len(trades)
        
        return BotStatusResponse(
            status="running",
            dry_run=False,  # TODO: Get from config
            active_accounts=active_accounts,
            paused_accounts=paused_accounts,
            breached_accounts=breached_accounts,
            total_active_trades=total_trades
        )
    except Exception as e:
        logger.error(f"Failed to get bot status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get bot status: {str(e)}"
        )
