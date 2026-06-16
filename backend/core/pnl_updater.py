"""
Mirror Pupil - Live PnL Updater
Background service that updates unrealized PnL for active trades every 2 minutes.
"""

import asyncio
from typing import TYPE_CHECKING
from loguru import logger

from .account_manager import get_account_manager

if TYPE_CHECKING:
    from ..database import DatabaseManager


class LivePnLUpdater:
    """
    Background service that fetches live unrealized PnL from TradeLocker
    and updates active trades every 2 minutes.
    
    Features:
    - Non-blocking updates (doesn't interfere with other processes)
    - Per-account error isolation
    - Efficient batch processing
    - Graceful degradation on API errors
    """
    
    def __init__(self, db: "DatabaseManager", update_interval: int = 120):
        """
        Initialize PnL updater.
        
        Args:
            db: Database manager instance
            update_interval: Update interval in seconds (default: 120 = 2 minutes)
        """
        self.db = db
        self.update_interval = update_interval
        self.account_manager = get_account_manager()
        self.updater_task = None
        self.is_running = False
    
    def start(self):
        """Start the PnL updater background task."""
        if self.is_running:
            logger.warning("Live PnL updater already running")
            return
        
        self.is_running = True
        self.updater_task = asyncio.create_task(self._update_loop())
        logger.info(f"✓ Started live PnL updater (every {self.update_interval}s)")
    
    def stop(self):
        """Stop the PnL updater background task."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.updater_task:
            self.updater_task.cancel()
        logger.info("✓ Stopped live PnL updater")
    
    async def _update_loop(self):
        """Main update loop - runs every 2 minutes."""
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                
                if not self.is_running:
                    break
                
                await self._update_all_active_trades_pnl()
                
            except asyncio.CancelledError:
                logger.info("PnL updater loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in PnL updater loop: {e}")
                # Continue running despite errors
    
    async def _update_all_active_trades_pnl(self):
        """
        Update PnL for all active trades across all accounts.
        Runs non-blocking with per-account error isolation.
        """
        try:
            # Get all accounts
            accounts = await self.db.get_all_accounts()
            
            if not accounts:
                return
            
            # Process each account in parallel (non-blocking)
            tasks = [
                self._update_account_pnl(account.account_key)
                for account in accounts
                if not account.paused and not account.breached
            ]
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
        except Exception as e:
            logger.error(f"Failed to update PnL for active trades: {e}")
    
    async def _update_account_pnl(self, account_key: str):
        """
        Update PnL for all active trades in a single account.
        Also updates account-level daily_pnl.
        
        Args:
            account_key: Account key
        """
        try:
            # Get account details
            account = await self.db.get_account(account_key)
            if not account:
                return
            
            # Get active trades for this account
            trades = await self.db.get_active_trades(account_key)
            
            if not trades:
                # No active trades - still update daily_pnl (for closed trades)
                await self._update_account_daily_pnl(account_key, account, 0.0)
                return
            
            # Filter only filled trades with position IDs
            filled_trades = [
                t for t in trades 
                if t.status == 'filled' and t.tl_position_id
            ]
            
            if not filled_trades:
                # No filled trades - update daily_pnl with 0 floating
                await self._update_account_daily_pnl(account_key, account, 0.0)
                return
            
            # Get TradeLocker client
            account_info = self.account_manager.get_account(account_key)
            if not account_info or 'client' not in account_info:
                logger.debug(f"[{account_key}] Client not available for PnL update")
                return
            
            client = account_info['client']
            
            # Fetch all positions from TradeLocker
            positions = await client.get_all_positions()
            
            # Build position map
            position_map = {}
            for pos in positions:
                pos_id = str(pos.get('positionId') or pos.get('id'))
                if pos_id:
                    position_map[pos_id] = pos
            
            # Update PnL for each trade and accumulate total floating PnL
            updates_count = 0
            total_floating_pnl = 0.0
            
            for trade in filled_trades:
                try:
                    if trade.tl_position_id in position_map:
                        pos = position_map[trade.tl_position_id]
                        
                        # Extract unrealizedPl
                        unrealized_pnl = pos.get('unrealizedPl')
                        if unrealized_pnl is None:
                            # Fallback to profit or pnl fields
                            unrealized_pnl = pos.get('profit') or pos.get('pnl')
                        
                        if unrealized_pnl is not None:
                            # Update in database
                            await self.db.update_trade_current_pnl(
                                trade.trade_id,
                                unrealized_pnl
                            )
                            updates_count += 1
                            total_floating_pnl += unrealized_pnl
                            
                except Exception as e:
                    logger.warning(
                        f"[{account_key}] Failed to update PnL for trade {trade.trade_id}: {e}"
                    )
                    # Continue with other trades
            
            # Update account-level daily_pnl
            await self._update_account_daily_pnl(account_key, account, total_floating_pnl)
            
            if updates_count > 0:
                logger.debug(
                    f"[{account_key}] Updated PnL for {updates_count}/{len(filled_trades)} trades, "
                    f"floating P&L: ${total_floating_pnl:.2f}"
                )
                
        except Exception as e:
            logger.error(f"[{account_key}] Failed to update account PnL: {e}")
    
    async def _update_account_daily_pnl(
        self,
        account_key: str,
        account: "Account",
        floating_pnl: float
    ):
        """
        Update account-level daily_pnl.
        
        Formula: daily_pnl = (current_balance - daily_start_balance) + floating_pnl
        
        Args:
            account_key: Account key
            account: Account object
            floating_pnl: Total unrealized P&L from open positions
        """
        try:
            # Calculate realized P&L (from closed trades today)
            realized_pnl = (account.current_balance or 0.0) - (account.daily_start_balance or account.current_balance or 0.0)
            
            # Total daily P&L = realized + unrealized
            daily_pnl = realized_pnl + floating_pnl
            
            # Update in database
            await self.db.execute_raw(
                "UPDATE accounts SET daily_pnl = $1 WHERE account_key = $2",
                daily_pnl,
                account_key
            )
            
        except Exception as e:
            logger.error(f"[{account_key}] Failed to update daily_pnl: {e}")


# Global instance (singleton pattern)
_pnl_updater = None


def get_pnl_updater(db: "DatabaseManager") -> LivePnLUpdater:
    """
    Get or create the global PnL updater instance.
    
    Args:
        db: Database manager instance
    
    Returns:
        LivePnLUpdater instance
    """
    global _pnl_updater
    if _pnl_updater is None:
        _pnl_updater = LivePnLUpdater(db)
    return _pnl_updater
