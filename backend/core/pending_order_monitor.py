"""
Mirror Pupil v5.1 - Pending Order Monitor
Monitors pending LIMIT and STOP orders until they fill or expire.
"""

import asyncio
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from loguru import logger

from ..database import DatabaseManager, ActiveTrade
from .account_manager import get_account_manager


class PendingOrderMonitor:
    """
    Monitors pending orders (LIMIT and STOP) until they fill, cancel, or expire.
    
    Features:
    - Polls TradeLocker every 30 seconds for order status
    - Updates database when orders fill
    - Cancels orders after 24 hours (configurable)
    - Handles partial fills
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.account_manager = get_account_manager()
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Configuration (per spec Section 3.6, 5.5)
        self.poll_interval = 600  # Check every 10 minutes (spec requirement)
        self.order_expiry_hours = 2  # Cancel after 2 hours (spec requirement for BOTH channels)
        
        logger.info("Initialized PendingOrderMonitor")
    
    async def start_monitoring(self):
        """Start background monitoring task."""
        if self.monitor_task:
            logger.warning("Pending order monitoring already running")
            return
        
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"✓ Started pending order monitoring ({self.poll_interval}s interval)")
    
    async def stop_monitoring(self):
        """Stop background monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped pending order monitoring")
    
    async def _monitoring_loop(self):
        """Background task that monitors pending orders."""
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                
                # Get all pending trades from database
                pending_trades = await self._get_pending_trades()
                
                if not pending_trades:
                    continue
                
                logger.debug(f"Monitoring {len(pending_trades)} pending order(s)")
                
                # Check each pending trade
                for trade in pending_trades:
                    try:
                        await self._check_pending_trade(trade)
                    except Exception as e:
                        logger.error(f"Error checking pending trade {trade.trade_id}: {e}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pending order monitoring error: {e}")
    
    async def _get_pending_trades(self) -> List[ActiveTrade]:
        """Get all pending trades from database."""
        async with self.db.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM active_trades
                WHERE status IN ('pending', 'partially_filled')
                ORDER BY entry_time
                """
            )
            return [ActiveTrade(**dict(row)) for row in rows]
    
    async def _check_pending_trade(self, trade: ActiveTrade):
        """
        Check status of a pending trade.
        
        Possible outcomes:
        1. Order filled → Update status to 'filled', update fill_price
        2. Order partially filled → Update status to 'partially_filled'
        3. Order cancelled → Remove from active_trades
        4. Order expired (>24h) → Cancel order, remove from active_trades
        5. Still pending → No action
        """
        # Get account
        account = self.account_manager.get_account(trade.account_key)
        if not account:
            logger.error(f"Account not found: {trade.account_key}")
            return
        
        client = account['client']
        
        # Check if order expired
        if trade.entry_time:
            age = datetime.now() - trade.entry_time
            if age > timedelta(hours=self.order_expiry_hours):
                logger.warning(
                    f"[{trade.account_key}] Order {trade.tl_order_id} expired "
                    f"(age: {age.total_seconds()/3600:.1f}h)"
                )
                await self._cancel_expired_order(trade, client)
                return
        
        # Get order status from TradeLocker
        try:
            order_status = await client.get_order_status(trade.tl_order_id)
            
            if not order_status:
                logger.warning(f"Order {trade.tl_order_id} not found on TradeLocker")
                return
            
            status = order_status.get('status', '').lower()
            filled_qty = order_status.get('filledQuantity', 0)
            fill_price = order_status.get('fillPrice') or order_status.get('avgPrice')
            
            # Handle different statuses
            if status == 'filled':
                await self._handle_order_filled(trade, fill_price, filled_qty)
            
            elif status == 'partially_filled':
                await self._handle_order_partially_filled(trade, fill_price, filled_qty)
            
            elif status in ['cancelled', 'rejected', 'expired']:
                await self._handle_order_cancelled(trade, status)
            
            elif status == 'pending':
                # Still pending, no action needed
                pass
            
            else:
                logger.warning(f"Unknown order status: {status} for order {trade.tl_order_id}")
        
        except Exception as e:
            logger.error(f"Failed to check order {trade.tl_order_id}: {e}")
    
    async def _handle_order_filled(self, trade: ActiveTrade, fill_price: float, filled_qty: float):
        """Handle order that has been filled."""
        logger.info(
            f"[{trade.account_key}] ✓ Order {trade.tl_order_id} FILLED: "
            f"{trade.symbol} {trade.direction} @ {fill_price}"
        )
        
        # Update trade in database
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE active_trades
                SET status = 'filled',
                    entry_price = $1,
                    lot_size = $2
                WHERE trade_id = $3
                """,
                fill_price,
                filled_qty,
                trade.trade_id
            )
        
        logger.info(f"[{trade.account_key}] ✅ Trade {trade.trade_id} updated to FILLED")
    
    async def _handle_order_partially_filled(
        self,
        trade: ActiveTrade,
        fill_price: float,
        filled_qty: float
    ):
        """Handle order that has been partially filled."""
        logger.info(
            f"[{trade.account_key}] ⚠ Order {trade.tl_order_id} PARTIALLY FILLED: "
            f"{filled_qty}/{trade.lot_size} lots @ {fill_price}"
        )
        
        # Update trade in database
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE active_trades
                SET status = 'partially_filled',
                    entry_price = $1,
                    lot_size = $2
                WHERE trade_id = $3
                """,
                fill_price,
                filled_qty,
                trade.trade_id
            )
        
        logger.info(
            f"[{trade.account_key}] ✅ Trade {trade.trade_id} updated to PARTIALLY FILLED"
        )
    
    async def _handle_order_cancelled(self, trade: ActiveTrade, reason: str):
        """Handle order that was cancelled or rejected."""
        logger.warning(
            f"[{trade.account_key}] ❌ Order {trade.tl_order_id} {reason.upper()}: "
            f"{trade.symbol} {trade.direction}"
        )
        
        # Remove from active_trades (order never filled)
        async with self.db.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM active_trades WHERE trade_id = $1",
                trade.trade_id
            )
        
        logger.info(
            f"[{trade.account_key}] ✅ Cancelled trade {trade.trade_id} removed from database"
        )
    
    async def _cancel_expired_order(self, trade: ActiveTrade, client):
        """Cancel an expired pending order."""
        try:
            # Cancel order on TradeLocker
            await client.delete_order(trade.tl_order_id)
            logger.info(
                f"[{trade.account_key}] ✓ Cancelled expired order {trade.tl_order_id}"
            )
        except Exception as e:
            logger.error(
                f"[{trade.account_key}] Failed to cancel order {trade.tl_order_id}: {e}"
            )
        
        # Remove from database
        await self._handle_order_cancelled(trade, "expired")
    
    async def get_pending_orders_summary(self, account_key: Optional[str] = None) -> Dict:
        """
        Get summary of pending orders.
        
        Args:
            account_key: Filter by account (None = all accounts)
        
        Returns:
            Dict with pending order statistics
        """
        if account_key:
            query = """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                       SUM(CASE WHEN status = 'partially_filled' THEN 1 ELSE 0 END) as partial
                FROM active_trades
                WHERE account_key = $1 AND status IN ('pending', 'partially_filled')
            """
            params = [account_key]
        else:
            query = """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                       SUM(CASE WHEN status = 'partially_filled' THEN 1 ELSE 0 END) as partial
                FROM active_trades
                WHERE status IN ('pending', 'partially_filled')
            """
            params = []
        
        async with self.db.pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
        
        return {
            "total": row['total'] or 0,
            "pending": row['pending'] or 0,
            "partially_filled": row['partial'] or 0
        }


# Global monitor instance
_monitor: Optional[PendingOrderMonitor] = None


async def get_pending_order_monitor(db: DatabaseManager) -> PendingOrderMonitor:
    """Get the global pending order monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = PendingOrderMonitor(db)
        await _monitor.start_monitoring()
    return _monitor
