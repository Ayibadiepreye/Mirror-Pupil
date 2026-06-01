"""
Firepips - Autonomous Management Actions
Implements Section 6.7 of the spec: Time-based autonomous trade management.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

from ...database import DatabaseManager, ActiveTrade
from ...core.account_manager import get_account_manager
from ...core.trade_executor import TradeExecutor


class FirepipsAutonomousManager:
    """
    Autonomous management for Firepips trades.
    
    Per spec Section 6.7:
    - 1 hour: Move SL to BE if trade in profit (floating P&L > 0)
    - 2 hours: Close 50% if trade in profit
    - 4 hours: Force close remaining (any state)
    - 4:45 PM EST: Force close all (EOD) ✅ Already implemented in eod_close.py
    - Friday 4:45 PM EST: Force close all (weekend) ✅ Already implemented
    
    Runs every 60 seconds to check all active Firepips trades.
    """
    
    def __init__(self, db: DatabaseManager, executor: TradeExecutor, channel_id: int):
        self.db = db
        self.executor = executor
        self.channel_id = channel_id  # -1001182913499 for Firepips
        self.account_manager = get_account_manager()
        self.manager_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.check_interval = 60  # Check every 60 seconds
        
        logger.info(f"Initialized FirepipsAutonomousManager (channel_id={channel_id})")
    
    async def start_managing(self):
        """Start background autonomous management task."""
        if self.manager_task:
            logger.warning("Firepips autonomous manager already running")
            return
        
        self.manager_task = asyncio.create_task(self._management_loop())
        logger.info(f"✓ Started Firepips autonomous management (every {self.check_interval}s)")
    
    async def stop_managing(self):
        """Stop background management task."""
        if self.manager_task:
            self.manager_task.cancel()
            try:
                await self.manager_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped Firepips autonomous management")
    
    async def _management_loop(self):
        """Main management loop - runs every 60 seconds."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_all_trades()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Firepips autonomous management error: {e}")
    
    async def _check_all_trades(self):
        """Check all active Firepips trades for autonomous actions."""
        # Get all active trades for this channel
        trades = await self.db.get_active_trades_by_channel(self.channel_id)
        
        if not trades:
            return
        
        now = datetime.utcnow()
        
        for trade in trades:
            try:
                await self._check_trade(trade, now)
            except Exception as e:
                logger.error(
                    f"Failed to check trade {trade.signal_id}: {e}"
                )
    
    async def _check_trade(self, trade: ActiveTrade, now: datetime):
        """
        Check a single trade for autonomous actions.
        
        Actions are checked in priority order:
        1. 4 hours → Close 100% (any state)
        2. 2 hours → Close 50% (if in profit)
        3. 1 hour → Move SL to BE (if in profit)
        """
        # Calculate time since entry
        time_since_entry = now - trade.entry_time
        
        # 4 HOURS: Close remaining 100% (any state)
        if time_since_entry >= timedelta(hours=4):
            await self._action_close_all(trade, "4-hour autonomous close")
            return
        
        # 2 HOURS: Close 50% if in profit
        if time_since_entry >= timedelta(hours=2):
            if await self._is_trade_in_profit(trade):
                await self._action_partial_close(trade, 0.50, "2-hour autonomous partial close")
            return
        
        # 1 HOUR: Move SL to BE if in profit
        if time_since_entry >= timedelta(hours=1):
            if await self._is_trade_in_profit(trade):
                await self._action_breakeven(trade, "1-hour autonomous BE")
            return
    
    async def _action_breakeven(self, trade: ActiveTrade, reason: str):
        """Move SL to entry price (breakeven)."""
        try:
            # Get TradeLocker client
            tl_client = self.account_manager.get_client_for_account(trade.account_key)
            if not tl_client:
                return
            
            # Modify SL to entry price
            await tl_client.modify_position(
                position_id=trade.tl_position_id,
                stop_loss=trade.entry_price
            )
            
            # Update database
            await self.db.update_trade(trade.trade_id, sl=trade.entry_price)
            
            logger.info(
                f"[AUTO-BE] {trade.signal_id} ({trade.symbol}): "
                f"SL moved to BE ({trade.entry_price:.5f}) - {reason}"
            )
            
        except Exception as e:
            logger.error(f"Failed to move {trade.signal_id} to BE: {e}")
    
    async def _action_partial_close(self, trade: ActiveTrade, pct: float, reason: str):
        """Close partial position (e.g., 50%)."""
        qty = round(trade.lot_size * pct, 2)
        
        if qty <= 0:
            return  # Nothing to close
        
        try:
            # Get TradeLocker client
            tl_client = self.account_manager.get_client_for_account(trade.account_key)
            if not tl_client:
                return
            
            # Close partial position
            await tl_client.close_position(
                position_id=trade.tl_position_id,
                quantity=qty
            )
            
            # Update database
            new_lot_size = round(trade.lot_size - qty, 2)
            await self.db.update_trade(trade.trade_id, lot_size=new_lot_size)
            
            logger.info(
                f"[AUTO-PARTIAL] {trade.signal_id} ({trade.symbol}): "
                f"Closed {pct*100:.0f}% ({qty} lots) - {reason}"
            )
            
        except Exception as e:
            logger.error(f"Failed to partial close {trade.signal_id}: {e}")
    
    async def _action_close_all(self, trade: ActiveTrade, reason: str):
        """Close full position."""
        try:
            # Get TradeLocker client
            tl_client = self.account_manager.get_client_for_account(trade.account_key)
            if not tl_client:
                return
            
            # Close full position
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
            except:
                # Fallback: get current market price
                try:
                    # Use existing get_market_price method
                    market_price = await tl_client.get_market_price(trade.symbol)
                    if market_price:
                        exit_price = market_price
                    else:
                        exit_price = trade.entry_price
                except:
                    exit_price = trade.entry_price  # Last resort fallback
            
            # Calculate actual P&L (simplified calculation)
            if trade.direction == 'BUY':
                pnl = (exit_price - trade.entry_price) * trade.lot_size * 100000
            else:
                pnl = (trade.entry_price - exit_price) * trade.lot_size * 100000
            
            # Determine outcome
            if pnl > 0:
                outcome = 'WIN'
            elif pnl < 0:
                outcome = 'LOSS'
            else:
                outcome = 'BE'
            
            # Move to history
            await self.db.close_active_trade(
                trade_id=trade.trade_id,
                exit_price=exit_price,
                pnl=pnl,
                outcome=outcome,
                close_reason=reason
            )
            
            logger.info(
                f"[AUTO-CLOSE] {trade.signal_id} ({trade.symbol}): "
                f"Closed 100% @ {exit_price:.5f} (P&L: ${pnl:.2f}) - {reason}"
            )
            
        except Exception as e:
            logger.error(f"Failed to close {trade.signal_id}: {e}")
    
    async def _is_trade_in_profit(self, trade: ActiveTrade) -> bool:
        """
        Check if trade has positive floating P&L.
        Per spec Section 6.7: "Trade in profit (floating P&L > 0)"
        """
        try:
            # Get current market price
            tl_client = self.account_manager.get_client_for_account(trade.account_key)
            if not tl_client:
                return False
            
            # Use existing get_market_price method
            market_price = await tl_client.get_market_price(trade.symbol)
            
            if not market_price or market_price <= 0:
                return False
            
            # Calculate profit in pips
            if trade.direction == 'BUY':
                profit_pips = (market_price - trade.entry_price) * 10000
            else:  # SELL
                profit_pips = (trade.entry_price - market_price) * 10000
            
            return profit_pips > 0
            
        except Exception as e:
            logger.error(f"Failed to check profit for {trade.signal_id}: {e}")
            return False


# Singleton instance
_manager: Optional[FirepipsAutonomousManager] = None


def get_firepips_autonomous_manager(
    db: Optional[DatabaseManager] = None,
    executor: Optional[TradeExecutor] = None,
    channel_id: int = -1001182913499
) -> FirepipsAutonomousManager:
    """Get or create singleton Firepips autonomous manager."""
    global _manager
    if _manager is None:
        if db is None or executor is None:
            raise ValueError("DatabaseManager and TradeExecutor required for first initialization")
        _manager = FirepipsAutonomousManager(db, executor, channel_id)
    return _manager
