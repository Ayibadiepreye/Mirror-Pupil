"""
BillirichyFX - Autonomous Management Actions
Implements Section 4.7 of the spec: Time-based autonomous trade management.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

from ...database import DatabaseManager, ActiveTrade
from ...core.account_manager import get_account_manager
from ...core.trade_executor import TradeExecutor


class BillirichyAutonomousManager:
    """
    Autonomous management for BillirichyFX trades.
    
    Per spec Section 4.7:
    - 15 minutes: Auto-assign TP if SL present but no TP
    - 1 hour: Move SL to BE if profit ≥ 15 pips (XAUUSD) or 8 pips (forex)
    - 2 hours: Close 50% if trade in profit
    - 4 hours: Close remaining 100%
    - 4:45 PM EST: Force close all (EOD) ✅ Already implemented in eod_close.py
    - Friday 4:45 PM EST: Force close all (weekend) ✅ Already implemented
    
    Runs every 60 seconds to check all active BillirichyFX trades.
    """
    
    def __init__(self, db: DatabaseManager, executor: TradeExecutor, channel_id: int):
        self.db = db
        self.executor = executor
        self.channel_id = channel_id  # -1001859598768 for BillirichyFX
        self.account_manager = get_account_manager()
        self.manager_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.check_interval = 60  # Check every 60 seconds
        
        # Profit thresholds for 1-hour BE action (in pips)
        self.be_profit_threshold = {
            'XAUUSD': 15.0,  # 15 pips for gold
            'default': 8.0   # 8 pips for forex
        }
        
        logger.info(f"Initialized BillirichyAutonomousManager (channel_id={channel_id})")
    
    async def start_managing(self):
        """Start background autonomous management task."""
        if self.manager_task:
            logger.warning("BillirichyFX autonomous manager already running")
            return
        
        self.manager_task = asyncio.create_task(self._management_loop())
        logger.info(f"✓ Started BillirichyFX autonomous management (every {self.check_interval}s)")
    
    async def stop_managing(self):
        """Stop background management task."""
        if self.manager_task:
            self.manager_task.cancel()
            try:
                await self.manager_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped BillirichyFX autonomous management")
    
    async def _management_loop(self):
        """Main management loop - runs every 60 seconds."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_all_trades()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"BillirichyFX autonomous management error: {e}")
    
    async def _check_all_trades(self):
        """Check all active BillirichyFX trades for autonomous actions."""
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
        1. 4 hours → Close 100%
        2. 2 hours → Close 50% (if in profit)
        3. 1 hour → Move SL to BE (if profit ≥ threshold)
        4. 15 minutes → Auto-assign TP (if SL present but no TP)
        """
        # Calculate time since entry
        time_since_entry = now - trade.entry_time
        
        # 4 HOURS: Close remaining 100% (unconditional)
        if time_since_entry >= timedelta(hours=4):
            await self._action_close_all(trade, "4-hour autonomous close")
            return
        
        # 2 HOURS: Close 50% if in profit (conditional)
        elif time_since_entry >= timedelta(hours=2):
            if await self._is_trade_in_profit(trade):
                await self._action_partial_close(trade, 0.50, "2-hour autonomous partial close")
                return
        
        # 1 HOUR: Move SL to BE if profit ≥ threshold (conditional)
        if time_since_entry >= timedelta(hours=1):
            if await self._should_move_to_be(trade):
                await self._action_breakeven(trade, "1-hour autonomous BE")
                return
        
        # 15 MINUTES: Auto-assign TP if SL present but no TP (conditional)
        if time_since_entry >= timedelta(minutes=15):
            if trade.sl and not trade.tp:
                await self._action_auto_assign_tp(trade)
                return
    
    async def _action_auto_assign_tp(self, trade: ActiveTrade):
        """
        Auto-assign TP = entry ± 2× SL distance.
        Per spec Section 4.7: 15-minute action.
        """
        sl_distance = abs(trade.entry_price - trade.sl)
        
        if trade.direction == 'BUY':
            auto_tp = trade.entry_price + (2 * sl_distance)
        else:  # SELL
            auto_tp = trade.entry_price - (2 * sl_distance)
        
        try:
            # Get TradeLocker client
            tl_client = self.account_manager.get_client_for_account(trade.account_key)
            if not tl_client:
                logger.warning(f"No TL client for {trade.account_key}")
                return
            
            # Modify order to add TP
            await tl_client.modify_position(
                position_id=int(trade.tl_position_id),
                take_profit=auto_tp
            )
            
            # Update database
            await self.db.update_trade_tp(trade.trade_id, auto_tp)
            
            logger.info(
                f"[AUTO-TP] {trade.signal_id} ({trade.symbol}): "
                f"Assigned TP={auto_tp:.5f} (entry={trade.entry_price:.5f}, sl={trade.sl:.5f})"
            )
            
        except Exception as e:
            logger.error(f"Failed to auto-assign TP for {trade.signal_id}: {e}")
    
    async def _action_breakeven(self, trade: ActiveTrade, reason: str):
        """Move SL to entry price (breakeven)."""
        try:
            # Get TradeLocker client
            tl_client = self.account_manager.get_client_for_account(trade.account_key)
            if not tl_client:
                return
            
            # Modify SL to entry price
            await tl_client.modify_position(
                position_id=int(trade.tl_position_id),
                stop_loss=trade.entry_price
            )
            
            # Update database
            await self.db.update_trade_sl(trade.trade_id, trade.entry_price)
            
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
                position_id=int(trade.tl_position_id),
                quantity=qty
            )
            
            # Update database
            new_lot_size = round(trade.lot_size - qty, 2)
            await self.db.update_trade_lot_size(trade.trade_id, new_lot_size)
            
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
            
            # PRIMARY: Use last saved current_pnl from database (updated every 15 seconds)
            pnl = trade.current_pnl
            
            if pnl is not None:
                logger.info(f"[{trade.account_key}] Using saved current_pnl: ${pnl:.2f}")
            else:
                # FALLBACK: Fetch unrealizedPl from TradeLocker position in real-time
                logger.warning(f"[{trade.account_key}] No saved PnL, fetching from TradeLocker...")
                if trade.tl_position_id:
                    try:
                        all_positions = await tl_client.get_all_positions()
                        position = next(
                            (p for p in all_positions if str(p.get('positionId') or p.get('id')) == str(trade.tl_position_id)),
                            None
                        )
                        if position:
                            pnl = position.get('unrealizedPl') or position.get('profit') or position.get('pnl')
                            if pnl is not None:
                                logger.info(f"[{trade.account_key}] Fetched TradeLocker unrealizedPl: ${pnl:.2f}")
                    except Exception as e:
                        logger.warning(f"[{trade.account_key}] Failed to fetch unrealizedPl: {e}")
                
                # LAST RESORT: Use 0.0 if still unavailable
                if pnl is None:
                    logger.error(f"[{trade.account_key}] Could not determine PnL, using 0.0")
                    pnl = 0.0
            
            # Get exit price for history record
            try:
                market_price = await tl_client.get_market_price(trade.symbol)
                exit_price = market_price if market_price else trade.entry_price
            except Exception:
                exit_price = trade.entry_price
            
            # Close full position on TradeLocker
            await tl_client.close_position(int(trade.tl_position_id))
            
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
        """Check if trade has positive floating P&L."""
        try:
            # Get current market price
            tl_client = self.account_manager.get_client_for_account(trade.account_key)
            if not tl_client:
                return False
            
            # Use existing get_market_price method
            market_price = await tl_client.get_market_price(trade.symbol)
            
            if not market_price or market_price <= 0:
                return False
            
            # Calculate profit in pips with correct multiplier per symbol
            # Forex (4 decimals): 1 pip = 0.0001 → * 10000
            # XAUUSD (2 decimals): 1 pip = 0.01 → * 100
            pip_multiplier = 100 if trade.symbol == 'XAUUSD' else 10000
            
            if trade.direction == 'BUY':
                profit_pips = (market_price - trade.entry_price) * pip_multiplier
            else:  # SELL
                profit_pips = (trade.entry_price - market_price) * pip_multiplier
            
            return profit_pips > 0
            
        except Exception as e:
            logger.error(f"Failed to check profit for {trade.signal_id}: {e}")
            return False
    
    async def _should_move_to_be(self, trade: ActiveTrade) -> bool:
        """
        Check if trade should move to BE.
        Requires profit ≥ 15 pips (XAUUSD) or 8 pips (forex).
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
            
            # Calculate profit in pips with correct multiplier per symbol
            # Forex (4 decimals): 1 pip = 0.0001 → * 10000
            # XAUUSD (2 decimals): 1 pip = 0.01 → * 100
            pip_multiplier = 100 if trade.symbol == 'XAUUSD' else 10000
            
            if trade.direction == 'BUY':
                profit_pips = (market_price - trade.entry_price) * pip_multiplier
            else:  # SELL
                profit_pips = (trade.entry_price - market_price) * pip_multiplier
            
            # Get threshold for this symbol
            threshold = self.be_profit_threshold.get(
                trade.symbol,
                self.be_profit_threshold['default']
            )
            
            return profit_pips >= threshold
            
        except Exception as e:
            logger.error(f"Failed to check BE condition for {trade.signal_id}: {e}")
            return False


# Singleton instance
_manager: Optional[BillirichyAutonomousManager] = None


def get_billirichy_autonomous_manager(
    db: Optional[DatabaseManager] = None,
    executor: Optional[TradeExecutor] = None,
    channel_id: int = -1001859598768
) -> BillirichyAutonomousManager:
    """Get or create singleton BillirichyFX autonomous manager."""
    global _manager
    if _manager is None:
        if db is None or executor is None:
            raise ValueError("DatabaseManager and TradeExecutor required for first initialization")
        _manager = BillirichyAutonomousManager(db, executor, channel_id)
    return _manager
