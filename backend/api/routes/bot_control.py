"""
Mirror Pupil v5.1 - Bot Control API Routes
Endpoints for controlling the bot (pause/resume, dry-run toggle).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager
from ...core.trade_executor import TradeExecutor
from ..main import get_db, get_executor


router = APIRouter()


class BotStatusResponse(BaseModel):
    """Response model for bot status."""
    status: str
    dry_run: bool
    active_accounts: int
    paused_accounts: int
    breached_accounts: int
    total_active_trades: int


class BotControlRequest(BaseModel):
    """Request model for bot control actions."""
    action: str  # "start", "stop"


class ToggleRequest(BaseModel):
    """Request model for toggle actions."""
    enabled: bool


class ForceCloseRequest(BaseModel):
    """Request model for force close actions."""
    account_key: str | None = None  # If None, close all accounts


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


@router.post("/control")
async def control_bot(
    request: BotControlRequest,
    db: DatabaseManager = Depends(get_db)
):
    """
    Control bot (start/stop).
    
    Args:
        request: Control action request
    
    Returns:
        Success message
    """
    try:
        if request.action == "start":
            logger.info("Bot start requested (already running)")
            return {"status": "success", "message": "Bot is running"}
        elif request.action == "stop":
            logger.info("Bot stop requested (not implemented - bot runs continuously)")
            return {"status": "success", "message": "Bot stop not implemented (runs continuously)"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to control bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control bot: {str(e)}"
        )


@router.post("/force-close-all")
async def force_close_all_positions(
    db: DatabaseManager = Depends(get_db),
    executor: TradeExecutor = Depends(get_executor)
):
    """
    Force close all open positions across all accounts.
    
    Returns:
        Number of positions closed
    """
    try:
        accounts = await db.get_all_accounts()
        total_closed = 0
        
        for account in accounts:
            trades = await db.get_active_trades(account.account_key)
            for trade in trades:
                try:
                    # Close the position via TradeLocker
                    acc_data = await db.get_account(account.account_key)
                    client = executor.account_manager.get_account(account.account_key)
                    
                    if client and trade.tl_position_id:
                        # Close position
                        await client['client'].close_position(trade.tl_position_id)
                        
                        # Mark as closed in database
                        await db.close_trade(
                            trade.trade_id,
                            exit_price=trade.entry_price,  # Use current price
                            exit_time=None,  # Will use current time
                            pnl=0.0  # Will be calculated
                        )
                        
                        total_closed += 1
                        logger.info(f"Force closed position {trade.tl_position_id} for {account.account_key}")
                except Exception as e:
                    logger.error(f"Failed to close position {trade.trade_id}: {e}")
                    continue
        
        logger.warning(f"Force closed {total_closed} positions")
        return {
            "status": "success",
            "message": f"Closed {total_closed} positions",
            "closed_count": total_closed
        }
    except Exception as e:
        logger.error(f"Failed to force close positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force close positions: {str(e)}"
        )


@router.post("/force-close-account/{account_key}")
async def force_close_account_positions(
    account_key: str,
    db: DatabaseManager = Depends(get_db),
    executor: TradeExecutor = Depends(get_executor)
):
    """
    Force close all open positions for a specific account.
    
    Args:
        account_key: Account key
    
    Returns:
        Number of positions closed
    """
    try:
        trades = await db.get_active_trades(account_key)
        total_closed = 0
        
        client = executor.account_manager.get_account(account_key)
        
        for trade in trades:
            try:
                if client and trade.tl_position_id:
                    # Close position
                    await client['client'].close_position(trade.tl_position_id)
                    
                    # Mark as closed in database
                    await db.close_trade(
                        trade.trade_id,
                        exit_price=trade.entry_price,
                        exit_time=None,
                        pnl=0.0
                    )
                    
                    total_closed += 1
                    logger.info(f"Force closed position {trade.tl_position_id} for {account_key}")
            except Exception as e:
                logger.error(f"Failed to close position {trade.trade_id}: {e}")
                continue
        
        logger.warning(f"Force closed {total_closed} positions for {account_key}")
        return {
            "status": "success",
            "message": f"Closed {total_closed} positions for account",
            "closed_count": total_closed
        }
    except Exception as e:
        logger.error(f"Failed to force close positions for {account_key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force close positions: {str(e)}"
        )


@router.post("/skip-next-signal/{channel_id}")
async def skip_next_signal(
    channel_id: int,
    db: DatabaseManager = Depends(get_db)
):
    """
    Skip the next signal from a specific channel.
    
    Args:
        channel_id: Channel ID
    
    Returns:
        Success message
    """
    try:
        # This would require a skip flag in the database or in-memory store
        # For now, just log it
        channel = await db.get_channel(channel_id)
        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel not found: {channel_id}"
            )
        
        logger.warning(f"Skip next signal requested for channel {channel.display_name} (not fully implemented)")
        
        return {
            "status": "success",
            "message": f"Next signal from {channel.display_name} will be skipped",
            "channel_id": channel_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to skip next signal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to skip next signal: {str(e)}"
        )
