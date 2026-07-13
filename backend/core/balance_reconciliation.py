"""
Mirror Pupil v5.1 - Balance Reconciliation Monitor
Polls TradeLocker every 5 minutes to detect withdrawals and balance changes.
Implements Section 2.9 of the spec.
"""

import asyncio
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from loguru import logger

from ..database.models import Account
from .account_manager import get_account_manager

if TYPE_CHECKING:
    from ..database import DatabaseManager


# Threshold for detecting meaningful balance changes (ignore smaller fluctuations)
WITHDRAWAL_THRESHOLD = 0.50  # $0.50


class BalanceReconciliationMonitor:
    """
    Monitors account balances every 5 minutes to detect external changes.
    
    Features:
    - Polls TradeLocker API every 5 minutes per account
    - Detects withdrawals (balance drop without closed trade)
    - Detects deposits/corrections (balance increase)
    - Updates current_balance and last_synced_balance
    - Does NOT change highest_banked_balance (floor never moves down)
    - Does NOT change daily_start_balance (daily floor is static)
    - Sends WARNING notifications on withdrawal
    - Broadcasts WebSocket events for GUI updates
    
    Per spec Section 2.9:
    - Withdrawal: balance drops, floor stays same, headroom decreases
    - Formal payout reset: everything resets (separate GUI action)
    """
    
    def __init__(self, db: "DatabaseManager"):
        self.db = db
        self.account_manager = get_account_manager()
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Configuration (per spec Section 2.9)
        self.poll_interval = 300  # 5 minutes = 300 seconds
        
        logger.info("Initialized BalanceReconciliationMonitor")
    
    async def start_monitoring(self):
        """Start background monitoring task."""
        if self.monitor_task:
            logger.warning("Balance reconciliation already running")
            return
        
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info(f"✓ Started balance reconciliation (every {self.poll_interval}s)")
    
    async def stop_monitoring(self):
        """Stop background monitoring task."""
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped balance reconciliation")
    
    async def _monitoring_loop(self):
        """Main monitoring loop - runs every 5 minutes."""
        while True:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._reconcile_all_accounts()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Balance reconciliation error: {e}")
    
    async def _reconcile_all_accounts(self):
        """Reconcile balances for all active accounts."""
        accounts = await self.db.get_all_accounts()
        
        for account in accounts:
            if account.breached or account.paused:
                continue  # Skip breached/paused accounts
            
            try:
                await self._reconcile_account(account)
            except Exception as e:
                logger.error(
                    f"Failed to reconcile account {account.account_key}: {e}"
                )
    
    async def _reconcile_account(self, account: Account):
        """
        Reconcile a single account's balance.
        
        Compares actual TradeLocker balance vs last_synced_balance.
        Detects withdrawals and deposits.
        """
        # Get actual balance from TradeLocker
        tl_client = self.account_manager.get_client(account.credential_key)
        if not tl_client:
            logger.warning(
                f"No TradeLocker client for {account.account_key}"
            )
            return
        
        try:
            # Poll actual balance (client is dedicated to this account)
            account_info = await tl_client.get_account_state()
            actual_balance = float(account_info.get('balance') or account_info.get('accountBalance', 0))
            
            # Calculate equity (balance + floating PnL)
            open_pnl = float(account_info.get('openNetPnL', 0.0) or account_info.get('openGrossPnL', 0.0) or 0.0)
            equity = actual_balance + open_pnl
            
            # Update all_time_high_equity if this is a new high
            if equity > (account.all_time_high_equity or 0.0):
                await self.db.update_account_balance(account.account_key, actual_balance, equity)
            
            # CRITICAL FIX: Update highest_banked_balance when balance reaches new high
            # This is what makes the trailing floor work correctly
            if actual_balance > (account.highest_banked_balance or 0.0):
                await self.db.update_account(
                    account.account_key,
                    highest_banked_balance=actual_balance
                )
                logger.info(
                    f"[{account.account_key}] New highest banked balance: "
                    f"${account.highest_banked_balance or 0:.2f} → ${actual_balance:.2f}"
                )
            
        except Exception as e:
            logger.error(
                f"Failed to fetch balance for {account.account_key}: {e}"
            )
            return
        
        # Compare to expected balance
        expected_balance = account.last_synced_balance or account.current_balance
        delta = expected_balance - actual_balance
        
        # Check for meaningful changes
        if abs(delta) < WITHDRAWAL_THRESHOLD:
            # Normal - just sync
            await self.db.update_account(
                account.account_key,
                last_synced_balance=actual_balance
            )
            return
        
        # Meaningful change detected
        if delta > WITHDRAWAL_THRESHOLD:
            # Balance dropped - withdrawal detected
            await self._handle_withdrawal(account, actual_balance, delta, expected_balance)
        
        elif actual_balance > account.current_balance + WITHDRAWAL_THRESHOLD:
            # Balance increased - deposit or correction
            await self._handle_deposit(account, actual_balance)
    
    async def _handle_withdrawal(
        self,
        account: Account,
        actual_balance: float,
        withdrawn: float,
        expected_balance: float
    ):
        """
        Handle detected withdrawal.
        
        Per spec Section 2.9:
        - current_balance → actual_balance (balance is lower)
        - last_synced_balance → actual_balance (sync reference)
        - highest_banked_balance → UNCHANGED (floor never moves down)
        - daily_start_balance → UNCHANGED (daily floor is static until 5pm)
        - profit_locked → UNCHANGED (lock status unaffected)
        - initial_balance → UNCHANGED (only changes on formal reset)
        """
        logger.warning(
            f"[WITHDRAWAL DETECTED] {account.account_key}: "
            f"−${withdrawn:.2f} (${expected_balance:.2f} → ${actual_balance:.2f})"
        )
        
        # Update balances (but NOT floors or profit lock)
        await self.db.update_account(
            account.account_key,
            current_balance=actual_balance,
            last_synced_balance=actual_balance
        )
        
        # Recalculate headroom
        overall_floor = await self._calculate_overall_floor(account)
        daily_floor = await self._calculate_daily_floor(account)
        
        # Get floating P&L
        floating_pnl = await self._get_floating_pnl(account)
        current_equity = actual_balance + floating_pnl
        
        overall_room = actual_balance - overall_floor
        daily_room = current_equity - daily_floor
        
        # Calculate new withdrawable amount
        withdrawable = await self._calculate_withdrawable(account, actual_balance)
        
        # Send WARNING notification
        message = (
            f"Withdrawal detected on {account.display_name or account.account_key}: "
            f"−${withdrawn:.2f}. "
            f"Balance: ${actual_balance:.2f}. "
            f"Overall room: ${overall_room:.2f}. "
            f"Daily room: ${daily_room:.2f}. "
            f"New withdrawable: ${withdrawable:.2f}."
        )
        
        await self._notify_gui(message, severity="WARNING", account_key=account.account_key)
        
        # Broadcast WebSocket event for GUI update
        await self._broadcast_balance_update(
            account=account,
            actual_balance=actual_balance,
            floating_pnl=floating_pnl,
            withdrawable=withdrawable,
            overall_floor=overall_floor,
            daily_floor=daily_floor
        )
    
    async def _handle_deposit(self, account: Account, actual_balance: float):
        """
        Handle detected deposit or balance correction.
        
        Updates current_balance only - does NOT touch highest_banked_balance.
        """
        increase = actual_balance - account.current_balance
        
        logger.info(
            f"[BALANCE INCREASE] {account.account_key}: "
            f"+${increase:.2f} (${account.current_balance:.2f} → ${actual_balance:.2f})"
        )
        
        # Update balances
        await self.db.update_account(
            account.account_key,
            current_balance=actual_balance,
            last_synced_balance=actual_balance
        )
        
        # Send INFO notification
        message = (
            f"Balance increase detected on {account.display_name or account.account_key}: "
            f"+${increase:.2f}"
        )
        
        await self._notify_gui(message, severity="INFO", account_key=account.account_key)
    
    async def _calculate_overall_floor(self, account: Account) -> float:
        """Calculate overall floor (trails from highest_banked_balance)."""
        # Get risk profile
        profile = await self._get_risk_profile(account)
        
        if account.profit_locked:
            # Profit lock active - floor locked at initial_balance
            return account.initial_balance * (1 - (profile.profit_lock_floor_pct or 0) / 100)
        
        if profile.overall_trailing:
            # Trailing from highest_banked_balance (Blue Guardian model)
            trail_ref = account.highest_banked_balance
            return trail_ref - (account.initial_balance * profile.overall_loss_pct / 100)
        else:
            # Static floor
            return account.initial_balance * (1 - profile.overall_loss_pct / 100)
    
    async def _calculate_daily_floor(self, account: Account) -> float:
        """Calculate daily floor (static for the day)."""
        profile = await self._get_risk_profile(account)
        return account.daily_start_balance - (account.initial_balance * profile.daily_loss_pct / 100)
    
    async def _calculate_withdrawable(self, account: Account, current_balance: float) -> float:
        """Calculate maximum safe withdrawal amount."""
        profile = await self._get_risk_profile(account)
        payout_buffer = account.initial_balance * (profile.payout_buffer_pct / 100)
        
        overall_floor = await self._calculate_overall_floor(account)
        withdrawable = current_balance - overall_floor - payout_buffer
        
        return max(withdrawable, 0.0)
    
    async def _get_risk_profile(self, account: Account):
        """Get account's risk profile from database."""
        try:
            if account.risk_profile_id:
                profile = await self.db.get_risk_profile(account.risk_profile_id)
            else:
                profile = await self.db.get_default_risk_profile()
            
            if not profile:
                logger.warning(f"No risk profile found for {account.account_key}, using defaults")
                # Fallback to Blue Guardian defaults
                from dataclasses import dataclass
                
                @dataclass
                class DefaultProfile:
                    daily_loss_pct: float = 3.0
                    overall_loss_pct: float = 6.0
                    overall_trailing: bool = True
                    profit_lock_floor_pct: float = 0.0
                    payout_buffer_pct: float = 1.0
                
                return DefaultProfile()
            
            return profile
        except Exception as e:
            logger.error(f"Failed to get risk profile: {e}")
            # Return safe defaults
            from dataclasses import dataclass
            
            @dataclass
            class DefaultProfile:
                daily_loss_pct: float = 3.0
                overall_loss_pct: float = 6.0
                overall_trailing: bool = True
                profit_lock_floor_pct: float = 0.0
                payout_buffer_pct: float = 1.0
            
            return DefaultProfile()
    
    async def _get_floating_pnl(self, account: Account) -> float:
        """Get floating P&L for account."""
        try:
            # Get TradeLocker client
            tl_account = self.account_manager.get_account(account.account_key)
            if not tl_account:
                return 0.0
            
            client = tl_account['client']
            
            # Get open positions
            positions = await client.get_all_positions()
            
            # Calculate total floating P&L
            total_pnl = 0.0
            for pos in positions:
                # Try different field names (API may vary)
                pnl = float(pos.get('unrealizedPl', 0) or pos.get('profit', 0) or pos.get('pnl', 0))
                total_pnl += pnl
            
            return total_pnl
            
        except Exception as e:
            logger.error(f"Failed to get floating P&L for {account.account_key}: {e}")
            return 0.0
    
    async def _notify_gui(self, message: str, severity: str, account_key: str):
        """Send notification to GUI via WebSocket."""
        try:
            # Log the notification
            logger.log(severity, message)
            
            # Send to GUI notification system
            # Import WebSocket manager when available
            try:
                from ..api.websocket import get_websocket_manager
                ws_manager = get_websocket_manager()
                
                notification_payload = {
                    "type": "notification",
                    "severity": severity,
                    "message": message,
                    "account_key": account_key,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await ws_manager.broadcast(notification_payload)
                logger.debug(f"[GUI NOTIFICATION] Sent: {severity} - {message}")
                
            except ImportError:
                logger.debug("WebSocket manager not available, notification logged only")
            except Exception as e:
                logger.warning(f"Failed to send GUI notification via WebSocket: {e}")
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    async def _broadcast_balance_update(
        self,
        account: Account,
        actual_balance: float,
        floating_pnl: float,
        withdrawable: float,
        overall_floor: float,
        daily_floor: float
    ):
        """Broadcast balance update via WebSocket."""
        try:
            payload = {
                "type": "balance_updated",
                "account_key": account.account_key,
                "current_balance": actual_balance,
                "daily_pnl": account.daily_pnl,
                "equity": actual_balance + floating_pnl,
                "withdrawable": withdrawable,
                "overall_floor": overall_floor,
                "daily_floor": daily_floor,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.debug(f"[WS] Balance update: {payload}")
            
            # Broadcast via WebSocket
            try:
                from ..api.websocket import get_websocket_manager
                ws_manager = get_websocket_manager()
                await ws_manager.broadcast(payload)
                logger.debug(f"[WS] Broadcasted balance update for {account.account_key}")
                
            except ImportError:
                logger.debug("WebSocket manager not available, balance update logged only")
            except Exception as e:
                logger.warning(f"Failed to broadcast balance update: {e}")
                
        except Exception as e:
            logger.error(f"Failed to create balance update payload: {e}")


# Singleton instance
_monitor: Optional[BalanceReconciliationMonitor] = None


def get_balance_monitor(db: Optional["DatabaseManager"] = None) -> BalanceReconciliationMonitor:
    """Get or create singleton balance reconciliation monitor."""
    global _monitor
    if _monitor is None:
        if db is None:
            raise ValueError("DatabaseManager required for first initialization")
        _monitor = BalanceReconciliationMonitor(db)
    return _monitor
