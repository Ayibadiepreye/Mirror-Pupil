"""
Mirror Pupil v5.1 - Trades API Routes
Endpoints for active trades, trade history, and manual actions.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response
from pydantic import BaseModel
from datetime import datetime
from loguru import logger
import csv
import io

from ...database import DatabaseManager, ActiveTrade
from ...core.trade_executor import TradeExecutor
from ...core.account_manager import get_account_manager
from ...core.firebase_auth import get_current_user
from ..main import get_db


router = APIRouter()


class ActiveTradeResponse(BaseModel):
    """Response model for active trade data."""
    trade_id: int
    account_key: str
    channel_id: int
    channel_name: str | None
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
    current_pnl: float | None = None
    
    class Config:
        from_attributes = True


class ManualActionRequest(BaseModel):
    """Request model for manual trade actions."""
    action_type: str  # MANUAL_CLOSE, MANUAL_BE, MANUAL_PARTIAL_25, MANUAL_PARTIAL_50, MANUAL_PARTIAL_75
    reason: Optional[str] = None


@router.post("/active/{trade_id}/close")
async def close_trade_manually(
    trade_id: int,
    action: ManualActionRequest,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Manually close an active trade.
    User must own the account or be super admin.
    
    Args:
        trade_id: Trade ID
        action: Action details
    
    Returns:
        Success status
    """
    try:
        # Get trade details
        trade = await db.get_active_trade_by_id(trade_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade not found: {trade_id}"
            )
        
        # Verify ownership
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        has_access = await db.verify_account_ownership(trade.account_key, user_id, is_super_admin)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this account"
            )
        
        # Execute close action through TradeExecutor
        executor = TradeExecutor(db)
        success = await executor.execute_manual_close(
            trade_id=trade_id,
            account_key=trade.account_key,
            reason=action.reason or "Manual close from GUI"
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to close trade"
            )
        
        # Log manual action
        await db.add_manual_action(
            account_key=trade.account_key,
            trade_id=trade_id,
            action_type="MANUAL_CLOSE",
            action_data={"reason": action.reason}
        )
        
        logger.info(f"✓ Manually closed trade {trade_id}")
        return {"success": True, "message": "Trade closed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close trade {trade_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close trade: {str(e)}"
        )


