"""
Mirror Pupil v5.1 - Bot Control API Routes
Endpoints for controlling the bot (pause/resume, dry-run toggle).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from ...database import DatabaseManager
from ...core.trade_executor import TradeExecutor
from ...core.firebase_auth import require_super_admin, get_current_user
from ...core.bot_state import get_bot_state
from ...risk.calculator import calculate_usd_pnl
from ..dependencies import get_db, get_executor


router = APIRouter()


class BotStatusResponse(BaseModel):
    """Response model for bot status."""
    status: str
    dry_run: bool
    active_accounts: int
    paused_accounts: int
    breached_accounts: int
    total_active_trades: int
    allow_weekend_trading: bool = False
    allow_eod_trading: bool = False


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
async def get_bot_status(
    db: DatabaseManager = Depends(get_db),
    user: dict = Depends(get_current_user)
):
    """
    Get current bot status.
    **All authenticated users can view.**
    
    Returns:
        Bot status information
    """
    try:
        # Get bot state
        bot_state = get_bot_state()
        
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
        
        # Get bot settings
        settings = await db.get_all_bot_settings()
        weekend_trading = settings.get('allow_weekend_trading', 'false') == 'true'
        eod_trading = settings.get('allow_eod_trading', 'false') == 'true'
        
        return BotStatusResponse(
            status=bot_state.get_status(),
            dry_run=False,  # TODO: Get from config
            active_accounts=active_accounts,
            paused_accounts=paused_accounts,
            breached_accounts=breached_accounts,
            total_active_trades=total_trades,
            allow_weekend_trading=weekend_trading,
            allow_eod_trading=eod_trading
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
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Control bot (start/stop).
    **Super admin only.**
    
    Args:
        request: Control action request
    
    Returns:
        Success message
    """
    try:
        bot_state = get_bot_state()
        
        if request.action == "start":
            changed = await bot_state.start()
            return {
                "status": "success",
                "message": "Bot started" if changed else "Bot already running",
                "bot_status": bot_state.get_status()
            }
        elif request.action == "stop":
            changed = await bot_state.stop()
            return {
                "status": "success",
                "message": "Bot stopped (existing trades will continue)" if changed else "Bot already stopped",
                "bot_status": bot_state.get_status()
            }
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
    executor: TradeExecutor = Depends(get_executor),
    admin: dict = Depends(require_super_admin)
):
    """
    Force close all open positions across all accounts.
    **Super admin only.**
    
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
                    # Get account and client
                    acc_data = await db.get_account(account.account_key)
                    client = executor.account_manager.get_account(account.account_key)
                    
                    if client and trade.tl_position_id:
                        # Get current market price BEFORE closing
                        current_price = None
                        try:
                            positions = await client['client'].get_all_positions()
                            for pos in positions:
                                if str(pos.get('id')) == str(trade.tl_position_id):
                                    current_price = float(pos.get('currentPrice', 0.0))
                                    break
                        except Exception as e:
                            logger.warning(f"Failed to fetch price before close: {e}")
                        
                        # Close position (ONCE)
                        close_response = await client['client'].close_position(int(trade.tl_position_id))
                        
                        # Determine exit price source
                        exit_price = None
                        price_source = None
                        
                        # Priority 1: Broker close response
                        if isinstance(close_response, dict) and 'price' in close_response:
                            exit_price = float(close_response.get('price', 0.0))
                            price_source = "broker_close_response"
                        
                        # Priority 2: Live price captured before close
                        if not exit_price and current_price and current_price > 0:
                            exit_price = current_price
                            price_source = "live_before_close"
                        
                        # Priority 3: Approximate (flag for reconciliation)
                        if not exit_price:
                            exit_price = trade.entry_price
                            price_source = "approximation_needs_reconciliation"
                            logger.warning(
                                f"[{account.account_key}] Force-close {trade.symbol}: "
                                f"No reliable exit price, using entry price approximation"
                            )
                        
                        logger.info(f"[{account.account_key}] Exit price source: {price_source}, price: {exit_price}")
                        
                        # PRIMARY: Use last saved current_pnl from database (updated every 15 seconds)
                        pnl = trade.current_pnl
                        
                        if pnl is not None:
                            logger.info(f"[{account.account_key}] Using saved current_pnl: ${pnl:.2f}")
                        else:
                            # FALLBACK: Try to get unrealizedPl from the position in real-time
                            logger.warning(f"[{account.account_key}] No saved PnL, fetching from TradeLocker...")
                            try:
                                positions = await client['client'].get_all_positions()
                                position = next((p for p in positions if str(p.get('id')) == str(trade.tl_position_id)), None)
                                if position:
                                    pnl = float(position.get('unrealizedPl', 0) or position.get('profit', 0) or position.get('pnl', 0))
                                    logger.info(f"[{account.account_key}] Fetched unrealizedPl from position: ${pnl:.2f}")
                            except Exception as e:
                                logger.warning(f"[{account.account_key}] Could not fetch unrealizedPl: {e}")
                            
                            # LAST RESORT: Use 0.0 if still unavailable
                            if pnl is None:
                                logger.error(f"[{account.account_key}] Could not determine PnL, using 0.0")
                                pnl = 0.0
                        
                        outcome = 'WIN' if pnl > 0 else ('LOSS' if pnl < 0 else 'BE')
                        
                        # Mark as closed in database
                        await db.close_active_trade(
                            trade.trade_id,
                            exit_price=current_price,
                            pnl=pnl,
                            outcome=outcome,
                            close_reason='FORCE_CLOSE'
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
    executor: TradeExecutor = Depends(get_executor),
    admin: dict = Depends(require_super_admin)
):
    """
    Force close all open positions for a specific account.
    **Super admin only.**
    
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
                    # Get current market price BEFORE closing
                    current_price = None
                    try:
                        positions = await client['client'].get_all_positions()
                        for pos in positions:
                            if str(pos.get('id')) == str(trade.tl_position_id):
                                current_price = float(pos.get('currentPrice', 0.0))
                                break
                    except Exception as e:
                        logger.warning(f"Failed to fetch price before close: {e}")
                    
                    # Close position (ONCE)
                    close_response = await client['client'].close_position(int(trade.tl_position_id))
                    
                    # Determine exit price source
                    exit_price = None
                    price_source = None
                    
                    # Priority 1: Broker close response
                    if isinstance(close_response, dict) and 'price' in close_response:
                        exit_price = float(close_response.get('price', 0.0))
                        price_source = "broker_close_response"
                    
                    # Priority 2: Live price captured before close
                    if not exit_price and current_price and current_price > 0:
                        exit_price = current_price
                        price_source = "live_before_close"
                    
                    # Priority 3: Approximate (flag for reconciliation)
                    if not exit_price:
                        exit_price = trade.entry_price
                        price_source = "approximation_needs_reconciliation"
                        logger.warning(
                            f"[{account_key}] Force-close {trade.symbol}: "
                            f"No reliable exit price, using entry price approximation"
                        )
                    
                    logger.info(f"[{account_key}] Exit price source: {price_source}, price: {exit_price}")
                    
                    # PRIMARY: Use last saved current_pnl from database (updated every 15 seconds)
                    pnl = trade.current_pnl
                    
                    if pnl is not None:
                        logger.info(f"[{account_key}] Using saved current_pnl: ${pnl:.2f}")
                    else:
                        # FALLBACK: Try to get unrealizedPl from the position in real-time
                        logger.warning(f"[{account_key}] No saved PnL, fetching from TradeLocker...")
                        try:
                            positions = await client['client'].get_all_positions()
                            position = next((p for p in positions if str(p.get('id')) == str(trade.tl_position_id)), None)
                            if position:
                                pnl = float(position.get('unrealizedPl', 0) or position.get('profit', 0) or position.get('pnl', 0))
                                logger.info(f"[{account_key}] Fetched unrealizedPl from position: ${pnl:.2f}")
                        except Exception as e:
                            logger.warning(f"[{account_key}] Could not fetch unrealizedPl: {e}")
                        
                        # LAST RESORT: Use 0.0 if still unavailable
                        if pnl is None:
                            logger.error(f"[{account_key}] Could not determine PnL, using 0.0")
                            pnl = 0.0
                    
                    outcome = 'WIN' if pnl > 0 else ('LOSS' if pnl < 0 else 'BE')
                    
                    # Mark as closed in database
                    await db.close_active_trade(
                        trade.trade_id,
                        exit_price=current_price,
                        pnl=pnl,
                        outcome=outcome,
                        close_reason='FORCE_CLOSE'
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
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Skip the next signal from a specific channel.
    **Super admin only.**
    
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



@router.post("/settings/weekend-trading")
async def toggle_weekend_trading(
    request: ToggleRequest,
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Toggle weekend trading setting.
    **Super admin only.**
    
    When enabled:
    - Allows new signals on Saturday/Sunday
    - Bypasses weekend blocking in TradeExecutor
    
    Args:
        request: Toggle request with enabled boolean
    
    Returns:
        Success message with new setting value
    """
    try:
        value = 'true' if request.enabled else 'false'
        success = await db.set_bot_setting('allow_weekend_trading', value)
        
        if success:
            logger.warning(f"Weekend trading {'ENABLED' if request.enabled else 'DISABLED'}")
            return {
                "status": "success",
                "message": f"Weekend trading {'enabled' if request.enabled else 'disabled'}",
                "allow_weekend_trading": request.enabled
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update setting"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle weekend trading: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle weekend trading: {str(e)}"
        )


@router.post("/settings/eod-trading")
async def toggle_eod_trading(
    request: ToggleRequest,
    db: DatabaseManager = Depends(get_db),
    admin: dict = Depends(require_super_admin)
):
    """
    Toggle EOD trading setting.
    **Super admin only.**
    
    When enabled:
    - Skips 4:45 PM EST force close
    - Allows new signals during reset lock (5:00 PM - 5:59 PM EST)
    - Allows trading after 4:45 PM and before 6:00 PM EST
    
    Args:
        request: Toggle request with enabled boolean
    
    Returns:
        Success message with new setting value
    """
    try:
        value = 'true' if request.enabled else 'false'
        success = await db.set_bot_setting('allow_eod_trading', value)
        
        if success:
            logger.warning(f"EOD trading {'ENABLED' if request.enabled else 'DISABLED'}")
            return {
                "status": "success",
                "message": f"EOD trading {'enabled' if request.enabled else 'disabled'}",
                "allow_eod_trading": request.enabled
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update setting"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle EOD trading: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle EOD trading: {str(e)}"
        )
