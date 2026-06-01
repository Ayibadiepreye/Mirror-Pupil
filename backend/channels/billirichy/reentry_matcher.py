"""
BillirichyFX - Re-Entry Parent Matcher
Implements Section 3.4: 7-Level Parent Matching for Re-Entries
"""

from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

from ...database import DatabaseManager, ActiveTrade


class ReentryParentMatcher:
    """
    7-Level parent matching for BillirichyFX re-entry signals.
    
    Levels (applied in order, stop at first match):
    1. Direct reply to a trade message ID
    2. Exactly one open trade exists
    3. Symbol + direction both match
    4. Symbol matches (direction ambiguous)
    5. Direction matches (symbol ambiguous)
    6. Price decimal places match
    7. No match → skip re-entry
    """
    
    def __init__(self, db: DatabaseManager, channel_id: int):
        self.db = db
        self.channel_id = channel_id
    
    async def find_parent_trade(
        self,
        reply_to_msg_id: Optional[int],
        symbol: Optional[str],
        direction: Optional[str],
        entry_price: Optional[float],
        account_key: str
    ) -> Optional[ActiveTrade]:
        """
        Find parent trade for a re-entry signal using 7-level matching.
        
        Args:
            reply_to_msg_id: Telegram reply-to message ID
            symbol: Extracted symbol from text
            direction: Extracted direction from text
            entry_price: Entry price if specified
            account_key: Account to match trades for
        
        Returns:
            Parent ActiveTrade object or None
        """
        # Get all active trades for this account and channel
        all_trades = await self.db.get_active_trades_by_channel(
            account_key, self.channel_id
        )
        
        if not all_trades:
            logger.debug(f"[ReEntry] No active trades for {account_key}")
            return None
        
        # Level 1: Direct reply to a trade message ID
        if reply_to_msg_id:
            matches = [t for t in all_trades if t.signal_id.endswith(f"_{reply_to_msg_id}")]
            if matches:
                parent = matches[0]  # Take first if multiple
                logger.info(
                    f"[ReEntry L1] Matched parent by reply-to msg_id={reply_to_msg_id}: "
                    f"{parent.symbol} {parent.direction}"
                )
                return parent
        
        # Level 2: Exactly one open trade exists
        if len(all_trades) == 1:
            parent = all_trades[0]
            logger.info(
                f"[ReEntry L2] Matched sole parent trade: {parent.symbol} {parent.direction}"
            )
            return parent
        
        # Level 3: Symbol + direction both match
        if symbol and direction:
            matches = [
                t for t in all_trades
                if t.symbol == symbol and t.direction == direction
            ]
            if len(matches) == 1:
                parent = matches[0]
                logger.info(
                    f"[ReEntry L3] Matched parent by symbol={symbol} direction={direction}"
                )
                return parent
            elif len(matches) > 1:
                # Multiple matches - take most recent
                parent = max(matches, key=lambda t: t.entry_time or datetime.min)
                logger.info(
                    f"[ReEntry L3] Multiple matches, taking most recent: "
                    f"{parent.symbol} {parent.direction}"
                )
                return parent
        
        # Level 4: Symbol matches (direction ambiguous)
        if symbol:
            matches = [t for t in all_trades if t.symbol == symbol]
            if len(matches) == 1:
                parent = matches[0]
                logger.info(
                    f"[ReEntry L4] Matched parent by symbol={symbol} (direction ambiguous)"
                )
                return parent
            elif len(matches) > 1:
                # Multiple matches - take most recent
                parent = max(matches, key=lambda t: t.entry_time or datetime.min)
                logger.info(
                    f"[ReEntry L4] Multiple symbol matches, taking most recent: "
                    f"{parent.symbol} {parent.direction}"
                )
                return parent
        
        # Level 5: Direction matches (symbol ambiguous)
        if direction:
            matches = [t for t in all_trades if t.direction == direction]
            if len(matches) == 1:
                parent = matches[0]
                logger.info(
                    f"[ReEntry L5] Matched parent by direction={direction} (symbol ambiguous)"
                )
                return parent
            elif len(matches) > 1:
                # Multiple matches - take most recent
                parent = max(matches, key=lambda t: t.entry_time or datetime.min)
                logger.info(
                    f"[ReEntry L5] Multiple direction matches, taking most recent: "
                    f"{parent.symbol} {parent.direction}"
                )
                return parent
        
        # Level 6: Price decimal places match
        if entry_price:
            decimal_places = self._count_decimal_places(entry_price)
            matches = [
                t for t in all_trades
                if self._count_decimal_places(t.entry_price) == decimal_places
            ]
            if len(matches) == 1:
                parent = matches[0]
                logger.info(
                    f"[ReEntry L6] Matched parent by price decimal places ({decimal_places})"
                )
                return parent
            elif len(matches) > 1:
                # Multiple matches - take most recent
                parent = max(matches, key=lambda t: t.entry_time or datetime.min)
                logger.info(
                    f"[ReEntry L6] Multiple decimal matches, taking most recent: "
                    f"{parent.symbol} {parent.direction}"
                )
                return parent
        
        # Level 7: No match
        logger.warning(
            f"[ReEntry L7] No parent found for re-entry: "
            f"symbol={symbol} direction={direction} account={account_key}"
        )
        return None
    
    def _count_decimal_places(self, price: float) -> int:
        """Count decimal places in a price."""
        price_str = f"{price:.10f}".rstrip('0').rstrip('.')
        if '.' in price_str:
            return len(price_str.split('.')[1])
        return 0
    
    async def inherit_from_parent(
        self,
        parent: ActiveTrade,
        signal_sl: Optional[float],
        signal_tp: Optional[List[float]]
    ) -> tuple[Optional[float], Optional[List[float]]]:
        """
        Inherit SL and TP from parent trade if not specified in signal.
        
        Rules:
        - SL: Use signal SL if present, else inherit parent's current SL
        - TP: Use signal TP if present, else inherit highest remaining active TP from parent
        - If parent has no active TP: auto-assign TP = entry ± 2× SL distance
        
        Args:
            parent: Parent trade
            signal_sl: SL from re-entry signal (if any)
            signal_tp: TP from re-entry signal (if any)
        
        Returns:
            Tuple of (inherited_sl, inherited_tp)
        """
        # Inherit SL
        inherited_sl = signal_sl if signal_sl else parent.sl
        
        # Inherit TP
        if signal_tp:
            inherited_tp = signal_tp
        elif parent.tp:
            # Inherit parent's TP
            inherited_tp = [parent.tp] if isinstance(parent.tp, (int, float)) else parent.tp
        else:
            # Auto-assign TP = entry ± 2× SL distance
            if inherited_sl and parent.entry_price:
                sl_distance = abs(parent.entry_price - inherited_sl)
                if parent.direction == 'BUY':
                    auto_tp = parent.entry_price + (2 * sl_distance)
                else:
                    auto_tp = parent.entry_price - (2 * sl_distance)
                inherited_tp = [auto_tp]
                logger.info(
                    f"[ReEntry] Auto-assigned TP={auto_tp:.5f} "
                    f"(entry ± 2× SL distance)"
                )
            else:
                inherited_tp = None
        
        logger.info(
            f"[ReEntry] Inherited from parent: SL={inherited_sl} TP={inherited_tp}"
        )
        
        return inherited_sl, inherited_tp