@router.post("/active/{trade_id}/breakeven")
async def set_trade_to_breakeven(
    trade_id: int,
    action: ManualActionRequest,
    db: DatabaseManager = Depends(get_db)
):
    """
    Set trade SL to breakeven (entry price).
    
    Args:
        trade_id: Trade ID
        action: Action details
    
    Returns:
        Success status
    """
    try:
        trade = await db.get_active_trade_by_id(trade_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade not found: {trade_id}"
            )
        
        executor = TradeExecutor(db)
        success = await executor.execute_manual_breakeven(
            trade_id=trade_id,
            account_key=trade.account_key
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to set breakeven"
            )
        
        await db.add_manual_action(
            account_key=trade.account_key,
            trade_id=trade_id,
            action_type="MANUAL_BE",
            action_data={"reason": action.reason}
        )
        
        logger.info(f"✓ Set trade {trade_id} to breakeven")
        return {"success": True, "message": "Trade set to breakeven"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set breakeven for trade {trade_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set breakeven: {str(e)}"
        )


@router.post("/active/{trade_id}/partial")
async def take_partial_profit(
    trade_id: int,
    action: ManualActionRequest,
    db: DatabaseManager = Depends(get_db)
):
    """
    Take partial profit on a trade.
    
    Args:
        trade_id: Trade ID
        action: Action details (action_type must be MANUAL_PARTIAL_25, _50, or _75)
    
    Returns:
        Success status
    """
    try:
        # Validate action type
        valid_actions = ["MANUAL_PARTIAL_25", "MANUAL_PARTIAL_50", "MANUAL_PARTIAL_75"]
        if action.action_type not in valid_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action type. Must be one of: {valid_actions}"
            )
        
        trade = await db.get_active_trade_by_id(trade_id)
        if not trade:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade not found: {trade_id}"
            )
        
        # Extract percentage from action type (25, 50, or 75)
        percentage = int(action.action_type.split("_")[-1])
        
        executor = TradeExecutor(db)
        success = await executor.execute_manual_partial(
            trade_id=trade_id,
            account_key=trade.account_key,
            percentage=percentage
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to take partial profit"
            )
        
        await db.add_manual_action(
            account_key=trade.account_key,
            trade_id=trade_id,
            action_type=action.action_type,
            action_data={"percentage": percentage, "reason": action.reason}
        )
        
        logger.info(f"✓ Took {percentage}% partial profit on trade {trade_id}")
        return {"success": True, "message": f"Took {percentage}% partial profit"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to take partial profit on trade {trade_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to take partial profit: {str(e)}"
        )


@router.get("/active", response_model=List[ActiveTradeResponse])
async def get_all_active_trades(
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get all active trades for current user with live P&L.
    Super admin sees all accounts, regular users see only their own.
    
    Returns:
        List of active trades
    """
    try:
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        # Get accounts based on user role
        accounts = await db.get_accounts_by_user(user_id, is_super_admin)
        
        # Get active trades for each account
        all_trades = []
        for account in accounts:
            trades = await db.get_active_trades(account.account_key)
            all_trades.extend(trades)
        
        # Return trades with current_pnl from database (updated by background service)
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
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get active trades for a specific account with live P&L.
    User must own the account or be super admin.
    
    Args:
        account_key: Account key
    
    Returns:
        List of active trades for the account
    """
    try:
        # Verify ownership
        user_id = user['user_id']
        is_super_admin = user.get('is_super_admin', False)
        
        has_access = await db.verify_account_ownership(account_key, user_id, is_super_admin)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this account"
            )
        
        trades = await db.get_active_trades(account_key)
        
        # Return trades with current_pnl from database (updated by background service)
        return [ActiveTradeResponse.model_validate(t) for t in trades]
    except HTTPException:
        raise
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
    channel_name: str | None
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
    manual_action_type: str | None
    
    class Config:
        from_attributes = True


@router.get("/history/export")
async def export_trade_history(
    account_key: str | None = None,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Export trade history as CSV file.
    Regular users export only their trades, super admin can export all.
    
    Args:
        account_key: Optional account filter
    
    Returns:
        CSV file download
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
        
        history = await db.get_trade_history(
            account_key=account_key,
            user_id=user_id,
            is_super_admin=is_super_admin,
            limit=10000
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "history_id", "account_key", "channel_id", "channel_name", "signal_id",
            "symbol", "direction", "entry_price", "exit_price", "sl", "tp",
            "lot_size", "entry_time", "exit_time", "pnl", "outcome", "close_reason",
            "manual_action_type"
        ])
        
        writer.writeheader()
        for trade in history:
            writer.writerow({
                "history_id": trade.get("history_id"),
                "account_key": trade.get("account_key"),
                "channel_id": trade.get("channel_id"),
                "channel_name": trade.get("channel_name", ""),
                "signal_id": trade.get("signal_id"),
                "symbol": trade.get("symbol"),
                "direction": trade.get("direction"),
                "entry_price": trade.get("entry_price"),
                "exit_price": trade.get("exit_price"),
                "sl": trade.get("sl", ""),
                "tp": trade.get("tp", ""),
                "lot_size": trade.get("lot_size"),
                "entry_time": trade.get("entry_time"),
                "exit_time": trade.get("exit_time"),
                "pnl": trade.get("pnl"),
                "outcome": trade.get("outcome"),
                "close_reason": trade.get("close_reason"),
                "manual_action_type": trade.get("manual_action_type", "")
            })
        
        # Return CSV response
        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=trade_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export trade history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export trade history: {str(e)}"
        )


@router.get("/history", response_model=List[TradeHistoryResponse])
async def get_trade_history(
    account_key: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get trade history with optional filtering.
    Regular users see only their trades, super admin sees all.
    
    Args:
        account_key: Optional account key filter
        limit: Maximum number of records (default 100)
        offset: Offset for pagination (default 0)
    
    Returns:
        List of closed trades from history
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
        
        history = await db.get_trade_history(
            account_key=account_key,
            user_id=user_id,
            is_super_admin=is_super_admin,
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
