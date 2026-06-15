# -*- coding: utf-8 -*-
"""
Mirror Pupil v5.1 - Position Reconciliation Monitor
Detects when TradeLocker closes positions (TP/SL hits) and updates database.
"""

import asyncio
from typing import Optional, Dict, List, Set, TYPE_CHECKING
from loguru import logger
from datetime import datetime

from ..database.models import ActiveTrade
from .account_manager import get_account_manager

if TYPE_CHECKING:
    from ..database import DatabaseManager


class PositionReconciliationMonitor:
    """
    Monitors active trades and detects when positions close on TradeLocker.
    
    Features:
    - Runs every 60 seconds
    - Compares database active_trades vs TradeLocker positions
    - Detects TP/SL hits, manual closes, or other external closures
    - Calculates P&L and moves closed trades to history
    - Updates balance and reconciles account state
    """
    
    def __init__(self, db: "DatabaseManager"):
        self.db = db
        self.account_manager = get_account_manager()
        self.notification_service = None  # Lazy-loaded to avoid circular import
        self.monitor_task: Optional[asyncio.Task] = None
        self.poll_interval = 60  # Check every 60 seconds
        
        logger.info("Initialized PositionReconciliationMonitor")
    
    def _get_notification_service(self):
        """Lazy-load notification service to avoid circular import."""
        if self.notification_service is None:
            from .notification_service import get_notification_service
            self.notification_service = get_notification_service(self.db)
        return self.notification_service
    
    async def start_monitoring(self):
        """Start background monitoring task."""
        if self.monitor_task:
            logger.warning("Position reconciliation already running")
            return
        
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"✓ Started position reconciliation (every {self.poll_interval}s)")
    
    async def stop_monitoring(self):
        """Stop background monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped position reconciliation")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._reconcile_all_accounts()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Position reconciliation error: {e}")
    
    async def _reconcile_all_accounts(self):
        """Check all accounts for closed positions."""
        accounts = await self.db.get_all_accounts()
        
        for account in accounts:
            if account.breached or account.paused:
                continue  # Skip breached/paused accounts
            
            try:
                await self._reconcile_account(account.account_key)
            except Exception as e:
                logger.error(
                    f"Failed to reconcile positions for {account.account_key}: {e}"
                )
    
    async def _reconcile_account(self, account_key: str):
        """
        Reconcile positions for a single account.
        
        Process:
        1. Get all active trades from database (status='filled')
        2. Get all open positions from TradeLocker
        3. Find trades where position no longer exists
        4. Determine close reason (TP hit, SL hit, or unknown)
        5. Calculate P&L and move to history
        """
        # Get active trades from database
        active_trades = await self.db.get_active_trades(account_key)
        filled_trades = [t for t in active_trades if t.status == 'filled']
        
        if not filled_trades:
            return  # No active positions to check
        
        # Get TradeLocker client
        account = self.account_manager.get_account(account_key)
        if not account:
            logger.warning(f"No account found for {account_key}")
            return
        
        client = account['client']
        
        # Get all open positions from TradeLocker
        try:
            tl_positions = await client.get_all_positions()
        except Exception as e:
            logger.error(f"Failed to fetch positions for {account_key}: {e}")
            return
        
        # Build set of open position IDs
        open_position_ids: Set[str] = {
            str(p.get('id')) for p in tl_positions if p.get('id')
        }
        
        # Check each active trade
        for trade in filled_trades:
            if not trade.tl_position_id:
                continue  # Skip trades without position_id
            
            # Check if position still exists on TradeLocker
            if trade.tl_position_id not in open_position_ids:
                # Position closed - reconcile it
                await self._handle_closed_position(
                    trade, client, account_key
                )
    
    async def _handle_closed_position(
        self,
        trade: ActiveTrade,
        client,
        account_key: str
    ):
        """
        Handle a position that closed on TradeLocker.
        
        Process:
        1. Determine close reason (TP hit, SL hit, or unknown)
        2. Get exit price from closed positions history (if available)
        3. Calculate P&L in USD
        4. Move to trade_history
        5. Update account balance
        """
        logger.info(
            f"[{account_key}] Position closed externally: {trade.symbol} "
            f"{trade.direction} (position_id: {trade.tl_position_id})"
        )
        
        # Try to get exit price from recent trade history
        exit_price = None
        close_reason = "EXTERNAL"
        
        try:
            # Get recent closed positions (TradeLocker may have history)
            # Note: This depends on TradeLocker API capabilities
            # Fallback to current market price if unavailable
            market_price = await client.get_market_price(trade.symbol)
            exit_price = market_price if market_price else trade.entry_price
            
            # Determine close reason based on exit price proximity to TP/SL
            if trade.tp and abs(exit_price - trade.tp) < 0.01:  # Within 1 pip
                close_reason = "TP_HIT"
                logger.info(f"[{account_key}] Detected TP hit for {trade.symbol}")
            elif trade.sl and abs(exit_price - trade.sl) < 0.01:  # Within 1 pip
                close_reason = "SL_HIT"
                logger.info(f"[{account_key}] Detected SL hit for {trade.symbol}")
            else:
                close_reason = "EXTERNAL"
                logger.info(f"[{account_key}] Position closed externally for {trade.symbol}")
            
        except Exception as e:
            logger.error(f"Failed to get exit price for {trade.symbol}: {e}")
            exit_price = trade.entry_price  # Fallback
        
        # Calculate P&L in USD
        try:
            # Get instrument details
            instruments = await client.get_all_instruments()
            instrument = next(
                (i for i in instruments if trade.symbol in i.get('name', '')),
                None
            )
            
            # Use proper USD P&L calculation
            from ..risk.calculator import calculate_usd_pnl
            pnl = await calculate_usd_pnl(
                symbol=trade.symbol,
                entry_price=trade.entry_price,
                exit_price=exit_price,
                lot_size=trade.lot_size,
                direction=trade.direction,
                client=client,
                instrument=instrument
            )
        except Exception as e:
            logger.error(f"Failed to calculate P&L for {trade.symbol}: {e}")
            pnl = 0.0
        
        # Move to history
        try:
            await self.db.move_trade_to_history(
                trade.trade_id,
                exit_price=exit_price,
                pnl=pnl,
                outcome="WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BE",
                close_reason=close_reason
            )
            
            logger.info(
                f"[{account_key}] ✓ Reconciled closed position: {trade.symbol} "
                f"P&L=${pnl:.2f} Reason={close_reason}"
            )
            
            # Send notification for trade closure
            await self._get_notification_service().trade_closed(
                account_key=account_key,
                symbol=trade.symbol,
                pnl=pnl,
                close_reason=close_reason
            )
            
            # Update account balance
            account_db = await self.db.get_account(account_key)
            if account_db:
                new_balance = account_db.current_balance + pnl
                await self.db.update_account(
                    account_key,
                    current_balance=new_balance,
                    last_synced_balance=new_balance
                )
                
                logger.debug(
                    f"[{account_key}] Updated balance: "
                    f"${account_db.current_balance:.2f} → ${new_balance:.2f}"
                )
        
        except Exception as e:
            logger.error(
                f"Failed to move trade {trade.trade_id} to history: {e}"
            )


# Global monitor instance
_monitor: Optional[PositionReconciliationMonitor] = None


async def get_position_reconciliation_monitor(db: "DatabaseManager") -> PositionReconciliationMonitor:
    """Get the global position reconciliation monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = PositionReconciliationMonitor(db)
    return _monitor
