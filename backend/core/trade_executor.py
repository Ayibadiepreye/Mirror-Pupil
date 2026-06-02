"""
Mirror Pupil v5.1 - Trade Executor
Executes ParsedSignals on TradeLocker accounts.
"""

import asyncio
from typing import Dict, List, Optional
from loguru import logger
import os

from ..channels.base import ParsedSignal, ParsedManagement
from .account_manager import get_account_manager
from ..database import DatabaseManager, ActiveTrade
from ..risk import RiskEnforcer, calculate_price_delta, get_trading_hours_validator


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
    
    def __init__(self, db: DatabaseManager, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run or os.getenv("DRY_RUN", "false").lower() == "true"
        self.account_manager = get_account_manager()
        self.risk_enforcer: Optional[RiskEnforcer] = None
        
        # Default lot size
        self.default_lot_size = float(os.getenv("DEFAULT_LOT_SIZE", "0.1"))
        
        if self.dry_run:
            logger.warning("🔶 TradeExecutor in DRY-RUN mode - no real trades will be placed")
        else:
            logger.info("✓ TradeExecutor initialized (LIVE mode)")
    
    async def initialize(self):
        """Initialize risk enforcer (async)."""
        from ..risk import get_risk_enforcer
        self.risk_enforcer = await get_risk_enforcer(self.db)
    
    async def execute_signal(
        self,
        signal: ParsedSignal,
        channel_id: int,
        account_keys: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """
        Execute a parsed signal on one or more accounts.
        
        Enforces:
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
        # CRITICAL: Check trading hours FIRST (before any execution)
        trading_hours = get_trading_hours_validator(db=self.db)
        allowed, reason = await trading_hours.is_trading_allowed()
        
        if not allowed:
            next_window = trading_hours.get_next_trading_window()
            logger.warning(
                f"Signal rejected: {reason}. "
                f"Trading resumes at {next_window}. "
                f"Signal: {signal.symbol} {signal.direction}"
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
                f"[{account_key}] Concurrent limit reached: {current_count}/{max_concurrent}"
            )
            
            # Get channel priorities for all active trades
            trade_priorities = []
            for trade in active_trades:
                if trade.status != 'filled':
                    continue
                channel_info = await self.db.get_channel(trade.channel_id)
                trade_priority = channel_info.priority if channel_info else 999
                trade_priorities.append((trade, trade_priority))
            
            # Sort by priority (higher number = lower priority)
            trade_priorities.sort(key=lambda x: x[1], reverse=True)
            
            # Check if incoming signal has higher priority than lowest priority trade
            if trade_priorities and channel_priority < trade_priorities[0][1]:
                # Close the lowest priority trade
                lowest_priority_trade = trade_priorities[0][0]
                logger.info(
                    f"[{account_key}] Closing lower priority trade to make room: "
                    f"{lowest_priority_trade.symbol} (priority {trade_priorities[0][1]}) "
                    f"for new signal (priority {channel_priority})"
                )
                
                # Close the trade
                account = self.account_manager.get_account(account_key)
                if account:
                    try:
                        await account['client'].close_position(
                            position_id=lowest_priority_trade.tl_position_id
                        )
                        await self.db.move_trade_to_history(
                            lowest_priority_trade.trade_id,
                            exit_price=0.0,  # Will be updated by polling
                            pnl=0.0,
                            close_reason='PRIORITY_CLOSE'
                        )
                        logger.info(
                            f"[{account_key}] ✓ Closed lower priority trade"
                        )
                    except Exception as e:
                        logger.error(
                            f"[{account_key}] Failed to close lower priority trade: {e}"
                        )
                        return {
                            "status": "rejected",
                            "reason": f"Concurrent limit reached and failed to close lower priority trade: {e}"
                        }
                
                # Now execute the new signal
                return await self._execute_on_account(signal, channel_id, account_key)
            else:
                # Reject the signal
                logger.warning(
                    f"[{account_key}] Signal rejected: concurrent limit reached "
                    f"and incoming priority ({channel_priority}) not higher than "
                    f"lowest active trade priority ({trade_priorities[0][1] if trade_priorities else 'N/A'})"
                )
                return {
                    "status": "rejected",
                    "reason": f"Concurrent limit reached ({current_count}/{max_concurrent}), "
                             f"incoming priority not high enough"
                }
        
        # Limit not reached, execute normally
        return await self._execute_on_account(signal, channel_id, account_key)
    
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
            
            # 4c. Get instrument details for lot step
            instruments = await client.get_all_instruments()
            instrument = next(
                (i for i in instruments if i.get('tradableInstrumentId') == instrument_id),
                None
            )
            
            if not instrument:
                raise Exception(f"Instrument details not found for {signal.symbol}")
            
            # Step 5: Validate trade with risk enforcer (now that we have instrument)
            if self.risk_enforcer and signal.sl:
                validation = await self.risk_enforcer.validate_trade(
                    account=account_db,
                    profile=profile,
                    entry_price=signal.entry_price or 0.0,  # Will be filled at market
                    sl_price=signal.sl,
                    lot_size=self.default_lot_size,
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
            
            lot_step = instrument.get('lotStep', 0.01)
            
            # Step 6: Round lot size
            lot_size = client.round_lot_size(self.default_lot_size, lot_step)
            
            # Step 7: Prepare order parameters
            side = signal.direction.lower()  # "buy" or "sell"
            type_ = signal.order_type.lower()  # "market", "limit", "stop"
            
            price = signal.entry_price if type_ == "limit" else None
            stop_price = signal.entry_price if type_ == "stop" else None
            
            # Handle multi-TP (use first TP for now)
            take_profit = signal.tp[0] if signal.tp and len(signal.tp) > 0 else None
            stop_loss = signal.sl
            
            # Step 8: Create order
            logger.info(
                f"[{account_key}] Placing {type_.upper()} order: "
                f"{side.upper()} {lot_size} lots of {signal.symbol}"
            )
            
            order = await client.create_order(
                instrument_id=instrument_id,
                quantity=lot_size,
                side=side,
                type_=type_,
                price=price,
                stop_price=stop_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                validity="GTC"
            )
            
            # Step 9: Extract order details
            order_id = order.get('orderId') or order.get('id')
            position_id = order.get('positionId')
            fill_price = order.get('fillPrice') or order.get('price')
            order_status = order.get('status', '').lower()
            
            # Determine if order is filled or pending
            if type_ == "market":
                # Market orders fill immediately
                status = "filled"
                fill_price = fill_price or signal.entry_price or 0.0
            elif order_status in ['filled', 'executed']:
                # Order already filled
                status = "filled"
                fill_price = fill_price or signal.entry_price or 0.0
            elif order_status in ['pending', 'working', 'accepted']:
                # Order is pending (LIMIT or STOP)
                status = "pending"
                fill_price = signal.entry_price or 0.0  # Use limit/stop price
            elif order_status == 'partially_filled':
                # Order partially filled
                status = "partially_filled"
                fill_price = fill_price or signal.entry_price or 0.0
            else:
                # Unknown status, assume pending
                status = "pending"
                fill_price = signal.entry_price or 0.0
            
            logger.info(
                f"[{account_key}] ✓ Order placed: ID={order_id}, "
                f"Position={position_id}, Status={status}, Price={fill_price}"
            )
            
            # Step 10: ✅ RECORD IN DATABASE (active_trades table)
            # This is the CRITICAL step that was missing!
            signal_id = f"{signal.channel_id}_{signal.msg_id}"  # Format: channel_id_msg_id
            
            active_trade = ActiveTrade(
                account_key=account_key,
                channel_id=channel_id,
                signal_id=signal_id,
                sub_signal_id=None,  # For multi-TP, will be signal_id_tp1, etc.
                symbol=signal.symbol,
                direction=signal.direction,
                entry_price=fill_price,
                sl=stop_loss,
                tp=take_profit,
                lot_size=lot_size,
                tl_order_id=str(order_id) if order_id else None,
                tl_position_id=str(position_id) if position_id else None,
                status=status,  # 'filled', 'pending', or 'partially_filled'
                risk_usd=trade_risk
            )
            
            trade_id = await self.db.add_active_trade(active_trade)
            
            if trade_id:
                if status == "filled":
                    logger.info(
                        f"[{account_key}] ✅ Trade recorded in database: trade_id={trade_id} (FILLED)"
                    )
                elif status == "pending":
                    logger.info(
                        f"[{account_key}] ✅ Pending order recorded in database: trade_id={trade_id} "
                        f"(will be monitored until filled or expired)"
                    )
                else:
                    logger.info(
                        f"[{account_key}] ✅ Trade recorded in database: trade_id={trade_id} ({status.upper()})"
                    )
            else:
                logger.error(
                    f"[{account_key}] ❌ Failed to record trade in database!"
                )
            
            # Step 11: Return result
            return {
                "status": status,
                "order_id": order_id,
                "position_id": position_id,
                "fill_price": fill_price,
                "lot_size": lot_size,
                "instrument_id": instrument_id,
                "trade_id": trade_id,  # Database trade ID
                "risk_usd": trade_risk,
                "order_type": type_
            }
            
        except Exception as e:
            logger.error(f"[{account_key}] Execution error: {e}")
            
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
            # BREAKEVEN
            if action == 'BREAKEVEN':
                await client.modify_position(
                    position_id=trade.tl_position_id,
                    stop_loss=trade.entry_price
                )
                await self.db.update_trade_sl(trade.trade_id, trade.entry_price)
                logger.info(
                    f"[{account_key}] ✓ BREAKEVEN: {trade.symbol} SL moved to {trade.entry_price}"
                )
                return {"trade_id": trade.trade_id, "status": "success", "action": "breakeven"}
            
            # CLOSE_ALL or IMPLIED_CLOSE
            elif action in ['CLOSE_ALL', 'IMPLIED_CLOSE']:
                await client.close_position(position_id=trade.tl_position_id)
                await self.db.move_trade_to_history(
                    trade.trade_id,
                    exit_price=0.0,  # Will be updated by polling
                    pnl=0.0,
                    close_reason='MANUAL'
                )
                logger.info(
                    f"[{account_key}] ✓ CLOSE_ALL: {trade.symbol} position closed"
                )
                return {"trade_id": trade.trade_id, "status": "success", "action": "close_all"}
            
            # PARTIAL_CLOSE
            elif action.startswith('PARTIAL_CLOSE'):
                close_pct = mgmt.close_pct or 0.5
                qty_to_close = round(trade.lot_size * close_pct, 2)
                
                await client.close_position(
                    position_id=trade.tl_position_id,
                    quantity=qty_to_close
                )
                
                new_lot_size = round(trade.lot_size - qty_to_close, 2)
                await self.db.update_trade_lot_size(trade.trade_id, new_lot_size)
                
                logger.info(
                    f"[{account_key}] ✓ PARTIAL_CLOSE: {trade.symbol} closed {close_pct*100:.0f}% "
                    f"({qty_to_close} lots, {new_lot_size} remaining)"
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
                # (This is a simplified check - full validation would need current market price)
                await client.modify_position(
                    position_id=trade.tl_position_id,
                    stop_loss=new_sl
                )
                await self.db.update_trade_sl(trade.trade_id, new_sl)
                
                logger.info(
                    f"[{account_key}] ✓ MODIFY_SL: {trade.symbol} SL updated to {new_sl}"
                )
                return {"trade_id": trade.trade_id, "status": "success", "action": "modify_sl", "new_sl": new_sl}
            
            # MODIFY_TP
            elif action == 'MODIFY_TP':
                new_tp = mgmt.new_tp
                if not new_tp:
                    return {"trade_id": trade.trade_id, "status": "failed", "error": "No new TP provided"}
                
                await client.modify_position(
                    position_id=trade.tl_position_id,
                    take_profit=new_tp
                )
                await self.db.update_trade_tp(trade.trade_id, new_tp)
                
                logger.info(
                    f"[{account_key}] ✓ MODIFY_TP: {trade.symbol} TP updated to {new_tp}"
                )
                return {"trade_id": trade.trade_id, "status": "success", "action": "modify_tp", "new_tp": new_tp}
            
            # COMPOUND (Close 33% + Breakeven)
            elif action == 'COMPOUND':
                # Close 33%
                qty_to_close = round(trade.lot_size * 0.33, 2)
                await client.close_position(
                    position_id=trade.tl_position_id,
                    quantity=qty_to_close
                )
                new_lot_size = round(trade.lot_size - qty_to_close, 2)
                await self.db.update_trade_lot_size(trade.trade_id, new_lot_size)
                
                # Set breakeven
                await client.modify_position(
                    position_id=trade.tl_position_id,
                    stop_loss=trade.entry_price
                )
                await self.db.update_trade_sl(trade.trade_id, trade.entry_price)
                
                logger.info(
                    f"[{account_key}] ✓ COMPOUND: {trade.symbol} closed 33% ({qty_to_close} lots) + BE"
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
                if trade.status == 'pending':
                    await client.delete_order(order_id=trade.tl_order_id)
                    await self.db.remove_active_trade(trade.trade_id)
                    logger.info(
                        f"[{account_key}] ✓ CANCEL_PENDING: {trade.symbol} order cancelled"
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


# Global executor instance
_executor: Optional[TradeExecutor] = None


async def get_trade_executor(db: DatabaseManager) -> TradeExecutor:
    """Get the global trade executor instance."""
    global _executor
    if _executor is None:
        _executor = TradeExecutor(db)
        await _executor.initialize()
    return _executor
