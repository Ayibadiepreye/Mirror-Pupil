"""
Mirror Pupil v5.1 - Risk Enforcer
Pre-trade risk validation and breach detection.
"""

import asyncio
from typing import Optional, Dict, List
from loguru import logger

from ..database import DatabaseManager, Account, RiskProfile, ActiveTrade
from .calculator import RiskCalculator, calculate_price_delta, get_risk_calculator


class RiskEnforcer:
    """
    Enforces risk limits and validates trades before execution.
    
    Features:
    - Pre-trade risk validation
    - Breach detection (runs every 60 seconds)
    - Concurrent trade limits
    - Channel priority handling
    """
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.calculator = get_risk_calculator()
        self.breach_check_task: Optional[asyncio.Task] = None
        
        logger.info("Initialized RiskEnforcer")
    
    async def start_breach_monitoring(self):
        """Start background breach monitoring task (runs every 60 seconds)."""
        if self.breach_check_task:
            logger.warning("Breach monitoring already running")
            return
        
        self.breach_check_task = asyncio.create_task(self._breach_monitoring_loop())
        logger.info("✓ Started breach monitoring (60s interval)")
    
    async def stop_breach_monitoring(self):
        """Stop background breach monitoring task."""
        if self.breach_check_task:
            self.breach_check_task.cancel()
            try:
                await self.breach_check_task
            except asyncio.CancelledError:
                pass
            logger.info("✓ Stopped breach monitoring")
    
    async def _breach_monitoring_loop(self):
        """Background task that checks all accounts for breaches every 60 seconds."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every 60 seconds
                
                accounts = await self.db.get_all_accounts()
                
                for account in accounts:
                    if account.breached or account.paused:
                        continue  # Skip already breached or paused accounts
                    
                    # Get risk profile
                    if account.risk_profile_id:
                        profile = await self.db.get_risk_profile(account.risk_profile_id)
                    else:
                        profile = await self.db.get_default_risk_profile()
                    
                    if not profile:
                        logger.error(f"No risk profile found for {account.account_key}")
                        continue
                    
                    # Check for breach
                    await self.check_risk_limits(account, profile)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Breach monitoring error: {e}")
    
    async def validate_trade(
        self,
        account: Account,
        profile: RiskProfile,
        entry_price: float,
        sl_price: float,
        lot_size: float,
        symbol: str,
        client = None,  # TradeLocker client for live price fetching
        instrument: Optional[Dict] = None
    ) -> Dict:
        """
        Validate a trade before execution.
        
        Checks:
        1. Combined portfolio risk limit
        2. Daily loss limit (with safety buffer)
        3. Overall loss limit
        4. Concurrent trade limit
        
        Args:
            account: Account object
            profile: Risk profile
            entry_price: Entry price
            sl_price: Stop loss price
            lot_size: Lot size
            symbol: Trading symbol
            client: TradeLocker client (for fetching live prices)
            instrument: Instrument data dict (optional)
        
        Returns:
            Dict with 'allowed' (bool) and 'reason' (str)
        """
        # Calculate trade risk using the correct async function
        if client:
            from .calculator import calculate_usd_risk
            
            # Fetch current price for conversion
            current_price = None
            try:
                current_price = await client.get_market_price(symbol)
            except Exception as e:
                logger.warning(f"Could not fetch current price for {symbol}: {e}")
            
            trade_risk = await calculate_usd_risk(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=sl_price,
                lot_size=lot_size,
                client=client,
                current_price=current_price,
                instrument=instrument
            )
        else:
            # Fallback to legacy function (less accurate)
            from .calculator import calculate_price_delta
            logger.warning("No TradeLocker client provided, using legacy risk calculation")
            trade_risk = calculate_price_delta(
                entry_price=entry_price,
                sl_price=sl_price,
                lot_size=lot_size,
                symbol=symbol
            )
        
        # Get active trades
        active_trades = await self.db.get_active_trades(account.account_key)
        active_count = len(active_trades)
        
        # Calculate existing portfolio risk
        existing_risk = sum(trade.risk_usd or 0.0 for trade in active_trades)
        
        # Calculate current equity (balance + floating P&L)
        # For now, use balance (floating P&L calculation requires TradeLocker API)
        current_equity = account.current_balance or 0.0
        
        # Check 1: Concurrent trade limit
        max_concurrent = account.max_concurrent_trades_override or profile.max_concurrent_trades
        if active_count >= max_concurrent:
            return {
                "allowed": False,
                "reason": f"Concurrent trade limit reached ({active_count}/{max_concurrent})"
            }
        
        # Check 2: Combined portfolio risk limit
        max_risk = account.initial_balance * profile.max_risk_per_trade_pct / 100
        combined_risk = existing_risk + trade_risk
        
        if combined_risk > max_risk:
            return {
                "allowed": False,
                "reason": f"Combined risk ${combined_risk:.2f} exceeds limit ${max_risk:.2f}"
            }
        
        # Check 3: Daily loss limit (with safety buffer)
        daily_floor = self.calculator.calculate_daily_floor(account, profile)
        daily_room = current_equity - daily_floor
        safety_buffer = daily_room * (profile.safety_buffer_pct / 100)
        buffered_daily_room = daily_room - safety_buffer
        
        if trade_risk > buffered_daily_room:
            return {
                "allowed": False,
                "reason": f"Trade risk ${trade_risk:.2f} exceeds buffered daily room ${buffered_daily_room:.2f}"
            }
        
        # Check 4: Overall loss limit
        overall_floor = self.calculator.calculate_overall_floor(account, profile)
        overall_room = current_equity - overall_floor
        
        if trade_risk > overall_room:
            return {
                "allowed": False,
                "reason": f"Trade risk ${trade_risk:.2f} exceeds overall room ${overall_room:.2f}"
            }
        
        # All checks passed
        return {
            "allowed": True,
            "reason": "All risk checks passed",
            "trade_risk": trade_risk
        }
    
    async def check_risk_limits(self, account: Account, profile: RiskProfile) -> bool:
        """
        Check if account has breached risk limits.
        
        Checks:
        - Daily loss floor
        - Overall loss floor
        - Profit lock trigger
        
        Returns:
            True if breached, False otherwise
        """
        # Calculate current equity (balance + floating P&L)
        # For now, use balance (floating P&L requires TradeLocker API)
        current_equity = account.current_balance or 0.0
        
        # Check daily loss
        daily_floor = self.calculator.calculate_daily_floor(account, profile)
        if current_equity <= daily_floor:
            logger.critical(
                f"[{account.account_key}] DAILY LOSS BREACHED: "
                f"Equity ${current_equity:.2f} ≤ Floor ${daily_floor:.2f}"
            )
            
            # Mark as breached
            account.breached = True
            await self.db.update_account_paused(account.account_key, True)
            
            # Close all trades
            await self._close_all_account_trades(account.account_key, "DAILY_BREACH")
            
            # Notify GUI
            await self._notify_breach(
                account.account_key,
                "DAILY_LOSS_BREACH",
                f"Equity ${current_equity:.2f} ≤ Floor ${daily_floor:.2f}"
            )
            
            return True
        
        # Check overall loss
        overall_floor = self.calculator.calculate_overall_floor(account, profile)
        if current_equity <= overall_floor:
            logger.critical(
                f"[{account.account_key}] OVERALL DRAWDOWN BREACHED: "
                f"Equity ${current_equity:.2f} ≤ Floor ${overall_floor:.2f}"
            )
            
            # Mark as breached
            account.breached = True
            await self.db.update_account_paused(account.account_key, True)
            
            # Close all trades
            await self._close_all_account_trades(account.account_key, "OVERALL_BREACH")
            
            # Notify GUI
            await self._notify_breach(
                account.account_key,
                "OVERALL_DRAWDOWN_BREACH",
                f"Equity ${current_equity:.2f} ≤ Floor ${overall_floor:.2f}"
            )
            
            return True
        
        # Check profit lock trigger
        if self.calculator.check_profit_lock_trigger(account, profile):
            logger.info(
                f"[{account.account_key}] PROFIT LOCK ACTIVATED: "
                f"Balance ${account.current_balance:.2f} reached threshold"
            )
            
            # Update account.profit_locked in database
            await self.db.update_account_profit_locked(account.account_key, True)
            account.profit_locked = True
            
            # Notify GUI
            await self._notify_breach(
                account.account_key,
                "PROFIT_LOCK_ACTIVATED",
                f"Balance ${account.current_balance:.2f} - Floor now locked at initial balance"
            )
        
        return False
    
    async def get_max_concurrent_trades(self, account_key: str) -> int:
        """
        Get max concurrent trades for an account.
        
        Returns account override if set, otherwise profile default.
        """
        account = await self.db.get_account(account_key)
        if not account:
            return 5  # Default fallback
        
        if account.max_concurrent_trades_override:
            return account.max_concurrent_trades_override
        
        # Get from profile
        if account.risk_profile_id:
            profile = await self.db.get_risk_profile(account.risk_profile_id)
        else:
            profile = await self.db.get_default_risk_profile()
        
        return profile.max_concurrent_trades if profile else 5
    
    async def _close_all_account_trades(self, account_key: str, reason: str):
        """
        Close all active trades for an account.
        
        Args:
            account_key: Account identifier
            reason: Close reason (e.g., "DAILY_BREACH", "OVERALL_BREACH")
        """
        try:
            # Get all active trades
            active_trades = await self.db.get_active_trades(account_key)
            
            if not active_trades:
                logger.debug(f"[{account_key}] No active trades to close")
                return
            
            logger.info(f"[{account_key}] Closing {len(active_trades)} trade(s) due to {reason}")
            
            # Import TradeLocker client access
            from ..core.account_manager import get_account_manager
            account_manager = get_account_manager()
            
            for trade in active_trades:
                try:
                    # Get TradeLocker client
                    tl_client = account_manager.get_client_for_account(account_key)
                    if not tl_client:
                        logger.error(f"No TradeLocker client for {account_key}")
                        continue
                    
                    # Close position on TradeLocker
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
                            market_price = await tl_client.get_market_price(trade.symbol)
                            if market_price:
                                exit_price = market_price
                            else:
                                exit_price = trade.entry_price
                        except:
                            exit_price = trade.entry_price  # Last resort fallback
                    
                    # Calculate P&L (simplified)
                    if trade.direction == 'BUY':
                        pnl = (exit_price - trade.entry_price) * trade.lot_size * 100000
                    else:
                        pnl = (trade.entry_price - exit_price) * trade.lot_size * 100000
                    
                    # Move to history
                    await self.db.close_active_trade(
                        trade_id=trade.trade_id,
                        exit_price=exit_price,
                        pnl=pnl,
                        outcome='BREACH',
                        close_reason=reason
                    )
                    
                    logger.info(f"[{account_key}] Closed trade {trade.signal_id}: P&L ${pnl:.2f}")
                    
                except Exception as e:
                    logger.error(f"Failed to close trade {trade.trade_id}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to close trades for {account_key}: {e}")
    
    async def _notify_breach(self, account_key: str, breach_type: str, message: str):
        """
        Send breach notification to GUI and WebSocket.
        
        Args:
            account_key: Account identifier
            breach_type: Type of breach (e.g., "DAILY_LOSS_BREACH", "PROFIT_LOCK_ACTIVATED")
            message: Notification message
        """
        try:
            # Log the breach
            logger.critical(f"[BREACH NOTIFICATION] {account_key}: {breach_type} - {message}")
            
            # TODO: Implement actual GUI notification system
            # For now, just log at critical level
            
            # TODO: Implement WebSocket broadcast
            # payload = {
            #     "type": "breach_notification",
            #     "account_key": account_key,
            #     "breach_type": breach_type,
            #     "message": message,
            #     "timestamp": datetime.utcnow().isoformat()
            # }
            # await websocket_manager.broadcast(payload)
            
        except Exception as e:
            logger.error(f"Failed to send breach notification: {e}")


# Global enforcer instance
_enforcer: Optional[RiskEnforcer] = None


async def get_risk_enforcer(db: DatabaseManager) -> RiskEnforcer:
    """Get the global risk enforcer instance."""
    global _enforcer
    if _enforcer is None:
        _enforcer = RiskEnforcer(db)
        await _enforcer.start_breach_monitoring()
    return _enforcer
