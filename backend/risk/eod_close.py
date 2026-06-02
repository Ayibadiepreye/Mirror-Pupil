"""
Mirror Pupil v5.1 - EOD Close Handler
Handles 4:45pm EST force close of all trades.
"""

import asyncio
from datetime import datetime, time
from typing import Optional
import pytz
from loguru import logger

from ..database import DatabaseManager


class EODCloseHandler:
    """
    Handles end-of-day force close at 4:45pm EST.
    
    All trades are force-closed 15 minutes before the 5pm daily reset
    to ensure accounts are flat at the benchmark snapshot.
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.close_task: Optional[asyncio.Task] = None
        self.timezone = pytz.timezone("America/New_York")  # EST/EDT
        
        logger.info("Initialized EODCloseHandler")
    
    async def start_eod_close_scheduler(self):
        """Start background task that runs EOD close at 4:45pm EST."""
        if self.close_task:
            logger.warning("EOD close scheduler already running")
            return
        
        self.close_task = asyncio.create_task(self._eod_close_loop())
        logger.info("✓ Started EOD close scheduler (4:45pm EST)")
    
    async def stop_eod_close_scheduler(self):
        """Stop EOD close scheduler."""
        if self.close_task:
            self.close_task.cancel()
            try:
                await self.close_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped EOD close scheduler")
    
    async def _eod_close_loop(self):
        """Background task that waits for 4:45pm EST and closes all trades."""
        while True:
            try:
                # Calculate time until next 4:45pm EST
                now = datetime.now(self.timezone)
                target_time = time(16, 45, 0)  # 4:45 PM
                
                # Create target datetime for today at 4:45pm
                target = self.timezone.localize(
                    datetime.combine(now.date(), target_time)
                )
                
                # If we've passed 4:45pm today, target tomorrow
                if now >= target:
                    from datetime import timedelta
                    target = target + timedelta(days=1)
                
                # Calculate seconds until target
                wait_seconds = (target - now).total_seconds()
                
                logger.info(
                    f"Next EOD close scheduled for {target.strftime('%Y-%m-%d %H:%M:%S %Z')} "
                    f"({wait_seconds/3600:.1f} hours)"
                )
                
                # Wait until 4:45pm
                await asyncio.sleep(wait_seconds)
                
                # Run EOD close for all accounts
                await self.run_eod_close()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"EOD close loop error: {e}")
                # Wait 1 minute before retrying
                await asyncio.sleep(60)
    
    async def run_eod_close(self):
        """
        Force close all open trades across all accounts.
        
        Called at exactly 4:45 PM EST (15 minutes before daily reset).
        Can be bypassed if 'allow_eod_trading' setting is enabled.
        """
        # Check if EOD trading is allowed (bypasses close)
        eod_allowed = await self.db.get_bot_setting('allow_eod_trading')
        if eod_allowed == 'true':
            logger.info("EOD close skipped - EOD trading is enabled")
            return
        
        logger.info("="*60)
        logger.info("EOD FORCE CLOSE - 4:45 PM EST")
        logger.info("="*60)
        
        accounts = await self.db.get_all_accounts()
        
        total_closed = 0
        
        for account in accounts:
            try:
                closed_count = await self.close_account_trades(account.account_key)
                total_closed += closed_count
            except Exception as e:
                logger.error(f"Failed to close trades for {account.account_key}: {e}")
        
        logger.info(f"✓ EOD close complete: {total_closed} trade(s) closed across {len(accounts)} account(s)")
    
    async def close_account_trades(self, account_key: str) -> int:
        """
        Close all open trades AND cancel all pending orders for a specific account.
        
        Returns:
            Number of trades/orders closed
        """
        # Get all active trades (includes pending orders with status='pending')
        active_trades = await self.db.get_active_trades(account_key)
        
        if not active_trades:
            logger.debug(f"[{account_key}] No active trades to close")
            return 0
        
        logger.info(f"[{account_key}] Closing {len(active_trades)} active trade(s)/order(s)...")
        
        closed_count = 0
        
        for trade in active_trades:
            try:
                # Get TradeLocker client
                from ..core.account_manager import get_account_manager
                account_manager = get_account_manager()
                tl_client = account_manager.get_client_for_account(account_key)
                
                if not tl_client:
                    logger.error(f"No TradeLocker client for {account_key}")
                    continue
                
                # Handle pending orders differently from filled positions
                if trade.status == 'pending':
                    # Cancel the pending order
                    try:
                        await tl_client.cancel_order(trade.tl_order_id)
                        logger.info(
                            f"[{account_key}] Cancelled pending order {trade.trade_id}: "
                            f"{trade.symbol} {trade.direction} @ {trade.entry_price}"
                        )
                        
                        # Move to history with zero P&L
                        success = await self.db.close_active_trade(
                            trade_id=trade.trade_id,
                            exit_price=trade.entry_price,
                            pnl=0.0,
                            outcome="BE",
                            close_reason="EOD_CANCELLED"
                        )
                        
                        if success:
                            closed_count += 1
                        
                        continue
                    except Exception as e:
                        logger.error(f"Failed to cancel pending order {trade.trade_id}: {e}")
                        continue
                
                # Close filled position on TradeLocker
                await tl_client.close_position(trade.tl_position_id)
                
                # Get actual exit price from closed position
                try:
                    # Get all positions and find this one
                    all_positions = await tl_client.get_all_positions()
                    position_info = next(
                        (p for p in all_positions if p.get('id') == trade.tl_position_id),
                        None
                    )
                    
                    if position_info:
                        exit_price = float(position_info.get('closePrice', trade.entry_price))
                    else:
                        # Position already closed, use market price
                        raise ValueError("Position already closed")
                except Exception:
                    # Fallback: get current market price
                    try:
                        # Use existing get_market_price method
                        market_price = await tl_client.get_market_price(trade.symbol)
                        if market_price:
                            exit_price = market_price
                        else:
                            exit_price = trade.entry_price
                    except Exception:
                        exit_price = trade.entry_price  # Last resort fallback
                
                # Calculate actual P&L (simplified calculation)
                if trade.direction == 'BUY':
                    pnl = (exit_price - trade.entry_price) * trade.lot_size * 100000
                else:
                    pnl = (trade.entry_price - exit_price) * trade.lot_size * 100000
                
                # Determine outcome
                if pnl > 0:
                    outcome = "WIN"
                elif pnl < 0:
                    outcome = "LOSS"
                else:
                    outcome = "BE"
                
                # Close trade in database
                success = await self.db.close_active_trade(
                    trade_id=trade.trade_id,
                    exit_price=exit_price,
                    pnl=pnl,
                    outcome=outcome,
                    close_reason="EOD"
                )
                
                if success:
                    closed_count += 1
                    logger.info(
                        f"[{account_key}] Closed trade {trade.trade_id}: "
                        f"{trade.symbol} {trade.direction} @ {exit_price:.5f} (P&L: ${pnl:.2f})"
                    )
                
            except Exception as e:
                logger.error(f"Failed to close trade {trade.trade_id}: {e}")
        
        logger.info(f"[{account_key}] ✓ Closed {closed_count}/{len(active_trades)} trade(s)")
        
        return closed_count
    
    async def is_weekend_close_time(self) -> bool:
        """
        Check if it's Friday 4:45pm EST (weekend close time).
        
        Returns:
            True if it's Friday at 4:45pm EST
        """
        now = datetime.now(self.timezone)
        return now.weekday() == 4 and now.hour == 16 and now.minute == 45  # Friday


# Global handler instance
_handler: Optional[EODCloseHandler] = None


async def get_eod_close_handler(db: DatabaseManager) -> EODCloseHandler:
    """Get the global EOD close handler instance."""
    global _handler
    if _handler is None:
        _handler = EODCloseHandler(db)
        await _handler.start_eod_close_scheduler()
    return _handler
