"""
Mirror Pupil v5.1 - Trade Executor
Executes ParsedSignals on TradeLocker accounts.
"""

import asyncio
from typing import Dict, List, Optional, TYPE_CHECKING
from loguru import logger
import os

from ..channels.base import ParsedSignal, ParsedManagement
from .account_manager import get_account_manager
from .bot_state import get_bot_state
from ..database.models import ActiveTrade, Account, RiskProfile

if TYPE_CHECKING:
    from ..database import DatabaseManager
    from ..risk import RiskEnforcer


class TradeExecutor:
    """
    Executes parsed signals on TradeLocker accounts.
    
    Features:
    - Multi-account concurrent execution
    - Partial failure handling
    - Dry-run mode support
    - Instrument resolution
    - Lot size rounding
    """
    
    def __init__(self, db: "DatabaseManager", dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run or os.getenv("DRY_RUN", "false").lower() == "true"
        self.account_manager = get_account_manager()
        self.risk_enforcer: Optional[RiskEnforcer] = None
        self.notification_service = None  # Will be initialized later
        
        # Default lot size
        self.default_lot_size = float(os.getenv("DEFAULT_LOT_SIZE", "0.1"))
        
        if self.dry_run:
            logger.warning("🔶 TradeExecutor in DRY-RUN mode - no real trades will be placed")
        else:
            logger.info("✓ TradeExecutor initialized (LIVE mode)")
    
    async def initialize(self):
        """Initialize risk enforcer and notification service (async)."""
        from ..risk import get_risk_enforcer, get_trading_hours_validator
        from .notification_service import get_notification_service  # Lazy import to avoid circular dependency
        self.risk_enforcer = await get_risk_enforcer(self.db)
        self.notification_service = get_notification_service(self.db)
    
    async def execute_signal(
        self,
        signal: ParsedSignal,
        channel_id: int,
        account_keys: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """
        Execute a parsed signal on one or more accounts.
        
        Enforces:
        - Bot running state (no new trades if stopped)
        - Trading hours validation (weekends, EOD, pre-market)
        - Channel subscription filtering
        - Concurrent trade limits per account
        - Channel priority when limit is reached
        
        Args:
            signal: ParsedSignal from parser
            channel_id: Channel ID where signal originated
            account_keys: List of account keys to execute on (None = all subscribed accounts)
        
        Returns:
            Dict mapping account_key → execution result
        """
        # CRITICAL: Check bot state FIRST
        bot_state = get_bot_state()
        if not bot_state.is_running():
            logger.warning(
                f"Signal rejected: Bot is stopped. "
                f"Signal: {signal.symbol} {signal.direction}"
            )
            
            # Notify rejection
            if self.notification_service:
                await self.notification_service.create_notification(
                    category='SIGNAL',
                    severity='WARNING',
                    title=f'Signal Rejected: {signal.symbol}',
                    message=f'Bot is stopped - {signal.direction} signal for {signal.symbol} not executed',
                    metadata={'symbol': signal.symbol, 'direction': signal.direction, 'reason': 'bot_stopped'}
                )
            
            return {
                "status": "rejected",
                "reason": "Bot is stopped - no new trades allowed"
            }
        
        # CRITICAL: Check trading hours SECOND (before any execution)
        from ..risk import get_trading_hours_validator
        trading_hours = get_trading_hours_validator(db=self.db)
        allowed, reason = await trading_hours.is_trading_allowed()
        
        if not allowed:
            next_window = trading_hours.get_next_trading_window()
            logger.warning(
                f"Signal rejected: {reason}. "
                f"Trading resumes at {next_window}. "
                f"Signal: {signal.symbol} {signal.direction}"
            )
            
            # Notify rejection
            if self.notification_service:
                await self.notification_service.create_notification(
                    category='SIGNAL',
                    severity='INFO',
                    title=f'Signal Rejected: {signal.symbol}',
                    message=f'{reason} - {signal.direction} signal for {signal.symbol} will not execute until {next_window}',
                    metadata={'symbol': signal.symbol, 'direction': signal.direction, 'reason': reason, 'next_window': str(next_window)}
                )
            return {
                "status": "rejected",
                "reason": reason,
                "next_trading_window": next_window
            }
        
        if account_keys is None:
            # Get all accounts subscribed to this channel
            all_accounts = await self.db.get_all_accounts()
            account_keys = []
            
            for account in all_accounts:
                if account.paused or account.breached:
                    continue  # Skip paused/breached accounts
                
                # Check channel subscription
                is_subscribed = await self.db.is_channel_subscribed(account.account_key, channel_id)
                if is_subscribed:
                    account_keys.append(account.account_key)
        
        if not account_keys:
            logger.warning(f"No accounts subscribed to channel {channel_id}")
            
            # Notify no subscribers
            if self.notification_service:
                channel = await self.db.get_channel(channel_id)
                channel_name = channel.display_name if channel else f"Channel {channel_id}"
                await self.notification_service.create_notification(
                    category='SIGNAL',
                    severity='INFO',
                    title=f'Signal Skipped: {signal.symbol}',
                    message=f'No active accounts subscribed to {channel_name} for {signal.direction} {signal.symbol}',
                    metadata={'symbol': signal.symbol, 'direction': signal.direction, 'channel_id': channel_id, 'reason': 'no_subscribers'}
                )
            
            return {}
        
        # Get channel info for priority
        channel_info = await self.db.get_channel(channel_id)
        channel_priority = channel_info.priority if channel_info else 999
        
        logger.info(
            f"Executing signal on {len(account_keys)} account(s): "
            f"{signal.symbol} {signal.direction} @ {signal.entry_price or 'MARKET'} "
            f"(channel priority: {channel_priority})"
        )
        
        # Execute concurrently on all accounts (with concurrent limit check per account)
        tasks = [
            self._execute_on_account_with_limit_check(
                signal, channel_id, channel_priority, account_key
            )
            for account_key in account_keys
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dict
        result_dict = {}
        for account_key, result in zip(account_keys, results):
            if isinstance(result, Exception):
                logger.error(f"[{account_key}] Execution failed: {result}")
                result_dict[account_key] = {
                    "status": "failed",
                    "error": str(result)
                }
            else:
                result_dict[account_key] = result
        
        # Summary
        success_count = sum(1 for r in result_dict.values() if r.get("status") == "filled")
        logger.info(
            f"✓ Signal execution complete: {success_count}/{len(account_keys)} successful"
        )
        
        return result_dict
    
    async def _execute_on_account_with_limit_check(
        self,
        signal: ParsedSignal,
        channel_id: int,
        channel_priority: int,
        account_key: str
    ) -> Dict:
        """
        Execute signal on account with concurrent trade limit enforcement.
        
        If concurrent limit is reached:
        1. Get all active trades for this account
        2. Sort by channel priority (lower = higher priority)
        3. If incoming signal has higher priority than lowest priority trade:
           - Close the lowest priority trade
           - Execute the new signal
        4. Else: reject the signal
        """
        # Get account from database
        account_db = await self.db.get_account(account_key)
        if not account_db:
            raise Exception(f"Account not found in database: {account_key}")
        
        # Get concurrent trade limit (from account override or risk profile)
        if account_db.max_concurrent_trades_override:
            max_concurrent = account_db.max_concurrent_trades_override
        else:
            # Get from risk profile
            if account_db.risk_profile_id:
                profile = await self.db.get_risk_profile(account_db.risk_profile_id)
            else:
                profile = await self.db.get_default_risk_profile()
            max_concurrent = profile.max_concurrent_trades if profile else 5
        
        # Get current active trade count
        active_trades = await self.db.get_active_trades(account_key)
        current_count = len([t for t in active_trades if t.status == 'filled'])
        
        # Check if limit reached
        if current_count >= max_concurrent:
            logger.warning(
                f"[{account_key}] Concurrent limit reached: {current_count}/{max_concurrent}. "
                f"Signal rejected. Wait for existing trades to close naturally."
            )
            
            # Reject the signal - do NOT force close existing trades
            return {
                "status": "rejected",
                "reason": f"Concurrent limit reached ({current_count}/{max_concurrent}). "
                         f"Wait for existing trades to close before accepting new signals."
            }
        
        # Limit not reached, execute normally
        return await self._execute_on_account(signal, channel_id, account_key)
    
    async def _calculate_lot_size_from_risk(
        self,
        account: Account,
        profile: RiskProfile,
        entry_price: float,
        sl_price: float,
        symbol: str,
        client,
        instrument: dict
    ) -> float:
        """
        Calculate lot size based on max_risk_per_trade_pct from risk profile.
        
        Formula: lot_size = (balance * max_risk_pct) / sl_distance_usd
        
        Args:
            account: Account object
            profile: Risk profile with max_risk_per_trade_pct
            entry_price: Entry price
            sl_price: Stop loss price
            symbol: Trading symbol
            client: TradeLocker client
            instrument: Instrument details
        
        Returns:
            Calculated lot size rounded to lot_step
        """
        if not sl_price or sl_price <= 0:
            # No SL - use default lot size
            logger.warning(f"No stop loss for {symbol}, using default lot size")
            return self.default_lot_size
        
        # Account lot size override takes precedence
        if account.lot_size_override and account.lot_size_override > 0:
            logger.debug(f"Using account lot size override: {account.lot_size_override}")
            return account.lot_size_override
        
        # Calculate risk in USD per lot
        from ..risk.calculator import calculate_usd_risk
        
        try:
            risk_per_lot = await calculate_usd_risk(
                symbol=symbol,
                entry_price=entry_price,
                stop_loss=sl_price,  # Correct parameter name
                lot_size=1.0,  # Calculate for 1 lot
                client=client,
                instrument=instrument
            )
            
            if risk_per_lot <= 0:
                logger.warning(f"[{account.account_key}] Invalid risk calculation for {symbol}, using default lot size")
                logger.warning(f"[{account.account_key}] Invalid risk calculation for {symbol}, using default lot size")
                return self.default_lot_size
            
            # Calculate desired risk amount
            balance = account.current_balance or account.initial_balance
            max_risk_amount = balance * (profile.max_risk_per_trade_pct / 100.0)
            
            # Calculate lot size
            calculated_lot_size = max_risk_amount / risk_per_lot
            
            # Reject zero or invalid calculated size
            if calculated_lot_size <= 0:
                logger.error(
                    f"[{account.account_key}] INVALID CALCULATED LOT SIZE: {calculated_lot_size} "
                    f"(balance=${balance:.2f}, max_risk_pct={profile.max_risk_per_trade_pct}%, "
                    f"risk_per_lot=${risk_per_lot:.2f}) - USING DEFAULT"
                )
                return self.default_lot_size
            
            # Round to lot step
            lot_step = instrument.get('lot_step', 0.01)
            rounded_lot_size = client.round_lot_size(calculated_lot_size, lot_step)
            
            # Comprehensive debug log
            logger.info(
                f"[{account.account_key}] LOT SIZE CALCULATION: "
                f"profile_risk={profile.max_risk_per_trade_pct}%, "
                f"balance=${balance:.2f}, "
                f"risk_per_lot=${risk_per_lot:.2f}, "
                f"computed_lot={calculated_lot_size:.4f}, "
                f"rounded_lot={rounded_lot_size}, "
                f"final_qty={rounded_lot_size}"
            )
            
            return rounded_lot_size
            
        except Exception as e:
            logger.error(f"Lot size calculation failed for {symbol}: {e}, using default")
            return self.default_lot_size
    
    async def _execute_on_account(
        self,
        signal: ParsedSignal,
        channel_id: int,
        account_key: str
    ) -> Dict:
        """
        Execute signal on a single account.
        
        CRITICAL FLOW:
        1. Get account from database
        2. Get risk profile
        3. Handle re-entry parent matching (if is_reentry=True)
        4. Validate trade (risk enforcer)
        5. Place order on TradeLocker
        6. ✅ RECORD IN DATABASE (active_trades table)
        7. Return result
        
        Returns:
            Execution result dict
        """
        # Step 1: Get account from database
        account_db = await self.db.get_account(account_key)
        if not account_db:
            raise Exception(f"Account not found in database: {account_key}")
        
        # CRITICAL: Check if account is frozen due to profit cap
        if account_db.profit_cap_frozen:
            logger.warning(
                f"[{account_key}] Trade rejected: Account frozen due to profit cap breach"
            )
            return {
                "status": "rejected",
                "reason": "Account frozen due to profit cap breach. Unfreeze account to resume trading."
            }
        
        # Send signal received notification
        if self.notification_service:
            channel = await self.db.get_channel(channel_id)
            channel_name = channel.display_name if channel else f"Channel {channel_id}"
            await self.notification_service.signal_received(
                channel_name=channel_name,
                symbol=signal.symbol,
                direction=signal.direction,
                account_key=account_key
            )
        
        # Get account from AccountManager (for TradeLocker client)
        account = self.account_manager.get_account(account_key)
        if not account:
            raise Exception(f"Account not found in AccountManager: {account_key}")
        
        client = account['client']
        
        # Step 2: Get risk profile
        if account_db.risk_profile_id:
            profile = await self.db.get_risk_profile(account_db.risk_profile_id)
        else:
            profile = await self.db.get_default_risk_profile()
        
        if not profile:
            raise Exception(f"No risk profile found for {account_key}")
        
        # Step 3: Handle re-entry parent matching
        if signal.is_reentry:
            # Only for BillirichyFX (channel_id = -1001859598768)
            if channel_id == -1001859598768:
                from ..channels.billirichy.reentry_matcher import ReentryParentMatcher
                
                matcher = ReentryParentMatcher(self.db, channel_id)
                parent = await matcher.find_parent_trade(
                    reply_to_msg_id=getattr(signal, 'reply_to_msg_id', None),
                    symbol=signal.symbol,
                    direction=signal.direction,
                    entry_price=signal.entry_price,
                    account_key=account_key
                )
                
                if parent:
                    # Inherit SL/TP from parent if not specified
                    inherited_sl, inherited_tp = await matcher.inherit_from_parent(
                        parent=parent,
                        signal_sl=signal.sl,
                        signal_tp=signal.tp
                    )
                    
                    # Update signal with inherited values
                    if not signal.sl and inherited_sl:
                        signal.sl = inherited_sl
                        logger.info(f"[{account_key}] Re-entry inherited SL: {inherited_sl}")
                    
                    if not signal.tp and inherited_tp:
                        signal.tp = inherited_tp
                        logger.info(f"[{account_key}] Re-entry inherited TP: {inherited_tp}")
                else:
                    logger.warning(
                        f"[{account_key}] Re-entry signal but no parent found - "
                        f"proceeding as standalone trade"
                    )
        
        # Dry-run mode
        if self.dry_run:
            return await self._dry_run_execute(signal, channel_id, account_key, 0.0)
        
        try:
            # Step 4: Resolve instrument and prepare order
            # 4a. Resolve symbol to instrument ID
            instrument_id = await client.get_instrument_id_from_symbol_name(signal.symbol)
            if not instrument_id:
                raise Exception(f"Symbol not found: {signal.symbol}")
            
            # 4b. Validate instrument routes
            routes = await client.validate_instrument_routes(instrument_id)
            if not routes['trade']:
                raise Exception(f"Instrument {signal.symbol} does not have TRADE route")
            
            # 4c. Get instrument details using new wrapper method
            instrument = await client.get_instrument(signal.symbol)
            
            # Step 4d: Calculate lot size from risk profile BEFORE risk validation
            entry_price_for_calc = signal.entry_price
            if entry_price_for_calc is None or entry_price_for_calc == 0.0:
                # Market order - fetch current price
                current_market_price = await client.get_market_price(signal.symbol)
                if current_market_price and current_market_price > 0:
                    entry_price_for_calc = current_market_price
                    logger.info(f"[{account_key}] Market order - using current price {current_market_price:.5f}")
                else:
                    entry_price_for_calc = 0.0
                    logger.warning(f"[{account_key}] Could not fetch market price for {signal.symbol}")
            
            # Calculate lot size based on risk profile
            calculated_lot_size = await self._calculate_lot_size_from_risk(
                account=account_db,
                profile=profile,
                entry_price=entry_price_for_calc,
                sl_price=signal.sl,
                symbol=signal.symbol,
                client=client,
                instrument=instrument
            )
            
            # Step 5: Validate trade with risk enforcer (using calculated lot size)
            if self.risk_enforcer and signal.sl:
                validation = await self.risk_enforcer.validate_trade(
                    account=account_db,
                    profile=profile,
                    entry_price=entry_price_for_calc,
                    sl_price=signal.sl,
                    lot_size=calculated_lot_size,  # Use calculated lot size
                    symbol=signal.symbol,
                    client=client,  # Pass TradeLocker client for live price fetching
                    instrument=instrument
                )
                
                if not validation['allowed']:
                    logger.warning(
                        f"[{account_key}] Trade rejected by risk enforcer: {validation['reason']}"
                    )
                    return {
                        "status": "rejected",
                        "reason": validation['reason']
                    }
                
                trade_risk = validation.get('trade_risk', 0.0)
            else:
                trade_risk = 0.0  # No SL = no risk calculation
            
            # Step 6: Use calculated lot size (already rounded)
            lot_size = calculated_lot_size
            
            # Step 7: Prepare order parameters
            side = signal.direction.lower()  # "buy" or "sell"
            type_ = signal.order_type.lower()  # "market", "limit", "stop"
            
            price = signal.entry_price if type_ == "limit" else None
            stop_price = signal.entry_price if type_ == "stop" else None
            
            # Handle multi-TP (use first TP for now)
            take_profit = signal.tp[0] if signal.tp and len(signal.tp) > 0 else None
            stop_loss = signal.sl
            
            # Step 8-10: ROLLBACK-SAFE ORDER PLACEMENT + DB PERSISTENCE
            logger.info(
                f"[{account_key}] Placing {type_.upper()} order: "
                f"{side.upper()} {lot_size} lots of {signal.symbol}"
            )
            
            # Set validity based on order type
            if type_ == "market":
                validity = "IOC"  # Market orders must use IOC (Immediate or Cancel)
            else:
                validity = "GTC"  # Limit/Stop orders can use GTC (Good Till Cancel)
            
            order_id = None
            position_id = None
            status = None
            rollback_attempted = False
            
            try:
                # STEP 8: Place order on broker
                order = await client.create_order(
                    instrument_id=instrument_id,
                    quantity=lot_size,
                    side=side,
                    type_=type_,
                    price=price,
                    stop_price=stop_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    validity=validity
                )
                
                # STEP 9: Extract order details
                if isinstance(order, int):
                    order_id = order
                    position_id = None
                    fill_price = signal.entry_price or 0.0
                    order_status = 'filled' if type_ == 'market' else 'new'
                else:
                    order_id = order.get('id') or order.get('orderId')
                    position_id = order.get('positionId')
                    fill_price = order.get('avgPrice') or order.get('fillPrice') or order.get('price')
                    order_status = order.get('status', '').lower()
                
                # Determine broker outcome
                if type_ == "market":
                    status = "filled"
                    fill_price = fill_price or signal.entry_price or 0.0
                elif order_status in ['filled', 'executed']:
                    status = "filled"
                    fill_price = fill_price or signal.entry_price or 0.0
                elif order_status in ['pending', 'working', 'accepted']:
                    status = "pending"
                    fill_price = signal.entry_price or 0.0
                elif order_status == 'partially_filled':
                    status = "partially_filled"
                    fill_price = fill_price or signal.entry_price or 0.0
                else:
                    status = "pending"
                    fill_price = signal.entry_price or 0.0
                
                # For filled market orders, fetch position details if needed
                if status == "filled" and not position_id:
                    try:
                        # Try to resolve position_id for filled market orders
                        for attempt in range(5):
                            try:
                                resolved_position_id = await client.get_position_id_from_order_id(order_id)
                                if resolved_position_id:
                                    position_id = resolved_position_id
                                    break
                            except:
                                pass
                            await asyncio.sleep(0.2)
                    except:
                        pass
                
                # Always fetch actual entry price from position after execution
                if status == "filled" and position_id:
                    try:
                        all_positions = await client.get_all_positions()
                        position_info = next((p for p in all_positions if p.get('id') == position_id), None)
                        if position_info:
                            # Use avgPrice from position as the actual entry price
                            actual_entry = position_info.get('avgPrice') or position_info.get('openPrice')
                            if actual_entry:
                                fill_price = float(actual_entry)
                    except:
                        pass
                
                logger.info(
                    f"[{account_key}] ✓ Order placed: ID={order_id}, "
                    f"Position={position_id}, Status={status}, Price={fill_price}"
                )
                
                # STEP 10: CRITICAL - Persist to database WITH ROLLBACK ON FAILURE
                signal_id = f"{signal.channel_id}_{signal.msg_id}"
                
                active_trade = ActiveTrade(
                    account_key=account_key,
                    channel_id=channel_id,
                    signal_id=signal_id,
                    sub_signal_id=None,
                    symbol=signal.symbol,
                    direction=signal.direction,
                    entry_price=fill_price,
                    sl=stop_loss,
                    tp=take_profit,
                    lot_size=lot_size,
                    tl_order_id=str(order_id) if order_id else None,
                    tl_position_id=str(position_id) if position_id else None,
                    status=status,
                    risk_usd=trade_risk
                )
                
                trade_id = await self.db.add_active_trade(active_trade)
                
                if not trade_id:
                    # CRITICAL: DB WRITE FAILED - INITIATE ROLLBACK
                    rollback_attempted = True
                    logger.critical(
                        f"[{account_key}] ❌ DB WRITE FAILED for order {order_id} - "
                        f"INITIATING ROLLBACK"
                    )
                    
                    # Determine rollback action based on broker state
                    if status == "filled" and position_id:
                        # Position is filled - close it
                        try:
                            await client.close_position(int(position_id))
                            logger.warning(
                                f"[{account_key}] ✓ ROLLBACK: Closed filled position {position_id}"
                            )
                            return {
                                "status": "rolled_back",
                                "reason": "DB write failed - position closed on broker",
                                "order_id": order_id,
                                "position_id": position_id
                            }
                        except Exception as rollback_error:
                            logger.critical(
                                f"[{account_key}] ❌ ROLLBACK FAILED: Could not close position {position_id}: "
                                f"{rollback_error}. MANUAL INTERVENTION REQUIRED. "
                                f"Account={account_key}, Symbol={signal.symbol}, OrderID={order_id}, "
                                f"PositionID={position_id}"
                            )
                            return {
                                "status": "rollback_failed",
                                "reason": f"DB failed AND rollback failed: {rollback_error}",
                                "order_id": order_id,
                                "position_id": position_id,
                                "requires_manual_intervention": True
                            }
                    
                    elif status == "pending" and order_id:
                        # Order is pending - cancel it
                        try:
                            await client.delete_order(order_id=order_id)
                            logger.warning(
                                f"[{account_key}] ✓ ROLLBACK: Cancelled pending order {order_id}"
                            )
                            return {
                                "status": "rolled_back",
                                "reason": "DB write failed - pending order cancelled",
                                "order_id": order_id
                            }
                        except Exception as rollback_error:
                            logger.critical(
                                f"[{account_key}] ❌ ROLLBACK FAILED: Could not cancel order {order_id}: "
                                f"{rollback_error}. MANUAL INTERVENTION REQUIRED. "
                                f"Account={account_key}, Symbol={signal.symbol}, OrderID={order_id}"
                            )
                            return {
                                "status": "rollback_failed",
                                "reason": f"DB failed AND rollback failed: {rollback_error}",
                                "order_id": order_id,
                                "requires_manual_intervention": True
                            }
                    
                    elif status == "partially_filled":
                        # Partial fill - try to close position
                        logger.critical(
                            f"[{account_key}] ⚠️ PARTIAL FILL ROLLBACK: Order {order_id} partially filled. "
                            f"Attempting to close any open position."
                        )
                        if position_id:
                            try:
                                await client.close_position(int(position_id))
                                logger.warning(f"[{account_key}] ✓ ROLLBACK: Closed partially filled position")
                                return {
                                    "status": "rolled_back",
                                    "reason": "DB failed - partially filled position closed",
                                    "order_id": order_id,
                                    "position_id": position_id
                                }
                            except Exception as rollback_error:
                                logger.critical(
                                    f"[{account_key}] ❌ PARTIAL FILL ROLLBACK FAILED: {rollback_error}. "
                                    f"MANUAL INTERVENTION REQUIRED."
                                )
                                return {
                                    "status": "rollback_failed",
                                    "reason": f"Partial fill rollback failed: {rollback_error}",
                                    "requires_manual_intervention": True
                                }
                    
                    # Unknown state
                    raise Exception(f"DB write failed with unknown broker state: {status}")
                
                # SUCCESS - DB write succeeded
                logger.info(
                    f"[{account_key}] ✓ Trade recorded: ID={trade_id}, "
                    f"Signal={signal_id}, Status={status}"
                )
                
                # Send notification for trade execution
                if self.notification_service and status == "filled":
                    # Get channel name
                    channel = await self.db.get_channel(channel_id)
                    channel_name = channel.display_name if channel else f"Channel {channel_id}"
                    
                    await self.notification_service.trade_executed(
                        account_key=account_key,
                        symbol=signal.symbol,
                        direction=signal.direction,
                        lot_size=lot_size,
                        entry_price=fill_price,
                        channel_name=channel_name
                    )
                
                # If position_id is None for a FILLED market order, fetch it from TradeLocker
                if position_id is None and status == "filled" and type_ == "market":
                    try:
                        logger.debug(f"[{account_key}] Resolving position_id for order {order_id}")
                        
                        # PRIMARY METHOD: Use SDK's built-in order→position lookup
                        for attempt in range(10):
                            try:
                                position_id = await client.get_position_id_from_order_id(order_id)
                                
                                if position_id is not None:
                                    await self.db.update_trade_position_id(trade_id, str(position_id))
                                    logger.info(
                                        f"[{account_key}] ✓ Resolved position_id {position_id} "
                                        f"for order {order_id} (attempt {attempt + 1})"
                                    )
                                    break
                            except Exception as e:
                                logger.warning(
                                    f"[{account_key}] Order→position lookup attempt {attempt + 1} failed: {e}"
                                )
                                position_id = None
                            
                            if position_id is not None:
                                break
                            
                            await asyncio.sleep(0.5)
                        
                        # FALLBACK METHOD: Scan positions if primary failed
                        if position_id is None:
                            logger.warning(f"[{account_key}] Primary lookup failed, falling back to position scan")
                            
                            positions = await client.get_all_positions()
                            active_trades_list = await self.db.get_active_trades(account_key)
                            existing_ids = {
                                str(t.tl_position_id) 
                                for t in active_trades_list 
                                if t.tl_position_id and t.trade_id != trade_id
                            }
                            
                            candidates = [
                                p for p in positions
                                if p.get('tradableInstrumentId') == instrument_id
                                and str(p.get('id')) not in existing_ids
                                and p.get('side', '').lower() == side.lower()
                            ]
                            
                            if len(candidates) == 1:
                                position_id = candidates[0].get('id')
                                await self.db.update_trade_position_id(trade_id, str(position_id))
                                logger.info(f"[{account_key}] ✓ Matched position_id {position_id} by instrument+side")
                            elif len(candidates) > 1:
                                logger.error(
                                    f"[{account_key}] ❌ CRITICAL: Cannot resolve position_id for order {order_id}. "
                                    f"Found {len(candidates)} candidates. Trade ID: {trade_id}"
                                )
                            else:
                                logger.error(f"[{account_key}] ❌ No position found for order {order_id}. Trade ID: {trade_id}")
                                
                    except Exception as e:
                        logger.error(f"[{account_key}] Position resolution failed for trade {trade_id}: {e}")
                
                # Step 11: Return result
                return {
                    "status": status,
                    "order_id": order_id,
                    "position_id": position_id,
                    "fill_price": fill_price,
                    "lot_size": lot_size,
                    "instrument_id": instrument_id,
                    "trade_id": trade_id,
                    "risk_usd": trade_risk,
                    "order_type": type_
                }
            
            except Exception as inner_e:
                # Inner try block exception (order placement or DB write)
                logger.error(f"[{account_key}] Order execution error: {inner_e}")
                if rollback_attempted:
                    logger.critical(f"[{account_key}] Exception during rollback: {inner_e}")
                    return {
                        "status": "rollback_failed",
                        "reason": str(inner_e),
                        "order_id": order_id,
                        "position_id": position_id,
                        "requires_manual_intervention": True
                    }
                raise
            
        except Exception as e:
            logger.error(f"[{account_key}] Execution error: {e}")
            
            # If rollback was attempted and this exception is from rollback, mark appropriately
            if rollback_attempted:
                logger.critical(
                    f"[{account_key}] Exception during rollback attempt: {e}. "
                    f"OrderID={order_id}, PositionID={position_id}, Status={status}"
                )
                return {
                    "status": "rollback_failed",
                    "reason": str(e),
                    "order_id": order_id,
                    "position_id": position_id,
                    "requires_manual_intervention": True
                }
            
            # Normal execution failure (order placement failed)
            # Record failed trade in database
            signal_id = f"{signal.channel_id}_{signal.msg_id}"
            
            failed_trade = ActiveTrade(
                account_key=account_key,
                channel_id=channel_id,
                signal_id=signal_id,
                symbol=signal.symbol,
                direction=signal.direction,
                entry_price=signal.entry_price or 0.0,
                sl=signal.sl,
                tp=signal.tp[0] if signal.tp else None,
                lot_size=self.default_lot_size,
                status="failed",
                risk_usd=trade_risk
            )
            
            await self.db.add_active_trade(failed_trade)
            
            raise
    
    async def _dry_run_execute(
        self,
        signal: ParsedSignal,
        channel_id: int,
        account_key: str,
        trade_risk: float
    ) -> Dict:
        """Simulate execution in dry-run mode."""
        logger.info(
            f"[{account_key}] 🔶 DRY-RUN: Would place {signal.order_type} order: "
            f"{signal.direction} {self.default_lot_size} lots of {signal.symbol} "
            f"@ {signal.entry_price or 'MARKET'} SL={signal.sl} TP={signal.tp} Risk=${trade_risk:.2f}"
        )
        
        # Simulate delay
        await asyncio.sleep(0.1)
        
        # Record in database even in dry-run mode
        signal_id = f"{signal.channel_id}_{signal.msg_id}"
        fill_price = signal.entry_price or 2650.0  # Mock price
        
        active_trade = ActiveTrade(
            account_key=account_key,
            channel_id=channel_id,
            signal_id=signal_id,
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=fill_price,
            sl=signal.sl,
            tp=signal.tp[0] if signal.tp else None,
            lot_size=self.default_lot_size,
            tl_order_id=f"DRY-{signal.msg_id}",
            tl_position_id=f"DRY-POS-{signal.msg_id}",
            status="filled",
            risk_usd=trade_risk
        )
        
        trade_id = await self.db.add_active_trade(active_trade)
        
        return {
            "status": "filled",
            "order_id": f"DRY-{signal.msg_id}",
            "position_id": f"DRY-POS-{signal.msg_id}",
            "fill_price": fill_price,
            "lot_size": self.default_lot_size,
            "instrument_id": 999,
            "trade_id": trade_id,
            "risk_usd": trade_risk,
            "dry_run": True
        }
    
    async def execute_management(
        self,
        mgmt: ParsedManagement,
        account_keys: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """
        Execute a management action on one or more accounts.
        
        Args:
            mgmt: ParsedManagement from parser
            account_keys: List of account keys (None = all accounts)
        
        Returns:
            Dict mapping account_key → execution result
        """
        if account_keys is None:
            account_keys = [acct['account_key'] for acct in self.account_manager.get_all_accounts()]
        
        if not account_keys:
            logger.warning("No accounts to execute management on")
            return {}
        
        logger.info(
            f"Executing management action on {len(account_keys)} account(s): "
            f"{mgmt.action}"
        )
        
        # Execute concurrently
        tasks = [
            self._execute_management_on_account(mgmt, account_key)
            for account_key in account_keys
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dict
        result_dict = {}
        for account_key, result in zip(account_keys, results):
            if isinstance(result, Exception):
                logger.error(f"[{account_key}] Management failed: {result}")
                result_dict[account_key] = {
                    "status": "failed",
                    "error": str(result)
                }
            else:
                result_dict[account_key] = result
        
        success_count = sum(1 for r in result_dict.values() if r.get("status") == "success")
        logger.info(
            f"✓ Management execution complete: {success_count}/{len(account_keys)} successful"
        )
        
        return result_dict
    
    async def _execute_management_on_account(
        self,
        mgmt: ParsedManagement,
        account_key: str
    ) -> Dict:
        """
        Execute management action on a single account.
        
        Uses context matching to find target trades, then applies the action.
        """
        account = self.account_manager.get_account(account_key)
        if not account:
            raise Exception(f"Account not found: {account_key}")
        
        client = account['client']
        
        # Dry-run mode
        if self.dry_run:
            logger.info(
                f"[{account_key}] 🔶 DRY-RUN: Would execute {mgmt.action}"
            )
            await asyncio.sleep(0.1)
            return {"status": "success", "action": mgmt.action, "dry_run": True}
        
        # Step 1: Use context matching to find target trades
        from ..channels.billirichy.context_matcher import BillirichyContextMatcher
        from ..channels.firepips.context_matcher import FirepipsContextMatcher
        
        # Determine which context matcher to use based on channel_id
        # BillirichyFX: -1001859598768, Firepips: -1001182913499
        if mgmt.channel_id == -1001859598768:
            matcher = BillirichyContextMatcher(self.db, mgmt.channel_id)
        elif mgmt.channel_id == -1001182913499:
            matcher = FirepipsContextMatcher(self.db, mgmt.channel_id)
        else:
            # Generic matcher (use Billirichy logic as default)
            matcher = BillirichyContextMatcher(self.db, mgmt.channel_id)
        
        # Match trades
        target_trades = await matcher.match_trades(
            reply_to_msg_id=mgmt.reply_to_msg_id,
            symbol=mgmt.symbol,
            direction=mgmt.direction,
            text=mgmt.raw_text,
            account_key=account_key,
            action=mgmt.action,  # Pass action for Firepips Level 9 validation
            client=client  # Pass TradeLocker client for live price fetching
        )
        
        if not target_trades:
            logger.warning(
                f"[{account_key}] No trades matched for {mgmt.action} "
                f"(symbol={mgmt.symbol}, direction={mgmt.direction})"
            )
            
            # Notify management failure
            if self.notification_service:
                await self.notification_service.create_notification(
                    category='MANAGEMENT',
                    severity='WARNING',
                    title=f'Management Failed: {mgmt.action}',
                    message=f'No trades matched for {mgmt.action} on {mgmt.symbol or "any symbol"} ({account_key.split(":")[0]})',
                    account_key=account_key,
                    metadata={'action': mgmt.action, 'symbol': mgmt.symbol, 'direction': mgmt.direction, 'reason': 'no_match'}
                )
            
            return {
                "status": "no_match",
                "action": mgmt.action,
                "reason": "No trades matched context"
            }
        
        logger.info(
            f"[{account_key}] Executing {mgmt.action} on {len(target_trades)} trade(s)"
        )
        
        # Step 2: Execute action on matched trades
        results = []
        for trade in target_trades:
            try:
                result = await self._apply_management_action(
                    mgmt, trade, client, account_key
                )
                results.append(result)
            except Exception as e:
                logger.error(
                    f"[{account_key}] Failed to apply {mgmt.action} to trade {trade.trade_id}: {e}"
                )
                results.append({"trade_id": trade.trade_id, "status": "failed", "error": str(e)})
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        
        return {
            "status": "success" if success_count > 0 else "failed",
            "action": mgmt.action,
            "trades_affected": len(target_trades),
            "trades_success": success_count,
            "results": results
        }
    
    async def _apply_management_action(
        self,
        mgmt: ParsedManagement,
        trade: 'ActiveTrade',
        client,
        account_key: str
    ) -> Dict:
        """
        Apply a specific management action to a trade.
        
        Supported actions:
        - BREAKEVEN: Move SL to entry price
        - CLOSE_ALL: Close full position
        - PARTIAL_CLOSE_XX: Close percentage of position
        - MODIFY_SL: Update stop loss
        - MODIFY_TP: Update take profit
        - COMPOUND: Close 33% + set breakeven
        - TP1_HIT, TP2_HIT, TP3_HIT: Mark TP hit (informational)
        - SL_HIT: Mark SL hit (informational)
        - IMPLIED_CLOSE: Close all (Firepips)
        - CANCEL_PENDING: Cancel pending order
        """
        action = mgmt.action
        
        try:
            # CRITICAL: Validate position_id exists before attempting operations
            if not trade.tl_position_id:
                logger.error(
                    f"[{account_key}] Cannot execute {action} on {trade.signal_id}: "
                    f"position_id not resolved. Trade ID: {trade.trade_id}"
                )
                return {
                    "trade_id": trade.trade_id,
                    "status": "failed",
                    "error": "position_id not resolved",
                    "action": action
                }
            
            # Verify position still exists on TradeLocker (skip for CANCEL_PENDING)
            if action != 'CANCEL_PENDING':
                try:
                    all_positions = await client.get_all_positions()
                    position_exists = any(
                        p.get('id') == int(trade.tl_position_id) for p in all_positions
                    )
                    
                    if not position_exists:
                        logger.error(
                            f"[{account_key}] Position {trade.tl_position_id} no longer exists on TradeLocker. "
                            f"Trade: {trade.symbol} {trade.direction}. Moving to history as EXTERNAL close."
                        )
                        
                        # Mark as closed externally
                        try:
                            market_price = await client.get_market_price(trade.symbol)
                            exit_price = market_price if market_price else trade.entry_price
                        except Exception:
                            exit_price = trade.entry_price
                        
                        await self.db.move_trade_to_history(
                            trade.trade_id,
                            exit_price=exit_price,
                            pnl=0.0,
                            close_reason='EXTERNAL'
                        )
                        
                        return {
                            "trade_id": trade.trade_id,
                            "status": "failed",
                            "error": "position_closed_externally",
                            "action": action
                        }
                except Exception as e:
                    logger.warning(
                        f"[{account_key}] Could not verify position existence: {e}. Proceeding anyway."
                    )
            
            # BREAKEVEN
            if action == 'BREAKEVEN':
                await client.modify_position(
                    position_id=int(trade.tl_position_id),
                    stop_loss=trade.entry_price
                )
                await self.db.update_trade_sl(trade.trade_id, trade.entry_price)
                logger.info(
                    f"[{account_key}] ✓ BREAKEVEN: {trade.symbol} SL moved to {trade.entry_price}"
                )
                
                # Notify management success
                if self.notification_service:
                    await self.notification_service.management_action(
                        account_key=account_key,
                        action_type='Breakeven',
                        symbol=trade.symbol,
                        details=f'Stop loss moved to entry price {trade.entry_price}'
                    )
                
                return {"trade_id": trade.trade_id, "status": "success", "action": "breakeven"}
            
            # CLOSE_ALL or IMPLIED_CLOSE
            elif action in ['CLOSE_ALL', 'IMPLIED_CLOSE']:
                # Get exit price and PnL BEFORE closing position
                try:
                    market_price = await client.get_market_price(trade.symbol)
                    exit_price = market_price if market_price else trade.entry_price
                except Exception:
                    exit_price = trade.entry_price
                
                # PRIMARY: Get unrealizedPl from TradeLocker position BEFORE closing
                pnl = None
                try:
                    all_positions = await client.get_all_positions()
                    position = next(
                        (p for p in all_positions if str(p.get('positionId') or p.get('id')) == str(trade.tl_position_id)),
                        None
                    )
                    if position:
                        # Primary: unrealizedPl
                        pnl = position.get('unrealizedPl')
                        # Fallback: profit or pnl fields
                        if pnl is None:
                            pnl = position.get('profit') or position.get('pnl')
                        
                        if pnl is not None:
                            logger.info(f"[{account_key}] Using TradeLocker unrealizedPl: ${pnl:.2f}")
                except Exception as e:
                    logger.warning(f"[{account_key}] Failed to fetch unrealizedPl: {e}")
                
                # FALLBACK: Calculate P&L manually if unavailable
                if pnl is None:
                    logger.warning(f"[{account_key}] unrealizedPl not available, calculating manually")
                    try:
                        instruments = await client.get_all_instruments()
                        instrument = next(
                            (i for i in instruments if trade.symbol in i.get('name', '')),
                            None
                        )
                        
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
                        logger.error(f"Failed to calculate USD P&L, using fallback: {e}")
                        logger.critical(
                            f"[{account_key}] CRITICAL: P&L calculation failed for {trade.symbol}. "
                            f"Recording as $0.00. Manual review required. Trade ID: {trade.trade_id}"
                        )
                        pnl = 0.0
                
                # Close position on TradeLocker AFTER getting PnL
                await client.close_position(position_id=int(trade.tl_position_id))
                
                await self.db.move_trade_to_history(
                    trade.trade_id,
                    exit_price=exit_price,
                    pnl=pnl,
                    close_reason='MANUAL'
                )
                logger.info(
                    f"[{account_key}] ✓ CLOSE_ALL: {trade.symbol} position closed (P&L: ${pnl:.2f})"
                )
                
                # Notify management success
                if self.notification_service:
                    await self.notification_service.management_action(
                        account_key=account_key,
                        action_type='Close All',
                        symbol=trade.symbol,
                        details=f'Position closed at {exit_price:.5f}, P&L: ${pnl:.2f}'
                    )
                
                return {"trade_id": trade.trade_id, "status": "success", "action": "close_all"}
            
            # PARTIAL_CLOSE
            elif action.startswith('PARTIAL_CLOSE'):
                close_pct = mgmt.close_pct or 0.5
                qty_to_close = round(trade.lot_size * close_pct, 2)
                
                await client.close_position(
                    position_id=int(trade.tl_position_id),
                    quantity=qty_to_close
                )
                
                new_lot_size = trade.lot_size - qty_to_close
                await self.db.update_trade_lot_size(trade.trade_id, new_lot_size)
                
                logger.info(
                    f"[{account_key}] ✓ PARTIAL_CLOSE: {trade.symbol} closed {close_pct*100:.0f}% "
                    f"({qty_to_close} lots, {new_lot_size} remaining)"
                )
                
                # Notify management success
                if self.notification_service:
                    await self.notification_service.management_action(
                        account_key=account_key,
                        action_type='Partial Close',
                        symbol=trade.symbol,
                        details=f'Closed {close_pct*100:.0f}% ({qty_to_close} lots), {new_lot_size} lots remaining'
                    )
                
                return {
                    "trade_id": trade.trade_id,
                    "status": "success",
                    "action": "partial_close",
                    "pct": close_pct,
                    "qty_closed": qty_to_close
                }
            
            # MODIFY_SL
            elif action == 'MODIFY_SL':
                new_sl = mgmt.new_sl
                if not new_sl:
                    return {"trade_id": trade.trade_id, "status": "failed", "error": "No new SL provided"}
                
                # Validation: SL must be on correct side of market
                try:
                    market_price = await client.get_market_price(trade.symbol)
                    if market_price:
                        if trade.direction == 'BUY' and new_sl >= market_price:
                            logger.error(
                                f"[{account_key}] Invalid SL for BUY: {new_sl} >= market {market_price}"
                            )
                            return {
                                "trade_id": trade.trade_id,
                                "status": "failed",
                                "error": f"Invalid SL for BUY: {new_sl} must be below market {market_price}"
                            }
                        elif trade.direction == 'SELL' and new_sl <= market_price:
                            logger.error(
                                f"[{account_key}] Invalid SL for SELL: {new_sl} <= market {market_price}"
                            )
                            return {
                                "trade_id": trade.trade_id,
                                "status": "failed",
                                "error": f"Invalid SL for SELL: {new_sl} must be above market {market_price}"
                            }
                except Exception as e:
                    logger.warning(f"[{account_key}] Could not validate SL direction: {e}")
                
                await client.modify_position(
                    position_id=int(trade.tl_position_id),
                    stop_loss=new_sl
                )
                await self.db.update_trade_sl(trade.trade_id, new_sl)
                
                logger.info(
                    f"[{account_key}] ✓ MODIFY_SL: {trade.symbol} SL updated to {new_sl}"
                )
                
                # Notify management success
                if self.notification_service:
                    await self.notification_service.management_action(
                        account_key=account_key,
                        action_type='Modify Stop Loss',
                        symbol=trade.symbol,
                        details=f'Stop loss updated to {new_sl}'
                    )
                
                return {"trade_id": trade.trade_id, "status": "success", "action": "modify_sl", "new_sl": new_sl}
            
            # MODIFY_TP
            elif action == 'MODIFY_TP':
                new_tp = mgmt.new_tp
                if not new_tp:
                    return {"trade_id": trade.trade_id, "status": "failed", "error": "No new TP provided"}
                
                # Validation: TP must be on correct side of market
                try:
                    market_price = await client.get_market_price(trade.symbol)
                    if market_price:
                        if trade.direction == 'BUY' and new_tp <= market_price:
                            logger.error(
                                f"[{account_key}] Invalid TP for BUY: {new_tp} <= market {market_price}"
                            )
                            return {
                                "trade_id": trade.trade_id,
                                "status": "failed",
                                "error": f"Invalid TP for BUY: {new_tp} must be above market {market_price}"
                            }
                        elif trade.direction == 'SELL' and new_tp >= market_price:
                            logger.error(
                                f"[{account_key}] Invalid TP for SELL: {new_tp} >= market {market_price}"
                            )
                            return {
                                "trade_id": trade.trade_id,
                                "status": "failed",
                                "error": f"Invalid TP for SELL: {new_tp} must be below market {market_price}"
                            }
                except Exception as e:
                    logger.warning(f"[{account_key}] Could not validate TP direction: {e}")
                
                await client.modify_position(
                    position_id=int(trade.tl_position_id),
                    take_profit=new_tp
                )
                await self.db.update_trade_tp(trade.trade_id, new_tp)
                
                logger.info(
                    f"[{account_key}] ✓ MODIFY_TP: {trade.symbol} TP updated to {new_tp}"
                )
                
                # Notify management success
                if self.notification_service:
                    await self.notification_service.management_action(
                        account_key=account_key,
                        action_type='Modify Take Profit',
                        symbol=trade.symbol,
                        details=f'Take profit updated to {new_tp}'
                    )
                
                return {"trade_id": trade.trade_id, "status": "success", "action": "modify_tp", "new_tp": new_tp}
            
            # COMPOUND (Close 50% + Breakeven)
            elif action == 'COMPOUND':
                # Close 50%
                qty_to_close = round(trade.lot_size * 0.50, 2)
                await client.close_position(
                    position_id=int(trade.tl_position_id),
                    quantity=qty_to_close
                )
                new_lot_size = trade.lot_size - qty_to_close
                await self.db.update_trade_lot_size(trade.trade_id, new_lot_size)
                
                # Set breakeven
                await client.modify_position(
                    position_id=int(trade.tl_position_id),
                    stop_loss=trade.entry_price
                )
                await self.db.update_trade_sl(trade.trade_id, trade.entry_price)
                
                logger.info(
                    f"[{account_key}] ✓ COMPOUND: {trade.symbol} closed 50% ({qty_to_close} lots) + BE"
                )
                
                # Notify management success
                if self.notification_service:
                    await self.notification_service.management_action(
                        account_key=account_key,
                        action_type='Compound',
                        symbol=trade.symbol,
                        details=f'Closed 50% ({qty_to_close} lots) and moved to breakeven'
                    )
                return {
                    "trade_id": trade.trade_id,
                    "status": "success",
                    "action": "compound",
                    "qty_closed": qty_to_close
                }
            
            # TP1_HIT, TP2_HIT, TP3_HIT (informational - mark for trailing stop)
            elif action in ['TP1_HIT', 'TP2_HIT', 'TP3_HIT']:
                if action == 'TP1_HIT':
                    await self.db.mark_tp1_hit(trade.trade_id)
                    logger.info(
                        f"[{account_key}] ✓ TP1_HIT: {trade.symbol} marked for trailing stop"
                    )
                    
                    # Notify TP1 hit
                    if self.notification_service:
                        await self.notification_service.management_action(
                            account_key=account_key,
                            action_type='TP1 Hit',
                            symbol=trade.symbol,
                            details=f'First take profit hit - trailing stop activated'
                        )
                else:
                    logger.info(
                        f"[{account_key}] ℹ {action}: {trade.symbol} (informational)"
                    )
                return {"trade_id": trade.trade_id, "status": "success", "action": action.lower()}
            
            # SL_HIT (informational)
            elif action == 'SL_HIT':
                logger.info(
                    f"[{account_key}] ℹ SL_HIT: {trade.symbol} (informational)"
                )
                return {"trade_id": trade.trade_id, "status": "success", "action": "sl_hit"}
            
            # CANCEL_PENDING
            elif action == 'CANCEL_PENDING':
                if trade.status in ['new', 'pending']:  # TradeLocker uses 'new' for pending orders
                    if not trade.tl_order_id:
                        logger.error(
                            f"[{account_key}] Cannot cancel order for {trade.symbol}: "
                            f"order_id not resolved. Trade ID: {trade.trade_id}"
                        )
                        return {
                            "trade_id": trade.trade_id,
                            "status": "failed",
                            "error": "order_id not resolved"
                        }
                    
                    await client.delete_order(order_id=trade.tl_order_id)
                    await self.db.remove_active_trade(trade.trade_id)
                    logger.info(
                        f"[{account_key}] ✓ CANCEL_PENDING: {trade.symbol} order cancelled"
                    )
                    
                    # Notify cancel success
                    if self.notification_service:
                        await self.notification_service.management_action(
                            account_key=account_key,
                            action_type='Cancel Pending',
                            symbol=trade.symbol,
                            details=f'Pending order cancelled'
                        )
                    
                    return {"trade_id": trade.trade_id, "status": "success", "action": "cancel_pending"}
                else:
                    logger.warning(
                        f"[{account_key}] Cannot cancel non-pending trade: {trade.symbol} (status={trade.status})"
                    )
                    return {"trade_id": trade.trade_id, "status": "skipped", "reason": "not_pending"}
            
            # Unknown action
            else:
                logger.warning(f"[{account_key}] Unknown action: {action}")
                return {"trade_id": trade.trade_id, "status": "failed", "error": f"Unknown action: {action}"}
        
        except Exception as e:
            logger.error(f"[{account_key}] Error applying {action} to trade {trade.trade_id}: {e}")
            raise
    
    # ==================== MANUAL ACTION METHODS ====================
    
    async def execute_manual_close(self, trade_id: int, account_key: str, reason: str = "Manual close") -> bool:
        """
        Manually close a trade from the GUI.
        
        Args:
            trade_id: Database trade ID
            account_key: Account key
            reason: Close reason
        
        Returns:
            True if successful
        """
        try:
            # Get trade from database
            trade = await self.db.get_active_trade_by_id(trade_id)
            if not trade:
                logger.error(f"Trade {trade_id} not found")
                return False
            
            # Get TradeLocker client
            account = self.account_manager.get_account(account_key)
            if not account:
                logger.error(f"Account {account_key} not found")
                return False
            
            client = account['client']
            
            # PRIMARY: Use last saved current_pnl from database (updated every 15 seconds)
            # This is the most accurate as it's TradeLocker's actual unrealizedPl
            pnl = trade.current_pnl
            
            if pnl is not None:
                logger.info(f"[{account_key}] Using saved current_pnl from database: ${pnl:.2f}")
            else:
                # FALLBACK: Fetch unrealizedPl from TradeLocker position in real-time
                logger.warning(f"[{account_key}] No saved PnL, fetching from TradeLocker...")
                if trade.tl_position_id:
                    try:
                        all_positions = await client.get_all_positions()
                        position = next(
                            (p for p in all_positions if str(p.get('positionId') or p.get('id')) == str(trade.tl_position_id)),
                            None
                        )
                        if position:
                            # Primary: unrealizedPl
                            pnl = position.get('unrealizedPl')
                            # Fallback: profit or pnl fields
                            if pnl is None:
                                pnl = position.get('profit') or position.get('pnl')
                            
                            if pnl is not None:
                                logger.info(f"[{account_key}] Fetched TradeLocker unrealizedPl: ${pnl:.2f}")
                    except Exception as e:
                        logger.warning(f"[{account_key}] Failed to fetch unrealizedPl: {e}")
                
                # LAST RESORT: Use 0.0 if still unavailable (better than wrong calculation)
                if pnl is None:
                    logger.error(f"[{account_key}] Could not determine PnL, using 0.0")
                    pnl = 0.0
            
            # Get exit price for history record
            market_price = await client.get_market_price(trade.symbol)
            exit_price = market_price if market_price else trade.entry_price
            
            # Close position on TradeLocker AFTER getting PnL
            if trade.tl_position_id:
                success = await client.close_position(int(trade.tl_position_id))
                if not success:
                    logger.error(f"Failed to close position {trade.tl_position_id}")
                    return False
            
            # Move to history with manual action type
            await self.db.move_trade_to_history(
                trade_id=trade_id,
                exit_price=exit_price,
                pnl=pnl,
                outcome="WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BE",
                close_reason="MANUAL_CLOSE",
                manual_action_type="MANUAL_CLOSE"
            )
            
            # Send notification
            if self.notification_service:
                await self.notification_service.trade_closed(
                    account_key=account_key,
                    symbol=trade.symbol,
                    pnl=pnl,
                    close_reason="MANUAL_CLOSE"
                )
            
            logger.info(f"✓ Manually closed trade {trade_id}: {trade.symbol} P&L=${pnl:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to manually close trade {trade_id}: {e}")
            return False
    
    async def execute_manual_breakeven(self, trade_id: int, account_key: str) -> bool:
        """
        Set trade SL to breakeven (entry price).
        
        Args:
            trade_id: Database trade ID
            account_key: Account key
        
        Returns:
            True if successful
        """
        try:
            # Get trade from database
            trade = await self.db.get_active_trade_by_id(trade_id)
            if not trade:
                logger.error(f"Trade {trade_id} not found")
                return False
            
            # Get TradeLocker client
            account = self.account_manager.get_account(account_key)
            if not account:
                logger.error(f"Account {account_key} not found")
                return False
            
            client = account['client']
            
            # Set SL to entry price
            new_sl = trade.entry_price
            
            if trade.tl_position_id:
                success = await client.modify_position(
                    int(trade.tl_position_id),
                    stop_loss=new_sl
                )
                if not success:
                    logger.error(f"Failed to modify position {trade.tl_position_id}")
                    return False
            
            # Update database
            await self.db.update_trade_sl(trade_id, new_sl)
            
            # Send notification
            if self.notification_service:
                await self.notification_service.management_action(
                    account_key=account_key,
                    action_type="BREAKEVEN",
                    symbol=trade.symbol,
                    details=f"SL set to breakeven: {new_sl}"
                )
            
            logger.info(f"✓ Set trade {trade_id} to breakeven: SL={new_sl}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set breakeven for trade {trade_id}: {e}")
            return False
    
    async def execute_manual_partial(self, trade_id: int, account_key: str, percentage: int) -> bool:
        """
        Take partial profit on a trade.
        
        Args:
            trade_id: Database trade ID
            account_key: Account key
            percentage: Percentage to close (25, 50, or 75)
        
        Returns:
            True if successful
        """
        try:
            # Get trade from database
            trade = await self.db.get_active_trade_by_id(trade_id)
            if not trade:
                logger.error(f"Trade {trade_id} not found")
                return False
            
            # Get TradeLocker client
            account = self.account_manager.get_account(account_key)
            if not account:
                logger.error(f"Account {account_key} not found")
                return False
            
            client = account['client']
            
            # Calculate partial close amount
            close_lots = (trade.lot_size * percentage) / 100.0
            
            # Get instrument for lot rounding
            instrument = await client.get_instrument(trade.symbol)
            lot_step = instrument.get('lot_step', 0.01)
            close_lots = client.round_lot_size(close_lots, lot_step)
            
            # Partial close on TradeLocker
            if trade.tl_position_id:
                success = await client.close_position(
                    int(trade.tl_position_id),
                    quantity=close_lots
                )
                if not success:
                    logger.error(f"Failed to partial close position {trade.tl_position_id}")
                    return False
            
            # Update lot size in database
            remaining_lots = trade.lot_size - close_lots
            await self.db.update_trade_lot_size(trade_id, remaining_lots)
            
            # Send notification
            if self.notification_service:
                await self.notification_service.management_action(
                    account_key=account_key,
                    action_type=f"PARTIAL_{percentage}%",
                    symbol=trade.symbol,
                    details=f"Closed {close_lots} lots ({percentage}%), {remaining_lots} lots remaining"
                )
            
            logger.info(
                f"✓ Partial close {percentage}% on trade {trade_id}: "
                f"closed {close_lots} lots, {remaining_lots} remaining"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to take partial profit on trade {trade_id}: {e}")
            return False


# Global executor instance
_executor: Optional[TradeExecutor] = None


async def get_trade_executor(db: "DatabaseManager") -> TradeExecutor:
    """Get the global trade executor instance."""
    global _executor
    if _executor is None:
        _executor = TradeExecutor(db)
        await _executor.initialize()
    return _executor
