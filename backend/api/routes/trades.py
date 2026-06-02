"""
Mirror Pupil v5.1 - Trades API Routes
Read-only endpoints for active trades and trade history.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
from loguru import logger

from ...database import DatabaseManager, ActiveTrade
from ..main import get_db


router = APIRouter()


class ActiveTradeResponse(BaseModel):
    """Response model for active trade data."""
    trade_id: int
    account_key: str
    channel_id: int
    signal_id: str
    sub_signal_id: str | None
    symbol: str
    direction: str
    entry_price: float
    sl: float | None
    tp: float | None
    lot_size: float
    entry_time: datetime
    tl_order_id: str | None
    tl_position_id: str | None
    status: str
    tp1_hit: bool
    risk_usd: float | None
    
    class Config:
        from_attributes = True


@router.get("/active", response_model=List[ActiveTradeResponse])
async def get_all_active_trades(db: DatabaseManager = Depends(get_db)):
    """
    Get all active trades across all accounts.
    
    Returns:
        List of all active trades
    """
    try:
        # Get all accounts
        accounts = await db.get_all_accounts()
        
        # Get active trades for each account
        all_trades = []
        for account in accounts:
            trades = await db.get_active_trades(account.account_key)
            all_trades.extend(trades)
        
        return [ActiveTradeResponse.model_validate(t) for t in all_trades]
    except Exception as e:
        logger.error(f"Failed to get active trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active trades: {str(e)}"
        )


@router.get("/active/{account_key}", response_model=List[ActiveTradeResponse])
async def get_active_trades_for_account(
    account_key: str,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get active trades for a specific account.
    
    Args:
        account_key: Account key
    
    Returns:
        List of active trades for the account
    """
    try:
        trades = await db.get_active_trades(account_key)
        return [ActiveTradeResponse.model_validate(t) for t in trades]
    except Exception as e:
        logger.error(f"Failed to get active trades for {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active trades: {str(e)}"
        )


class TradeHistoryResponse(BaseModel):
    """Response model for trade history data."""
    history_id: int
    account_key: str
    channel_id: int
    signal_id: str
    sub_signal_id: str | None
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    sl: float | None
    tp: float | None
    lot_size: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    outcome: str
    close_reason: str
    
    class Config:
        from_attributes = True


@router.get("/history", response_model=List[TradeHistoryResponse])
async def get_trade_history(
    account_key: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: DatabaseManager = Depends(get_db)
):
    """
    Get trade history with optional filtering.
    
    Args:
        account_key: Optional account key filter
        limit: Maximum number of records (default 100)
        offset: Offset for pagination (default 0)
    
    Returns:
        List of closed trades from history
    """
    try:
        history = await db.get_trade_history(
            account_key=account_key,
            limit=limit,
            offset=offset
        )
        return [TradeHistoryResponse(**h) for h in history]
    except Exception as e:
        logger.error(f"Failed to get trade history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trade history: {str(e)}"
        )
